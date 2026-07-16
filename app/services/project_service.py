import logging
from pathlib import Path

from app.models.project import Project, ProjectMetadata
from app.repositories.project_repository import ProjectRepository

logger = logging.getLogger(__name__)

class ProjectService:
    def __init__(self, project_repo: ProjectRepository):
        self.project_repo = project_repo

    def create_new_project(
        self, 
        root_path: Path, 
        project_name: str, 
        customer_name: str, 
        project_type: str
    ) -> Project:
        """
        Creates a new project directory and initializes scaffolding.
        """
        # Create a safe folder name based on project name
        safe_name = "".join(c if c.isalnum() else "_" for c in project_name).strip("_")
        project_dir = root_path / safe_name
        
        # Ensure it doesn't already exist
        if project_dir.exists():
            raise FileExistsError(f"Directory already exists: {project_dir}")
            
        project_dir.mkdir(parents=True)
        
        metadata = ProjectMetadata.create_new(
            name=project_name, 
            customer=customer_name, 
            p_type=project_type
        )
        
        project = Project(path=str(project_dir), metadata=metadata)
        
        # Save project.json
        self.project_repo.create_project(project)
        
        # JIT Scaffolding: Create base directories
        base_dirs = ["00_Inbox", "01_Planning", "02_Design", "03_Implementation", "04_Delivery"]
        for d in base_dirs:
            (project_dir / d).mkdir()
            
        logger.info(f"Created new project '{project_name}' at {project_dir}")
        return project
