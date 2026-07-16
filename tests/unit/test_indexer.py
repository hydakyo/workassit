from pathlib import Path
from app.database.connection import DatabaseManager
from app.database.indexer import Indexer
from app.models.project import Project, ProjectMetadata
from app.models.domain import Task

def test_indexer_sync(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db_manager = DatabaseManager(str(db_path))
    indexer = Indexer(db_manager)
    
    metadata = ProjectMetadata.create_new("Test Proj", "Test Cust", "FW")
    project = Project(
        path=str(tmp_path / "proj"),
        metadata=metadata
    )
    task = Task(title="Test Task")
    project.tasks.append(task)
    
    indexer.sync_project(project)
    
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects")
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0]['name'] == "Test Proj"
        
        cursor.execute("SELECT * FROM tasks")
        task_rows = cursor.fetchall()
        assert len(task_rows) == 1
        assert task_rows[0]['title'] == "Test Task"
    assert db_manager.check_integrity()
