from dataclasses import dataclass, field
from typing import List

@dataclass
class AppSettings:
    schema_version: int = 1
    workspace_roots: List[str] = field(default_factory=list)
    theme: str = "dark"
    default_author: str = ""
    ai_provider: str = "None"
    ai_api_key: str = ""
