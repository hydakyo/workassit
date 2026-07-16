import logging
import sys
import webview
from pathlib import Path

from app.utils.logging_config import setup_logging
from app.repositories.settings_repository import SettingsRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.checklist_repository import ChecklistRepository

from app.services.workspace_scan_service import WorkspaceScanService
from app.services.project_service import ProjectService
from app.services.file_service import FileService
from app.services.delivery_service import DeliveryService

from app.bridge.api_bridge import ApiBridge

def main() -> None:
    # 1. Init logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Project OS (JS Bridge Mode)")
    
    try:
        # 2. Init repositories
        settings_repo = SettingsRepository()
        project_repo = ProjectRepository()
        audit_repo = AuditRepository()
        checklist_repo = ChecklistRepository()
        
        # 2.5 Init Database and Templates
        from app.database.connection import DatabaseManager
        from app.database.indexer import Indexer
        from app.templates.loader import TemplateLoader
        
        db_manager = DatabaseManager()
        indexer = Indexer(db_manager)
        template_loader = TemplateLoader()
        
        # 3. Init services
        scan_service = WorkspaceScanService(project_repo, indexer)
        project_service = ProjectService(project_repo, template_loader)
        file_service = FileService(audit_repo)
        delivery_service = DeliveryService()
        
        # 4. Create Api Bridge
        api_bridge = ApiBridge(
            settings_repo, project_repo, scan_service, project_service, 
            file_service, delivery_service, audit_repo, checklist_repo,
            template_loader
        )
        
        # 5. Start PyWebView
        html_path = str(Path(__file__).parent / 'web' / 'index.html')
        webview.create_window('Project OS', url=html_path, js_api=api_bridge, width=1200, height=800)
        webview.start(debug=True)
        
    except Exception as e:
        logger.critical(f"Application crashed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
