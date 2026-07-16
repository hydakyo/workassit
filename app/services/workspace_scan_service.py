import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Callable, Optional

from app.models.project import Project
from app.repositories.project_repository import ProjectRepository
from app.config.settings import AppSettings
from app.utils.path_validator import normalize_path
from app.database.indexer import Indexer

logger = logging.getLogger(__name__)

class WorkspaceScanService:
    def __init__(self, project_repo: ProjectRepository, indexer: Optional[Indexer] = None):
        self.project_repo = project_repo
        self.indexer = indexer
        self.executor = ThreadPoolExecutor(max_workers=1)

    def scan_workspaces_async(
        self, 
        settings: AppSettings, 
        on_complete: Callable[[List[Project], List[str]], None],
        on_error: Callable[[str], None]
    ) -> None:
        """
        Scans workspace roots in the background.
        """
        def scan_task() -> None:
            try:
                projects: List[Project] = []
                warnings: List[str] = []
                
                for root_str in settings.workspace_roots:
                    root_path = normalize_path(root_str)
                    
                    if not root_path.is_dir():
                        warnings.append(f"Workspace root not found or not a directory: {root_path}")
                        continue
                        
                    try:
                        # Iterate top-level directories in the workspace root
                        # Do not use rglob to avoid infinite recursion and slow scans
                        for entry in root_path.iterdir():
                            if entry.is_dir():
                                try:
                                    project = self.project_repo.read_project(entry)
                                    if project:
                                        projects.append(project)
                                        if self.indexer:
                                            self.indexer.sync_project(project)
                                except ValueError as ve:
                                    warnings.append(f"Corrupt project in {entry.name}: {ve}")
                    except OSError as e:
                        warnings.append(f"Error accessing directory {root_path}: {e}")
                        
                on_complete(projects, warnings)
            except Exception as e:
                logger.error(f"Scan failed: {e}", exc_info=True)
                on_error(str(e))

        self.executor.submit(scan_task)
        
    def shutdown(self) -> None:
        self.executor.shutdown(wait=False)
