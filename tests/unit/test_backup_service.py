from pathlib import Path
import zipfile

from app.models.project import Project, ProjectMetadata
from app.services.backup_service import BackupService


def test_backup_creates_recovery_zip_without_recursing_into_backups(tmp_path: Path) -> None:
    (tmp_path / "01_Planning").mkdir()
    (tmp_path / "01_Planning" / "plan.txt").write_text("plan")
    project = Project(path=str(tmp_path), metadata=ProjectMetadata.create_new("Project", "Customer", "Network"))

    relative_backup = BackupService().create_backup(project)

    backup_path = tmp_path / relative_backup
    assert backup_path.is_file()
    with zipfile.ZipFile(backup_path) as archive:
        assert "01_Planning/plan.txt" in archive.namelist()
        assert not any(name.startswith(".projectos/backups/") for name in archive.namelist())


def test_restore_extracts_backup_to_new_project_directory(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "project.json").write_text('{"project": "source"}')
    project = Project(path=str(source_root), metadata=ProjectMetadata.create_new("Project", "Customer", "Network"))
    service = BackupService()
    backup_path = service.create_backup(project)
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    destination = service.restore_backup(project, backup_path, workspace_root)

    assert destination.parent == workspace_root
    assert (destination / "project.json").read_text() == '{"project": "source"}'
