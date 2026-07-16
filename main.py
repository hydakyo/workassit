import logging
import sys
import threading
import uvicorn
import webview

from app.utils.logging_config import setup_logging
from app.repositories.settings_repository import SettingsRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.checklist_repository import ChecklistRepository

from app.services.workspace_scan_service import WorkspaceScanService
from app.services.project_service import ProjectService
from app.services.file_service import FileService
from app.services.delivery_service import DeliveryService

from app.api.server import create_app

def start_api_server(app):
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

def main() -> None:
    # 1. Init logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Project OS (Hybrid Mode)")
    
    try:
        # 2. Init repositories
        settings_repo = SettingsRepository()
        project_repo = ProjectRepository()
        audit_repo = AuditRepository()
        checklist_repo = ChecklistRepository()
        
        # 3. Init services
        scan_service = WorkspaceScanService(project_repo)
        project_service = ProjectService(project_repo)
        file_service = FileService(audit_repo)
        delivery_service = DeliveryService()
        
        # 4. Create FastAPI app
        api_app = create_app(
            settings_repo, project_repo, scan_service, project_service, 
            file_service, delivery_service, audit_repo, checklist_repo
        )
        
        # 5. Start API Server in background thread
        api_thread = threading.Thread(target=start_api_server, args=(api_app,), daemon=True)
        api_thread.start()
        
        # 6. Start PyWebView
        webview.create_window('Project OS', 'http://127.0.0.1:8000', width=1200, height=800)
        webview.start()
        
    except Exception as e:
        logger.critical(f"Application crashed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
