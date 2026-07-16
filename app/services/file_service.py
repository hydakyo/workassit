import shutil
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict

from app.models.project import Project
from app.models.audit import AuditEntry, UndoResult, UndoStatus
from app.repositories.audit_repository import AuditRepository
from app.utils.path_validator import PathViolationError, resolve_project_path

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self, audit_repo: AuditRepository):
        self.audit_repo = audit_repo
        
        # Simple routing rules
        self.routing_rules: Dict[str, str] = {
            ".json": "03_Implementation/configs",
            ".txt": "00_Inbox",
            ".drawio": "02_Design/diagrams",
            ".yaml": "03_Implementation/configs",
            ".yml": "03_Implementation/configs",
        }

    def _get_destination_dir(self, project_path: Path, extension: str) -> Path:
        sub_dir = self.routing_rules.get(extension.lower(), "00_Inbox")
        dest_dir = resolve_project_path(project_path, sub_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        return dest_dir

    def _copy_atomically(self, source_path: Path, destination_path: Path) -> None:
        temp_file = tempfile.NamedTemporaryFile(delete=False, dir=destination_path.parent)
        temp_path = Path(temp_file.name)
        temp_file.close()
        try:
            shutil.copy2(source_path, temp_path)
            os.replace(temp_path, destination_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def import_file_for_artifact(self, project: Project, source_path_str: str) -> Optional[str]:
        source_path = Path(source_path_str)
        if not source_path.is_file():
            logger.error(f"Source file not found: {source_path}")
            return None
            
        project_dir = Path(project.path)
        try:
            dest_dir = self._get_destination_dir(project_dir, source_path.suffix)
            destination_relative_path = str((dest_dir / source_path.name).relative_to(project_dir))
            dest_path = resolve_project_path(project_dir, destination_relative_path)
        except (PathViolationError, ValueError) as exc:
            logger.error("Rejected unsafe artifact destination: %s", exc)
            return None
        
        now = datetime.now(timezone.utc).isoformat()
        version_path: Optional[str] = None
        backup_path: Optional[Path] = None
        action = "IMPORT"
        
        if dest_path.exists():
            # Versioning
            action = "OVERWRITE"
            versions_dir = resolve_project_path(project_dir, ".versions")
            versions_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            backup_name = f"{timestamp}_{uuid.uuid4().hex}_{source_path.name}"
            backup_path = resolve_project_path(project_dir, f".versions/{backup_name}")
            
            try:
                shutil.copy2(dest_path, backup_path)
                version_path = str(backup_path.relative_to(project_dir))
            except Exception as e:
                logger.error(f"Failed to create version backup for {dest_path}: {e}")
                return None
                
        try:
            self._copy_atomically(source_path, dest_path)
        except Exception as e:
            logger.error(f"Failed to import file to {dest_path}: {e}")
            return None
            
        rel_dest_path = str(dest_path.relative_to(project_dir))
        entry = AuditEntry(
            timestamp=now,
            action=action,
            file_name=source_path.name,
            destination_path=rel_dest_path,
            previous_version_path=version_path,
            user="System" # In phase 1/3, user is implicit
        )
        try:
            self.audit_repo.append_log(project_dir, entry)
        except RuntimeError:
            try:
                if action == "IMPORT":
                    dest_path.unlink()
                elif backup_path is not None:
                    self._copy_atomically(backup_path, dest_path)
                    backup_path.unlink(missing_ok=True)
            except OSError:
                logger.critical("Import rollback failed after audit failure.")
            return None
        return rel_dest_path

    def undo_last_import(self, project: Project) -> UndoResult:
        project_dir = Path(project.path)
        try:
            logs = self.audit_repo.read_logs(project_dir)
        except RuntimeError:
            return UndoResult(UndoStatus.AUDIT_FAILED)
        if not logs:
            return UndoResult(UndoStatus.NOTHING_TO_UNDO)
            
        # Collect timestamps of already undone events
        undone_event_ids = set()
        for log in logs:
            if log.action == "UNDO" and log.undo_of_event_id:
                undone_event_ids.add(log.undo_of_event_id)
                
        # Find last IMPORT or OVERWRITE that hasn't been undone
        last_entry = None
        for i in range(len(logs) - 1, -1, -1):
            if logs[i].action in ["IMPORT", "OVERWRITE"] and logs[i].event_id not in undone_event_ids:
                last_entry = logs[i]
                break
                
        if not last_entry:
            return UndoResult(UndoStatus.NOTHING_TO_UNDO)
        try:
            dest_path = resolve_project_path(project_dir, last_entry.destination_path)
            rollback_dir = resolve_project_path(project_dir, ".projectos/undo")
            rollback_dir.mkdir(parents=True, exist_ok=True)
        except PathViolationError:
            return UndoResult(UndoStatus.PATH_REJECTED, last_entry.event_id)
        if not dest_path.is_file():
            return UndoResult(UndoStatus.TARGET_MISSING, last_entry.event_id)

        rollback_path = rollback_dir / f"{uuid.uuid4().hex}.rollback"
        try:
            if last_entry.action == "IMPORT":
                os.replace(dest_path, rollback_path)
            else:
                if not last_entry.previous_version_path:
                    return UndoResult(UndoStatus.BACKUP_MISSING, last_entry.event_id)
                backup_path = resolve_project_path(project_dir, last_entry.previous_version_path)
                if not backup_path.is_file():
                    return UndoResult(UndoStatus.BACKUP_MISSING, last_entry.event_id)
                self._copy_atomically(dest_path, rollback_path)
                self._copy_atomically(backup_path, dest_path)
        except (OSError, PathViolationError):
            return UndoResult(UndoStatus.IO_ERROR, last_entry.event_id)

        now = datetime.now(timezone.utc).isoformat()
        undo_entry = AuditEntry(
            timestamp=now,
            action="UNDO",
            file_name=last_entry.file_name,
            destination_path=last_entry.destination_path,
            undo_of_event_id=last_entry.event_id,
            user="System"
        )
        try:
            self.audit_repo.append_log(project_dir, undo_entry)
        except RuntimeError:
            try:
                os.replace(rollback_path, dest_path)
            except OSError:
                logger.critical("Undo rollback failed after audit failure.")
            return UndoResult(UndoStatus.AUDIT_FAILED, last_entry.event_id)
        rollback_path.unlink(missing_ok=True)
        return UndoResult(UndoStatus.SUCCESS, last_entry.event_id)
