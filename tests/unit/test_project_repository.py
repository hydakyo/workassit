import json
import pytest
from pathlib import Path
from app.repositories.project_repository import ProjectRepository
from app.config.constants import PROJECT_FILENAME
from app.models.domain import Device, Phase, Site
from app.models.project import Project, ProjectMetadata

@pytest.fixture
def repo():
    return ProjectRepository()

def test_read_valid_project(tmp_path: Path, repo: ProjectRepository):
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()
    
    valid_data = {
        "schema_version": 1,
        "project_id": "123",
        "project_name": "Test Project",
        "customer_name": "Test Customer",
        "project_type": "network",
        "stage": "planning",
        "created_at": "2023-10-01",
        "updated_at": "2023-10-02",
        "features": {
            "design": True
        }
    }
    
    with open(project_dir / PROJECT_FILENAME, "w", encoding="utf-8") as f:
        json.dump(valid_data, f)
        
    project = repo.read_project(project_dir)
    assert project is not None
    assert project.metadata.project_name == "Test Project"
    assert project.metadata.features.design is True
    assert project.metadata.features.implementation is False

def test_read_missing_project(tmp_path: Path, repo: ProjectRepository):
    project_dir = tmp_path / "empty_dir"
    project_dir.mkdir()
    
    project = repo.read_project(project_dir)
    assert project is None

def test_read_corrupted_json(tmp_path: Path, repo: ProjectRepository):
    project_dir = tmp_path / "corrupt_project"
    project_dir.mkdir()
    
    with open(project_dir / PROJECT_FILENAME, "w", encoding="utf-8") as f:
        f.write("{ invalid_json: ")
        
    with pytest.raises(ValueError):
        repo.read_project(project_dir)

def test_read_missing_required_fields(tmp_path: Path, repo: ProjectRepository):
    project_dir = tmp_path / "incomplete_project"
    project_dir.mkdir()
    
    incomplete_data = {
        "schema_version": 1,
        "project_name": "Missing Fields Project"
        # missing other required fields
    }
    
    with open(project_dir / PROJECT_FILENAME, "w", encoding="utf-8") as f:
        json.dump(incomplete_data, f)
        
    with pytest.raises(ValueError):
        repo.read_project(project_dir)


def test_project_persists_phases_sites_and_devices(tmp_path: Path, repo: ProjectRepository) -> None:
    metadata = ProjectMetadata.create_new("Test", "Customer", "Network")
    project = Project(
        path=str(tmp_path),
        metadata=metadata,
        phases=[Phase(name="Design", entry_criteria=["Kickoff complete"])],
        sites=[Site(name="Hanoi")],
        devices=[Device(site_id="site-1", serial_number="SERIAL-1")],
    )

    repo.create_project(project)
    loaded = repo.read_project(tmp_path)

    assert loaded is not None
    assert loaded.phases[0].entry_criteria == ["Kickoff complete"]
    assert loaded.sites[0].name == "Hanoi"
    assert loaded.devices[0].serial_number == "SERIAL-1"
