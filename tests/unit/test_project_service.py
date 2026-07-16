import pytest
from pathlib import Path
from app.services.project_service import ProjectService
from app.repositories.project_repository import ProjectRepository

@pytest.fixture
def repo():
    return ProjectRepository()

@pytest.fixture
def service(repo):
    return ProjectService(repo)

def test_create_new_project(tmp_path: Path, service: ProjectService):
    root = tmp_path / "workspace"
    root.mkdir()
    
    project = service.create_new_project(root, "New Network", "ACME", "network_deployment")
    
    assert project is not None
    assert project.metadata.project_name == "New Network"
    assert project.metadata.customer_name == "ACME"
    assert project.metadata.project_type == "network_deployment"
    
    project_dir = Path(project.path)
    assert project_dir.exists()
    assert (project_dir / "project.json").exists()
    assert (project_dir / "00_Inbox").exists()
    assert (project_dir / "01_Planning").exists()
    
def test_create_project_exists(tmp_path: Path, service: ProjectService):
    root = tmp_path / "workspace"
    root.mkdir()
    
    # First creation
    service.create_new_project(root, "Test", "Customer", "type")
    
    # Second creation should fail
    with pytest.raises(FileExistsError):
        service.create_new_project(root, "Test", "Customer", "type")
