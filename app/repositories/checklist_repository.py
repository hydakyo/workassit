import json
import logging
from pathlib import Path
from typing import List

from app.models.checklist import ChecklistItem

logger = logging.getLogger(__name__)

class ChecklistRepository:
    def __init__(self, filename: str = "checklist.json"):
        self.filename = filename

    def load_checklist(self, project_path: Path) -> List[ChecklistItem]:
        checklist_file = project_path / self.filename
        if not checklist_file.exists():
            return []
            
        try:
            with open(checklist_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [
                    ChecklistItem(
                        id=item.get("id", str(i)),
                        title=item.get("title", ""),
                        is_completed=item.get("is_completed", False)
                    )
                    for i, item in enumerate(data)
                ]
        except Exception as e:
            logger.error(f"Failed to load checklist from {checklist_file}: {e}")
            return []

    def save_checklist(self, project_path: Path, items: List[ChecklistItem]) -> bool:
        checklist_file = project_path / self.filename
        try:
            data = [
                {
                    "id": item.id,
                    "title": item.title,
                    "is_completed": item.is_completed
                }
                for item in items
            ]
            
            # Use a temporary file for atomic write
            temp_file = checklist_file.with_suffix('.tmp')
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            temp_file.replace(checklist_file)
            return True
        except Exception as e:
            logger.error(f"Failed to save checklist to {checklist_file}: {e}")
            return False
