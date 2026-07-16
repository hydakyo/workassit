import logging
from pathlib import Path
from typing import Optional
import dataclasses

from app.models.project import Project, ProjectMetadata, ProjectFeatures
from app.models.domain import Task, Artifact, Delivery
from app.config.constants import PROJECT_FILENAME
from app.utils.atomic_json import read_json, write_json_atomic

logger = logging.getLogger(__name__)

class ProjectRepository:
    def read_project(self, directory: Path) -> Optional[Project]:
        """
        Reads project metadata from a directory.
        Returns None if no project.json exists or if it is corrupt.
        """
        project_file = directory / PROJECT_FILENAME
        
        if not project_file.is_file():
            return None
            
        try:
            data = read_json(project_file)
        except Exception as e:
            raise ValueError(f"Invalid JSON in {project_file}: {e}")
            
        required_fields = [
            "schema_version", "project_id", "project_name", 
            "customer_name", "project_type", "stage", 
            "created_at", "updated_at"
        ]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field '{field}' in {project_file}")
                
        features_data = data.get("features", {})
        features = ProjectFeatures(
            design=features_data.get("design", False),
            implementation=features_data.get("implementation", False)
        )
        
        metadata = ProjectMetadata(
            schema_version=data["schema_version"],
            project_id=data["project_id"],
            project_name=data["project_name"],
            customer_name=data["customer_name"],
            project_type=data["project_type"],
            stage=data["stage"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            features=features
        )
        
        tasks = []
        for t in data.get("tasks", []):
            valid_fields = {f.name for f in dataclasses.fields(Task)}
            filtered_t = {k: v for k, v in t.items() if k in valid_fields}
            tasks.append(Task(**filtered_t))
            
        artifacts = []
        for a in data.get("artifacts", []):
            valid_fields = {f.name for f in dataclasses.fields(Artifact)}
            filtered_a = {k: v for k, v in a.items() if k in valid_fields}
            artifacts.append(Artifact(**filtered_a))

        deliveries = []
        for d in data.get("deliveries", []):
            valid_fields = {f.name for f in dataclasses.fields(Delivery)}
            filtered_d = {k: v for k, v in d.items() if k in valid_fields}
            deliveries.append(Delivery(**filtered_d))
            
        return Project(
            path=str(directory), 
            metadata=metadata,
            template_id=data.get("template_id", ""),
            tasks=tasks,
            artifacts=artifacts,
            deliveries=deliveries
        )

    def create_project(self, project: Project) -> None:
        """
        Saves a project to disk (project.json).
        """
        project_dir = Path(project.path)
        project_dir.mkdir(parents=True, exist_ok=True)
        
        project_file = project_dir / PROJECT_FILENAME
        
        data = {
            "schema_version": project.metadata.schema_version,
            "project_id": project.metadata.project_id,
            "project_name": project.metadata.project_name,
            "customer_name": project.metadata.customer_name,
            "project_type": project.metadata.project_type,
            "stage": project.metadata.stage,
            "created_at": project.metadata.created_at,
            "updated_at": project.metadata.updated_at,
            "features": {
                "design": project.metadata.features.design,
                "implementation": project.metadata.features.implementation
            },
            "template_id": project.template_id,
            "tasks": [dataclasses.asdict(t) for t in project.tasks],
            "artifacts": [dataclasses.asdict(a) for a in project.artifacts],
            "deliveries": [dataclasses.asdict(d) for d in project.deliveries]
        }
        
        write_json_atomic(project_file, data)

    def save_project(self, project: Project) -> None:
        self.create_project(project)
