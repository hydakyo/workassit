import asyncio
from typing import List, Dict, Any, cast
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.models.project import Project
from app.models.checklist import ChecklistItem
from app.config.settings import AppSettings
from app.services.ai_service import AIService
from app.repositories.settings_repository import SettingsRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.checklist_repository import ChecklistRepository
from app.services.workspace_scan_service import WorkspaceScanService
from app.services.project_service import ProjectService
from app.services.file_service import FileService
from app.services.delivery_service import DeliveryService

def create_app(
    settings_repo: SettingsRepository, 
    project_repo: ProjectRepository, 
    scan_service: WorkspaceScanService, 
    project_service: ProjectService, 
    file_service: FileService, 
    delivery_service: DeliveryService, 
    audit_repo: AuditRepository, 
    checklist_repo: ChecklistRepository
) -> FastAPI:
    app = FastAPI(title="Project OS API")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.state.settings_repo = settings_repo
    app.state.project_repo = project_repo
    app.state.scan_service = scan_service
    app.state.project_service = project_service
    app.state.file_service = file_service
    app.state.delivery_service = delivery_service
    app.state.audit_repo = audit_repo
    app.state.checklist_repo = checklist_repo

    # --- API ROUTES ---

    @app.get("/api/settings")
    def get_settings(request: Request) -> AppSettings:
        return cast(AppSettings, request.app.state.settings_repo.load_settings())
        
    class SettingsUpdate(BaseModel):
        theme: str
        workspace_roots: List[str]
        ai_provider: str
        ai_api_key: str
        
    @app.post("/api/settings")
    def update_settings(request: Request, update: SettingsUpdate) -> Dict[str, str]:
        settings = cast(AppSettings, request.app.state.settings_repo.load_settings())
        settings.theme = update.theme
        settings.workspace_roots = update.workspace_roots
        settings.ai_provider = update.ai_provider
        settings.ai_api_key = update.ai_api_key
        request.app.state.settings_repo.save_settings(settings)
        return {"status": "success"}

    @app.get("/api/projects/scan")
    async def scan_projects(request: Request) -> Any:
        scan_service = cast(WorkspaceScanService, request.app.state.scan_service)
        settings = cast(AppSettings, request.app.state.settings_repo.load_settings())
        
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        
        def on_complete(projects: List[Project], warnings: List[str]) -> None:
            loop.call_soon_threadsafe(future.set_result, {"projects": projects, "warnings": warnings})
            
        def on_error(err: str) -> None:
            loop.call_soon_threadsafe(future.set_exception, Exception(err))
            
        scan_service.scan_workspaces_async(settings, on_complete, on_error)
        
        try:
            return await future
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    class ProjectCreate(BaseModel):
        name: str
        customer: str
        project_type: str
        
    @app.post("/api/projects")
    def create_project(request: Request, data: ProjectCreate) -> Dict[str, str]:
        settings = cast(AppSettings, request.app.state.settings_repo.load_settings())
        if not settings.workspace_roots:
            raise HTTPException(status_code=400, detail="No workspace roots configured")
            
        root_path = Path(settings.workspace_roots[0])
        try:
            request.app.state.project_service.create_new_project(
                root_path=root_path,
                project_name=data.name,
                customer_name=data.customer,
                project_type=data.project_type
            )
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def _get_project_by_path(request: Request, path: str) -> Project:
        try:
            project = request.app.state.project_repo.read_project(Path(path))
            if not project:
                raise ValueError()
            return cast(Project, project)
        except ValueError:
            raise HTTPException(status_code=404, detail="Project not found")

    class ImportRequest(BaseModel):
        project_path: str
        file_path: str
        
    @app.post("/api/projects/import")
    def import_file(request: Request, data: ImportRequest) -> Dict[str, str]:
        project = _get_project_by_path(request, data.project_path)
        success = request.app.state.file_service.import_file(project, data.file_path)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to import file")
        return {"status": "success"}

    class ActionRequest(BaseModel):
        project_path: str

    @app.post("/api/projects/undo")
    def undo_import(request: Request, data: ActionRequest) -> Dict[str, str]:
        project = _get_project_by_path(request, data.project_path)
        success = request.app.state.file_service.undo_last_import(project)
        if not success:
            raise HTTPException(status_code=400, detail="Nothing to undo or failed")
        return {"status": "success"}

    @app.post("/api/projects/package")
    def create_package(request: Request, data: ActionRequest) -> Dict[str, str]:
        project = _get_project_by_path(request, data.project_path)
        path = request.app.state.delivery_service.create_delivery_package(project)
        if not path:
            raise HTTPException(status_code=500, detail="Failed to create package")
        return {"status": "success", "path": path}

    @app.get("/api/projects/checklist")
    def get_checklist(request: Request, project_path: str) -> List[ChecklistItem]:
        items = request.app.state.checklist_repo.load_checklist(Path(project_path))
        return cast(List[ChecklistItem], items)

    class ChecklistUpdate(BaseModel):
        project_path: str
        items: List[Dict[str, Any]]

    @app.post("/api/projects/checklist")
    def update_checklist(request: Request, data: ChecklistUpdate) -> Dict[str, str]:
        items = [ChecklistItem(**item) for item in data.items]
        request.app.state.checklist_repo.save_checklist(Path(data.project_path), items)
        return {"status": "success"}

    @app.get("/api/projects/audit")
    def get_audit(request: Request, project_path: str) -> List[str]:
        logs = request.app.state.audit_repo.read_logs(Path(project_path))
        return list(reversed(logs))

    class AnalyzeRequest(BaseModel):
        project_path: str
        prompt: str

    @app.post("/api/projects/analyze")
    def analyze_project(request: Request, data: AnalyzeRequest) -> Dict[str, Any]:
        settings = cast(AppSettings, request.app.state.settings_repo.load_settings())
        if settings.ai_provider == "None":
            raise HTTPException(status_code=400, detail="AI provider not configured")
            
        ai_service = AIService(settings.ai_provider, settings.ai_api_key)
        result = ai_service.analyze_project(data.prompt)
        return {"result": result}

    # Mount static web files (if web folder exists)
    web_dir = Path(__file__).parent.parent.parent / "web"
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")
        
    return app
