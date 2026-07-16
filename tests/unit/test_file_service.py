import pytest
from pathlib import Path
from app.services.file_service import FileService
from app.repositories.audit_repository import AuditRepository
from app.models.project import Project, ProjectMetadata, ProjectFeatures

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
    
    success = file_service.import_file(dummy_project, str(source_file))
    assert success
    
    project_dir = Path(dummy_project.path)
    dest_file = project_dir / "03_Implementation/configs/config.json"
    assert dest_file.exists()
    
    logs = file_service.audit_repo.read_logs(project_dir)
    assert len(logs) == 1
    assert logs[0].action == "IMPORT"

def test_file_versioning_and_undo(tmp_path: Path, file_service: FileService, dummy_project: Project):
    source_file = tmp_path / "config.json"
    source_file.write_text('{"v": 1}')
    
    file_service.import_file(dummy_project, str(source_file))
    
    source_file.write_text('{"v": 2}')
    file_service.import_file(dummy_project, str(source_file))
    
    project_dir = Path(dummy_project.path)
    dest_file = project_dir / "03_Implementation/configs/config.json"
    
    assert dest_file.read_text() == '{"v": 2}'
    
    logs = file_service.audit_repo.read_logs(project_dir)
    assert len(logs) == 2
    assert logs[1].action == "OVERWRITE"
    assert logs[1].previous_version_path is not None
    
    # Test undo
    success = file_service.undo_last_import(dummy_project)
    assert success
    assert dest_file.read_text() == '{"v": 1}'
    
    logs_after_undo = file_service.audit_repo.read_logs(project_dir)
    assert len(logs_after_undo) == 3
    assert logs_after_undo[2].action == "UNDO"
