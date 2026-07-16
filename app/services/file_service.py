import shutil
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict

from app.models.project import Project
from app.models.audit import AuditEntry
from app.repositories.audit_repository import AuditRepository

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
        dest_dir = project_path / sub_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        return dest_dir

    def import_file_for_artifact(self, project: Project, source_path_str: str) -> Optional[str]:
        source_path = Path(source_path_str)
        if not source_path.is_file():
            logger.error(f"Source file not found: {source_path}")
            return None
            
        project_dir = Path(project.path)
        dest_dir = self._get_destination_dir(project_dir, source_path.suffix)
        dest_path = dest_dir / source_path.name
        
        now = datetime.now(timezone.utc).isoformat()
        version_path: Optional[str] = None
        action = "IMPORT"
        
        if dest_path.exists():
            # Versioning
            action = "OVERWRITE"
            versions_dir = project_dir / ".versions"
            versions_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            backup_name = f"{timestamp}_{source_path.name}"
            backup_path = versions_dir / backup_name
            
            try:
                shutil.copy2(dest_path, backup_path)
                version_path = str(backup_path.relative_to(project_dir))
            except Exception as e:
                logger.error(f"Failed to create version backup for {dest_path}: {e}")
                return None
                
        try:
            shutil.copy2(source_path, dest_path)
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
        self.audit_repo.append_log(project_dir, entry)
        return rel_dest_path

    def undo_last_import(self, project: Project) -> bool:
        project_dir = Path(project.path)
        logs = self.audit_repo.read_logs(project_dir)
        if not logs:
            return False
            
        # Collect timestamps of already undone events
        undone_timestamps = set()
        for log in logs:
            if log.action == "UNDO" and log.previous_version_path:
                undone_timestamps.add(log.previous_version_path)
                
        # Find last IMPORT or OVERWRITE that hasn't been undone
        last_entry = None
        for i in range(len(logs) - 1, -1, -1):
            if logs[i].action in ["IMPORT", "OVERWRITE"] and logs[i].timestamp not in undone_timestamps:
                last_entry = logs[i]
                break
                
        if not last_entry:
            return False
            
        dest_path = project_dir / last_entry.destination_path
        
        if last_entry.action == "IMPORT":
            if dest_path.exists():
                dest_path.unlink()
        elif last_entry.action == "OVERWRITE":
            if last_entry.previous_version_path:
                backup_path = project_dir / last_entry.previous_version_path
                if backup_path.exists():
                    shutil.copy2(backup_path, dest_path)
                    
        now = datetime.now(timezone.utc).isoformat()
        undo_entry = AuditEntry(
            timestamp=now,
            action="UNDO",
            file_name=last_entry.file_name,
            destination_path=last_entry.destination_path,
            previous_version_path=last_entry.timestamp, # Store the undone event's timestamp here
            user="System"
        )
        self.audit_repo.append_log(project_dir, undo_entry)
        return True
