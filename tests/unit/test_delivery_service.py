from pathlib import Path
from app.services.delivery_service import DeliveryService
from app.models.project import Project, ProjectMetadata, ProjectFeatures

def test_delivery_service(tmp_path: Path):
    project_dir = tmp_path / "dummy_project"
    project_dir.mkdir()
    
    # Create dummy files
    (project_dir / "03_Implementation").mkdir()
    (project_dir / "03_Implementation" / "config.json").write_text("{}")
    
    # Create excluded files
    (project_dir / ".versions").mkdir()
    (project_dir / ".versions" / "old.json").write_text("{}")
    (project_dir / "project.json").write_text("{}")
    
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
    project = Project(path=str(project_dir), metadata=meta)
    
    service = DeliveryService()
    zip_path = service.create_delivery_package(project)
    
    assert zip_path is not None
    assert Path(zip_path).exists()
    assert Path(zip_path).suffix == ".zip"
