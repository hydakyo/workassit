from pathlib import Path
import zipfile
import json
from app.services.delivery_service import DeliveryService
from app.models.project import Project, ProjectMetadata, ProjectFeatures
from app.models.domain import Artifact

def test_delivery_service(tmp_path: Path):
    project_dir = tmp_path / "dummy_project"
    project_dir.mkdir()
    
    # Create dummy artifacts
    (project_dir / "03_Implementation").mkdir()
    (project_dir / "03_Implementation" / "config.json").write_text('{"key": "value"}')
    
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
    
    art = Artifact(type="Config", path="03_Implementation/config.json")
    
    project = Project(path=str(project_dir), metadata=meta, artifacts=[art])
    
    service = DeliveryService()
    rel_zip_path = service.create_delivery_package(project)
    
    assert rel_zip_path is not None
    zip_path = project_dir / rel_zip_path
    
    assert zip_path.exists()
    assert zip_path.suffix == ".zip"
    
    # Check if delivery object was added
    assert len(project.deliveries) == 1
    assert project.deliveries[0].version == "1.0"
    
    # Check ZIP contents
    with zipfile.ZipFile(zip_path, 'r') as zf:
        namelist = zf.namelist()
        assert "config.json" in namelist
        assert "manifest.json" in namelist
        
        manifest_data = json.loads(zf.read("manifest.json"))
        assert manifest_data["project_name"] == "Test"
        assert len(manifest_data["artifacts"]) == 1
        assert manifest_data["artifacts"][0]["type"] == "Config"


def test_delivery_prefers_template_delivery_directory(tmp_path: Path) -> None:
    project_dir = tmp_path / "template_project"
    project_dir.mkdir()
    (project_dir / "05_Delivery").mkdir()
    metadata = ProjectMetadata(
        schema_version=1,
        project_id="test",
        project_name="Test",
        customer_name="Customer",
        project_type="type",
        stage="planning",
        created_at="",
        updated_at="",
        features=ProjectFeatures(),
    )

    result = DeliveryService().create_delivery_package(Project(path=str(project_dir), metadata=metadata))
    assert result is not None
    assert Path(result).parts[0] == "05_Delivery"


def test_delivery_keeps_artifacts_with_duplicate_names(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    first_dir = project_dir / "first"
    second_dir = project_dir / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    (first_dir / "config.json").write_text('{"site": 1}')
    (second_dir / "config.json").write_text('{"site": 2}')
    metadata = ProjectMetadata(
        schema_version=1,
        project_id="test",
        project_name="Test",
        customer_name="Customer",
        project_type="type",
        stage="planning",
        created_at="",
        updated_at="",
        features=ProjectFeatures(),
    )
    project = Project(
        path=str(project_dir),
        metadata=metadata,
        artifacts=[Artifact(type="First", path="first/config.json"), Artifact(type="Second", path="second/config.json")],
    )

    result = DeliveryService().create_delivery_package(project)

    assert result is not None
    with zipfile.ZipFile(project_dir / result) as zip_file:
        names = zip_file.namelist()
        assert len([name for name in names if name.endswith("config.json")]) == 2
