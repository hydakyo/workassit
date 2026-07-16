import pytest
from pathlib import Path
from app.services.file_service import FileService
from app.repositories.audit_repository import AuditRepository
from app.models.project import Project, ProjectMetadata, ProjectFeatures
from app.models.audit import AuditEntry, UndoStatus
from unittest.mock import patch

@pytest.fixture
def audit_repo():
    return AuditRepository()

@pytest.fixture
def file_service(audit_repo):
    return FileService(audit_repo)

@pytest.fixture
def dummy_project(tmp_path: Path):
    project_dir = tmp_path / "dummy_project"
    project_dir.mkdir()
    meta = ProjectMetadata(
        schema_version=1,
        project_id="test",
        project_name="Test",
        customer_name="Customer",
        project_type="type",
        stage="planning",
        created_at="",
        updated_at="",
        features=ProjectFeatures()
    )
    return Project(path=str(project_dir), metadata=meta)

def test_file_import_and_routing(tmp_path: Path, file_service: FileService, dummy_project: Project):
    source_file = tmp_path / "config.json"
    source_file.write_text("{}")
    
    rel_path = file_service.import_file_for_artifact(dummy_project, str(source_file))
    
    assert rel_path is not None
    project_dir = Path(dummy_project.path)
    dest_path = project_dir / rel_path
    assert dest_path.exists()
    assert dest_path.parent.name == "configs"
    
    logs = file_service.audit_repo.read_logs(project_dir)
    assert len(logs) == 1
    assert logs[0].action == "IMPORT"
    assert logs[0].file_name == "config.json"

def test_file_versioning_and_undo(tmp_path: Path, file_service: FileService, dummy_project: Project):
    source_file = tmp_path / "config.json"
    source_file.write_text('{"v": 1}')
    
    file_service.import_file_for_artifact(dummy_project, str(source_file))
    
    source_file.write_text('{"v": 2}')
    file_service.import_file_for_artifact(dummy_project, str(source_file))
    
    project_dir = Path(dummy_project.path)
    dest_path = project_dir / "03_Implementation/configs/config.json"
    assert dest_path.read_text() == '{"v": 2}'
    
    logs = file_service.audit_repo.read_logs(project_dir)
    assert len(logs) == 2
    assert logs[1].action == "OVERWRITE"
    assert logs[1].previous_version_path is not None
    
    undo_result = file_service.undo_last_import(dummy_project)
    
    assert undo_result.status == UndoStatus.SUCCESS
    assert dest_path.read_text() == '{"v": 1}'
    logs = file_service.audit_repo.read_logs(project_dir)
    assert len(logs) == 3
    assert logs[-1].action == "UNDO"
    assert logs[-1].undo_of_event_id == logs[1].event_id


def test_undo_rejects_tampered_audit_path(tmp_path: Path, file_service: FileService, dummy_project: Project) -> None:
    protected_file = tmp_path / "protected.txt"
    protected_file.write_text("keep")
    file_service.audit_repo.append_log(
        Path(dummy_project.path),
        AuditEntry(
            timestamp="2026",
            action="IMPORT",
            file_name="protected.txt",
            destination_path="../../protected.txt",
        ),
    )

    result = file_service.undo_last_import(dummy_project)

    assert result.status == UndoStatus.PATH_REJECTED
    assert protected_file.read_text() == "keep"


def test_undo_does_not_audit_success_when_target_is_missing(
    tmp_path: Path, file_service: FileService, dummy_project: Project
) -> None:
    file_service.audit_repo.append_log(
        Path(dummy_project.path),
        AuditEntry(timestamp="2026", action="IMPORT", file_name="gone.txt", destination_path="00_Inbox/gone.txt"),
    )

    result = file_service.undo_last_import(dummy_project)

    assert result.status == UndoStatus.TARGET_MISSING
    assert len(file_service.audit_repo.read_logs(Path(dummy_project.path))) == 1


def test_import_rolls_back_when_audit_write_fails(
    tmp_path: Path, file_service: FileService, dummy_project: Project
) -> None:
    source_file = tmp_path / "config.json"
    source_file.write_text("{}")
    with patch.object(file_service.audit_repo, "append_log", side_effect=RuntimeError("Denied")):
        assert file_service.import_file_for_artifact(dummy_project, str(source_file)) is None

    assert not (Path(dummy_project.path) / "03_Implementation/configs/config.json").exists()
