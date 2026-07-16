from pathlib import Path

from app.database.connection import DatabaseManager
from app.database.indexer import Indexer
from app.models.domain import Artifact, Task
from app.models.project import Project, ProjectMetadata
from app.services.search_service import SearchService


def test_search_and_dashboard_metrics(tmp_path: Path) -> None:
    database = DatabaseManager(str(tmp_path / "index.db"))
    project = Project(
        path=str(tmp_path / "project"),
        metadata=ProjectMetadata.create_new("Hanoi Network", "Example Customer", "Network"),
        tasks=[Task(title="Done", status="Done"), Task(title="Open")],
        artifacts=[Artifact(type="HLD", path="design/hld.pdf")],
    )
    Indexer(database).sync_project(project)
    service = SearchService(database)

    results = service.search_projects("customer")

    assert results[0]["id"] == project.metadata.project_id
    assert service.get_dashboard_metrics() == {
        "projects": 1,
        "tasks_total": 2,
        "tasks_done": 1,
        "artifacts_attached": 1,
    }
