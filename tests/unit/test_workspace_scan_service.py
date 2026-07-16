from pathlib import Path
from app.services.workspace_scan_service import WorkspaceScanService
from app.repositories.project_repository import ProjectRepository
from app.config.settings import AppSettings
from app.models.project import Project, ProjectMetadata
import time

class DummyProjectRepo(ProjectRepository):
    def read_project(self, project_path: Path) -> Project | None:
        if (project_path / "project.json").exists():
            from datetime import datetime
            return Project(
                path=str(project_path),
                metadata=ProjectMetadata(
                    schema_version=1,
                    project_id="test",
                    project_name="Test",
                    customer_name="Test",
                    project_type="test",
                    stage="init",
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat()
                )
            )
        return None

def test_scan_workspaces_async(tmp_path):
    # Setup mock workspace
    ws_root = tmp_path / "workspace"
    ws_root.mkdir()
    
    p1 = ws_root / "Project1"
    p1.mkdir()
    (p1 / "project.json").write_text("{}")
    
    p2 = ws_root / "NotProject"
    p2.mkdir()
    
    settings = AppSettings(workspace_roots=[str(ws_root), str(tmp_path / "invalid_root")])
    repo = DummyProjectRepo()
    service = WorkspaceScanService(repo)
    
    result_projects = []
    result_warnings = []
    
    def on_complete(projects, warnings):
        result_projects.extend(projects)
        result_warnings.extend(warnings)
        
    def on_error(err):
        pass
        
    service.scan_workspaces_async(settings, on_complete, on_error)
    
    # Wait for background thread
    time.sleep(0.1)
    service.shutdown()
    
    assert len(result_projects) == 1
    assert result_projects[0].metadata.project_name == "Test"
    assert len(result_warnings) == 1
    assert "Workspace root not found" in result_warnings[0]
