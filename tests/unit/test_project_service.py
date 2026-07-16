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
    
    project = service.create_new_project(
        root_path=tmp_path,
        project_name="Test Project",
        customer_name="Test Cust",
        project_type="Network"
    )
    
    assert project.metadata.project_name == "Test Project"
    assert project.metadata.customer_name == "Test Cust"
    assert (tmp_path / "Test_Project").exists()
    assert (tmp_path / "Test_Project" / "01_Planning").exists()

def test_create_project_with_template(tmp_path: Path):
    from app.templates.loader import TemplateLoader
    from app.models.template import ProjectTemplate
    from app.models.domain import Task
    
    class MockTemplateLoader(TemplateLoader):
        def load_template(self, template_id: str):
            return ProjectTemplate(
                template_id="test-1",
                name="Test",
                description="desc",
                folder_structure=["Docs", "Code"],
                default_tasks=[Task(title="T1", phase="Phase 1")],
                required_artifacts=["HLD"]
            )
            
    project_repo = ProjectRepository()
    project_service = ProjectService(project_repo, MockTemplateLoader())
    
    project = project_service.create_new_project(
        root_path=tmp_path,
        project_name="Template Project",
        customer_name="Cust",
        project_type="Network",
        template_id="test-1"
    )
    
    assert (tmp_path / "Template_Project").exists()
    assert (tmp_path / "Template_Project" / "Docs").exists()
    assert (tmp_path / "Template_Project" / "Code").exists()
    assert not (tmp_path / "Template_Project" / "01_Planning").exists()
    
    assert len(project.tasks) == 1
    assert project.tasks[0].title == "T1"
    assert len(project.artifacts) == 1
    assert project.artifacts[0].type == "HLD"
    
def test_create_project_exists(tmp_path: Path, service: ProjectService):
    root = tmp_path / "workspace"
    root.mkdir()
    
    # First creation
    service.create_new_project(root, "Test", "Customer", "type")
    
    # Second creation should fail
    with pytest.raises(FileExistsError):
        service.create_new_project(root, "Test", "Customer", "type")


def test_create_project_preserves_interrupted_staging_operation(
    tmp_path: Path, service: ProjectService
) -> None:
    recovery_dir = tmp_path / ".projectos" / "staging" / "interrupted-operation"
    recovery_dir.mkdir(parents=True)
    recovery_file = recovery_dir / "project.json"
    recovery_file.write_text('{"recovery": true}')

    service.create_new_project(tmp_path, "Test", "Customer", "type")

    assert recovery_file.read_text() == '{"recovery": true}'
    assert (tmp_path / "Test").is_dir()
