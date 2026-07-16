from dataclasses import dataclass, field
from typing import List
from app.models.domain import Phase, Task

@dataclass
class ProjectTemplate:
    template_id: str
    name: str
    description: str
    folder_structure: List[str] = field(default_factory=list)
    phases: List[Phase] = field(default_factory=list)
    default_tasks: List[Task] = field(default_factory=list)
    required_artifacts: List[str] = field(default_factory=list)
