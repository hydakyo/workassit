from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

class TaskStatus(Enum):
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    BLOCKED = "Blocked"
    DONE = "Done"

class Priority(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class ArtifactStatus(Enum):
    DRAFT = "Draft"
    REVIEW = "Review"
    APPROVED = "Approved"

@dataclass
class Task:
    title: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    status: str = TaskStatus.TODO.value
    priority: str = Priority.MEDIUM.value
    owner: Optional[str] = None
    due_date: Optional[str] = None
    phase: Optional[str] = None
    category: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None

@dataclass
class Artifact:
    type: str
    path: str
    artifact_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = ArtifactStatus.DRAFT.value
    version: str = "1.0"
    checksum: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    owner: Optional[str] = None
    
@dataclass
class Phase:
    name: str
    description: str = ""
    entry_criteria: List[str] = field(default_factory=list)
    exit_criteria: List[str] = field(default_factory=list)
    required_artifacts: List[str] = field(default_factory=list)
    approval_status: str = "Pending"
    blocking_issues: List[str] = field(default_factory=list)

@dataclass
class Site:
    name: str
    site_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    location: str = ""
    contact: Optional[str] = None

@dataclass
class Device:
    site_id: str
    serial_number: str
    device_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_hostname: str = ""
    target_hostname: str = ""
    model: str = ""
    management_ip: str = ""
    firmware: str = ""
    deployment_wave: str = ""
    pre_check_status: str = "Pending"
    implementation_status: str = "Pending"
    post_check_status: str = "Pending"
    uat_status: str = "Pending"

@dataclass
class Delivery:
    version: str
    release_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    manifest: Dict[str, Any] = field(default_factory=dict)
    included_artifacts: List[str] = field(default_factory=list)
    checksum: str = ""
    generated_time: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    generated_by: str = ""
    approval_state: str = "Pending"
    release_notes: str = ""
