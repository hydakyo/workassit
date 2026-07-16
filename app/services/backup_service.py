"""Create self-contained project backups without blocking the UI thread."""

import os
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from app.models.project import Project
from app.utils.path_validator import PathViolationError, resolve_project_path


class BackupService:
    """Export a project tree into a timestamped ZIP stored inside the project recovery area."""

    def create_backup(self, project: Project) -> str:
        """Create a backup ZIP and return its project-relative path."""
        project_root = Path(project.path)
        backup_dir = resolve_project_path(project_root, ".projectos/backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_name = (
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_"
            f"{uuid.uuid4().hex[:8]}_backup.zip"
        )
        backup_path = resolve_project_path(project_root, f".projectos/backups/{backup_name}")
        descriptor, temp_name = tempfile.mkstemp(prefix=".backup_", suffix=".zip", dir=backup_dir)
        os.close(descriptor)
        temp_path = Path(temp_name)
        try:
            with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for file_path in project_root.rglob("*"):
                    if not file_path.is_file():
                        continue
                    relative_path = file_path.relative_to(project_root)
                    if relative_path.parts[:2] == (".projectos", "backups"):
                        continue
                    safe_path = resolve_project_path(project_root, str(relative_path))
                    if safe_path != file_path.resolve(strict=True):
                        raise PathViolationError("Backup encountered an unsafe project path.")
                    archive.write(safe_path, arcname=str(relative_path))
            os.replace(temp_path, backup_path)
        finally:
            temp_path.unlink(missing_ok=True)
        return str(backup_path.relative_to(project_root))

    def list_backups(self, project: Project) -> list[str]:
        """List project-relative backup ZIP paths newest first."""
        project_root = Path(project.path)
        backup_dir = resolve_project_path(project_root, ".projectos/backups")
        if not backup_dir.is_dir():
            return []
        return [
            str(path.relative_to(project_root))
            for path in sorted(backup_dir.glob("*_backup.zip"), key=lambda path: path.name, reverse=True)
            if path.is_file()
        ]

    def restore_backup(self, project: Project, backup_relative_path: str, workspace_root: Path) -> Path:
        """Restore a backup into a new directory, never overwriting an existing project."""
        source_root = Path(project.path)
        backup_path = resolve_project_path(source_root, backup_relative_path)
        if not backup_path.is_file() or backup_path.suffix.lower() != ".zip":
            raise ValueError("Backup file was not found.")
        if not workspace_root.is_dir() or workspace_root.is_symlink():
            raise ValueError("Restore workspace root is invalid.")
        safe_name = "".join(char if char.isalnum() else "_" for char in project.metadata.project_name).strip("_")
        destination = workspace_root / f"Restored_{safe_name}_{uuid.uuid4().hex[:8]}"
        if destination.exists():
            raise FileExistsError("Restore destination already exists.")
        destination.mkdir()
        try:
            with zipfile.ZipFile(backup_path) as archive:
                for entry in archive.infolist():
                    if entry.is_dir():
                        continue
                    output_path = resolve_project_path(destination, entry.filename)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(entry) as source_file, open(output_path, "wb") as destination_file:
                        shutil.copyfileobj(source_file, destination_file)
        except Exception:
            # The incomplete restore is deliberately retained for diagnosis/recovery.
            raise
        return destination
