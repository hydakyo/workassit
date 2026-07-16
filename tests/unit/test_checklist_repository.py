from pathlib import Path
from app.models.checklist import ChecklistItem
from app.repositories.checklist_repository import ChecklistRepository

def test_checklist_repository(tmp_path: Path):
    repo = ChecklistRepository()
    
    # Save
    items = [
        ChecklistItem("1", "Task 1", False),
        ChecklistItem("2", "Task 2", True)
    ]
    assert repo.save_checklist(tmp_path, items)
    
    # Load
    loaded = repo.load_checklist(tmp_path)
    assert len(loaded) == 2
    assert loaded[0].id == "1"
    assert loaded[0].title == "Task 1"
    assert not loaded[0].is_completed
    
    assert loaded[1].id == "2"
    assert loaded[1].title == "Task 2"
    assert loaded[1].is_completed
