from dataclasses import dataclass
from typing import Optional

@dataclass
class AuditEntry:
    timestamp: str
    action: str  # e.g., "IMPORT", "OVERWRITE", "UNDO"
    file_name: str
    destination_path: str
    previous_version_path: Optional[str] = None
    user: str = "System"
