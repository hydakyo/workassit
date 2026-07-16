import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

@dataclass
class AuditEntry:
    timestamp: str
    action: str  # e.g., "IMPORT", "OVERWRITE", "UNDO"
    file_name: str
    destination_path: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    previous_version_path: Optional[str] = None
    undo_of_event_id: Optional[str] = None
    user: str = "System"


class UndoStatus(str, Enum):
    SUCCESS = "SUCCESS"
    NOTHING_TO_UNDO = "NOTHING_TO_UNDO"
    TARGET_MISSING = "TARGET_MISSING"
    BACKUP_MISSING = "BACKUP_MISSING"
    PATH_REJECTED = "PATH_REJECTED"
    AUDIT_FAILED = "AUDIT_FAILED"
    IO_ERROR = "IO_ERROR"


@dataclass(frozen=True)
class UndoResult:
    status: UndoStatus
    event_id: Optional[str] = None
