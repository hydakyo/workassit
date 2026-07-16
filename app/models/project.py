import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field

@dataclass
class ProjectFeatures:
    design: bool = False
    implementation: bool = False

@dataclass
class ProjectMetadata:
    schema_version: int
    project_id: str
    project_name: str
    customer_name: str
    project_type: str
    stage: str
    created_at: str
    updated_at: str
    features: ProjectFeatures = field(default_factory=ProjectFeatures)

    @classmethod
    def create_new(cls, name: str, customer: str, p_type: str) -> "ProjectMetadata":
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            schema_version=1,
            project_id=str(uuid.uuid4()),
            project_name=name,
            customer_name=customer,
            project_type=p_type,
            stage="planning",
            created_at=now,
            updated_at=now
        )

@dataclass
class Project:
    path: str
    metadata: ProjectMetadata
