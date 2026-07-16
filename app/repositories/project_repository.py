import logging
from pathlib import Path
from typing import Optional

from app.models.project import Project, ProjectMetadata, ProjectFeatures
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
            
            # Minimal schema validation
            required_fields = [
                "schema_version", "project_id", "project_name", 
                "customer_name", "project_type", "stage", 
                "created_at", "updated_at"
            ]
            for field in required_fields:
                if field not in data:
                    logger.warning(f"Project metadata at {project_file} is missing required field: {field}")
                    return None
            
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
            
            return Project(path=str(directory), metadata=metadata)
            
        except Exception as e:
            logger.warning(f"Failed to read or parse project at {project_file}: {e}")
            return None

    def create_project(self, project: Project) -> None:
        """
        Saves a new project to disk (project.json).
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
            }
        }
        
        write_json_atomic(project_file, data)
