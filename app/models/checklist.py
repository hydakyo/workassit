from dataclasses import dataclass

@dataclass
class ChecklistItem:
    id: str
    title: str
    is_completed: bool = False
