import logging
import uuid
from pathlib import Path
from typing import Optional

from app.models.project import Project, ProjectMetadata
from app.repositories.project_repository import ProjectRepository
from app.templates.loader import TemplateLoader
from app.models.domain import Task, Artifact
from app.utils.atomic_json import write_json_atomic
from app.utils.path_validator import resolve_project_path

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
            
        staging_root = resolve_project_path(root_path, ".projectos/staging")
        staging_root.mkdir(parents=True, exist_ok=True)
        operation_id = str(uuid.uuid4())
        staging_dir = resolve_project_path(root_path, f".projectos/staging/{operation_id}")
        staging_dir.mkdir()
        manifest_path = resolve_project_path(root_path, f".projectos/staging/{operation_id}.json")
        write_json_atomic(
            manifest_path,
            {"operation_id": operation_id, "operation": "create_project", "project_name": project_name},
        )
        
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
                    project.phases = [
                        type(phase)(
                            name=phase.name,
                            description=phase.description,
                            entry_criteria=list(phase.entry_criteria),
                            exit_criteria=list(phase.exit_criteria),
                            required_artifacts=list(phase.required_artifacts),
                            approval_status=phase.approval_status,
                            blocking_issues=list(phase.blocking_issues),
                        )
                        for phase in template.phases
                    ]
                        
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
            manifest_path.unlink()
            project.path = str(project_dir)
        except Exception:
            logger.exception("Project creation interrupted; staging operation %s was retained.", operation_id)
            raise
            
        logger.info(f"Created new project '{project_name}' at {project_dir} using template '{template_id}'")
        return project
