import logging
import sys

from app.utils.logging_config import setup_logging
from app.repositories.settings_repository import SettingsRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.checklist_repository import ChecklistRepository
from app.services.workspace_scan_service import WorkspaceScanService
from app.services.project_service import ProjectService
from app.services.file_service import FileService
from app.services.delivery_service import DeliveryService
from app.ui.main_window import MainWindow

def main() -> None:
    # 1. Init logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Project OS")
    
    try:
        # 2. Init repositories
        settings_repo = SettingsRepository()
        settings = settings_repo.load_settings()
        
        # 1. UI Config
        import customtkinter as ctk
        ctk.set_appearance_mode(settings.theme)
        ctk.set_default_color_theme("blue")
        
        project_repo = ProjectRepository()
        audit_repo = AuditRepository()
        checklist_repo = ChecklistRepository()
        
        # 3. Init services
        scan_service = WorkspaceScanService(project_repo)
        project_service = ProjectService(project_repo)
        file_service = FileService(audit_repo)
        delivery_service = DeliveryService()
        
        # 4. Init UI
        app = MainWindow(settings_repo, project_repo, scan_service, project_service, file_service, delivery_service, audit_repo, checklist_repo)
        
        # 5. Run mainloop
        app.mainloop()
    except Exception as e:
        logger.critical(f"Application crashed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
