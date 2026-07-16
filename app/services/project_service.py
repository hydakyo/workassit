import logging
from pathlib import Path
from typing import Optional

from app.models.project import Project, ProjectMetadata
from app.repositories.project_repository import ProjectRepository
from app.templates.loader import TemplateLoader
from app.models.domain import Task, Artifact

logger = logging.getLogger(__name__)

class ProjectService:
    def __init__(self, project_repo: ProjectRepository, template_loader: Optional[TemplateLoader] = None):
        self.project_repo = project_repo
        self.template_loader = template_loader or TemplateLoader()

    def create_new_project(
        self, 
        root_path: Path, 
        project_name: str, 
        customer_name: str, 
        project_type: str,
        template_id: str = ""
    ) -> Project:
        """
        Creates a new project directory and initializes scaffolding.
        """
        safe_name = "".join(c if c.isalnum() else "_" for c in project_name).strip("_")
        if not safe_name:
            safe_name = "New_Project"
            
        project_dir = root_path / safe_name
        
        if project_dir.exists():
            raise FileExistsError(f"Directory already exists: {project_dir}")
            
        staging_dir = root_path / f".staging_{safe_name}"
        if staging_dir.exists():
            import shutil
            shutil.rmtree(staging_dir)
            
        staging_dir.mkdir(parents=True)
        
        try:
            metadata = ProjectMetadata.create_new(
                name=project_name, 
                customer=customer_name, 
                p_type=project_type
            )
            
            project = Project(path=str(staging_dir), metadata=metadata)
            
            # Load template if provided
            base_dirs = ["00_Inbox", "01_Planning", "02_Design", "03_Implementation", "04_Delivery"]
            if template_id:
                project.template_id = template_id
                template = self.template_loader.load_template(template_id)
                if template:
                    if template.folder_structure:
                        base_dirs = template.folder_structure
                        
                    # Copy tasks
                    for dt in template.default_tasks:
                        task = Task(
                            title=dt.title,
                            description=dt.description,
                            phase=dt.phase,
                            priority=dt.priority
                        )
                        project.tasks.append(task)
                        
                    # Initialize artifacts
                    for req_art in template.required_artifacts:
                        art = Artifact(
                            type=req_art,
                            path=""
                        )
                        project.artifacts.append(art)
            
            # Save project.json
            self.project_repo.create_project(project)
            
            # JIT Scaffolding: Create base directories
            for d in base_dirs:
                (staging_dir / d).mkdir()
                
            # Rename staging to final directory atomically
            staging_dir.rename(project_dir)
            project.path = str(project_dir)
        except Exception as e:
            import shutil
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise e
            
        logger.info(f"Created new project '{project_name}' at {project_dir} using template '{template_id}'")
        return project
