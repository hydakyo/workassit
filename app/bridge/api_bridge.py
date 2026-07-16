import uuid
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List

from app.models.project import Project
from app.services.workspace_scan_service import WorkspaceScanService
from app.services.project_service import ProjectService
from app.services.file_service import FileService
from app.services.delivery_service import DeliveryService
from app.repositories.settings_repository import SettingsRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.checklist_repository import ChecklistRepository
from app.services.ai_service import AIService
from app.templates.loader import TemplateLoader

logger = logging.getLogger(__name__)

class ApiBridge:
    def __init__(
        self,
        settings_repo: SettingsRepository,
        project_repo: ProjectRepository,
        scan_service: WorkspaceScanService,
        project_service: ProjectService,
        file_service: FileService,
        delivery_service: DeliveryService,
        audit_repo: AuditRepository,
        checklist_repo: ChecklistRepository,
        template_loader: TemplateLoader
    ):
        self.settings_repo = settings_repo
        self.project_repo = project_repo
        self.scan_service = scan_service
        self.project_service = project_service
        self.file_service = file_service
        self.delivery_service = delivery_service
        self.audit_repo = audit_repo
        self.checklist_repo = checklist_repo
        self.template_loader = template_loader
        
        self.project_registry: Dict[str, Path] = {}

    def _resolve_project(self, project_id: str) -> Project:
        if project_id not in self.project_registry:
            raise ValueError("Project ID not found or invalid.")
        path = self.project_registry[project_id]
        project = self.project_repo.read_project(path)
        if not project:
            raise ValueError("Project not found at path.")
        return project

    def get_settings(self) -> Dict[str, Any]:
        settings = self.settings_repo.load_settings()
        return {
            "theme": settings.theme,
            "workspace_roots": settings.workspace_roots,
            "ai_provider": settings.ai_provider,
            "ai_key_configured": bool(settings.ai_api_key)
        }
        
    def update_settings(self, payload: Dict[str, Any]) -> Dict[str, str]:
        settings = self.settings_repo.load_settings()
        settings.theme = payload.get("theme", settings.theme)
        settings.workspace_roots = payload.get("workspace_roots", settings.workspace_roots)
        settings.ai_provider = payload.get("ai_provider", settings.ai_provider)
        
        new_key = payload.get("ai_api_key")
        if new_key:
            settings.ai_api_key = new_key
            
        self.settings_repo.save_settings(settings)
        return {"status": "success"}

    def scan_projects(self) -> Dict[str, Any]:
        settings = self.settings_repo.load_settings()
        event = threading.Event()
        result_data: Dict[str, Any] = {}
        
        def on_complete(projects: List[Project], warnings: List[str]) -> None:
            self.project_registry.clear()
            project_dicts = []
            for p in projects:
                pid = str(uuid.uuid4())
                self.project_registry[pid] = Path(p.path)
                project_dicts.append({
                    "id": pid,
                    "metadata": {
                        "project_name": p.metadata.project_name,
                        "customer_name": p.metadata.customer_name,
                        "project_type": p.metadata.project_type,
                        "stage": p.metadata.stage,
                        "updated_at": p.metadata.updated_at
                    }
                })
            result_data["projects"] = project_dicts
            result_data["warnings"] = warnings
            event.set()
            
        def on_error(err: str) -> None:
            result_data["error"] = err
            event.set()
            
        self.scan_service.scan_workspaces_async(settings, on_complete, on_error)
        event.wait()
        
        if "error" in result_data:
            raise Exception(result_data["error"])
            
        return result_data

    def create_project(self, payload: Dict[str, Any]) -> Dict[str, str]:
        settings = self.settings_repo.load_settings()
        if not settings.workspace_roots:
            raise Exception("No workspace roots configured")
            
        root_path = Path(settings.workspace_roots[0])
        self.project_service.create_new_project(
            root_path=root_path,
            project_name=payload["name"],
            customer_name=payload["customer"],
            project_type=payload["project_type"],
            template_id=payload.get("template_id", "")
        )
        return {"status": "success"}

    def get_templates(self) -> List[Dict[str, str]]:
        return self.template_loader.list_templates()


    def open_file_dialog(self) -> str:
        import webview
        if webview.windows:
            window = webview.windows[0]
            result = window.create_file_dialog(webview.OPEN_DIALOG)
            if result and len(result) > 0:
                if isinstance(result[0], str):
                    return result[0]
        return ""

    def attach_artifact(self, payload: Dict[str, Any]) -> Dict[str, str]:
        project = self._resolve_project(payload["project_id"])
        artifact_type = payload["artifact_type"]
        file_path = payload["file_path"]
        
        # Find artifact
        target_art = next((a for a in project.artifacts if a.type == artifact_type), None)
        if not target_art:
            raise Exception("Artifact type not found in project")
            
        rel_path = self.file_service.import_file_for_artifact(project, file_path)
        if not rel_path:
            raise Exception("Failed to import file")
            
        # Update artifact
        target_art.path = rel_path
        target_art.status = "Completed"
        
        # Save project
        self.project_repo.save_project(project)
        
        return {"status": "success", "path": rel_path}

    def undo_import(self, payload: Dict[str, Any]) -> Dict[str, str]:
        project = self._resolve_project(payload["project_id"])
        success = self.file_service.undo_last_import(project)
        if not success:
            raise Exception("Nothing to undo or failed")
        return {"status": "success"}

    def create_package(self, payload: Dict[str, Any]) -> Dict[str, str]:
        project = self._resolve_project(payload["project_id"])
        path = self.delivery_service.create_delivery_package(project)
        if not path:
            raise Exception("Failed to create package")
        self.project_repo.save_project(project)
        return {"status": "success", "path": path}

    def get_checklist(self, project_id: str) -> Dict[str, Any]:
        project = self._resolve_project(project_id)
        # Convert dataclasses to dict
        import dataclasses
        tasks = [dataclasses.asdict(t) for t in project.tasks]
        artifacts = [dataclasses.asdict(a) for a in project.artifacts]
        return {
            "tasks": tasks,
            "artifacts": artifacts
        }

    def update_checklist(self, payload: Dict[str, Any]) -> Dict[str, str]:
        # Handle updating a specific task status
        project_id = payload["project_id"]
        project = self._resolve_project(project_id)
        
        task_id = payload.get("task_id")
        new_status = payload.get("status")
        
        if task_id and new_status:
            for t in project.tasks:
                if getattr(t, 'id', None) == task_id or getattr(t, 'title', None) == task_id: # Fallback to title
                    t.status = new_status
            self.project_repo.save_project(project)
            
        return {"status": "success"}

    def get_audit(self, project_id: str) -> List[str]:
        if project_id not in self.project_registry:
            raise ValueError("Invalid project ID")
        logs = self.audit_repo.read_logs(self.project_registry[project_id])
        return [f"[{log.timestamp}] {log.action}: {log.file_name} (by {log.user})" for log in reversed(logs)]

    def _build_project_context(self, project: Project) -> str:
        """Build a rich Markdown context string from project data for AI prompts."""
        lines: List[str] = []
        m = project.metadata
        lines.append(f"# Project: {m.project_name}")
        lines.append(f"- **Customer:** {m.customer_name}")
        lines.append(f"- **Type:** {m.project_type}")
        lines.append(f"- **Stage:** {m.stage}")
        lines.append(f"- **Last Updated:** {m.updated_at}")
        lines.append("")

        # Task statistics
        total = len(project.tasks)
        done = sum(1 for t in project.tasks if t.status == "Done")
        in_progress = sum(1 for t in project.tasks if t.status == "In Progress")
        todo = total - done - in_progress
        pct = round(done / total * 100) if total > 0 else 0
        lines.append(f"## Task Progress ({pct}% complete)")
        lines.append("| Status | Count |")
        lines.append("|---|---|")
        lines.append(f"| Done | {done} |")
        lines.append(f"| In Progress | {in_progress} |")
        lines.append(f"| To Do | {todo} |")
        lines.append(f"| **Total** | **{total}** |")
        lines.append("")

        # Per-task detail
        if project.tasks:
            lines.append("### Task List")
            for t in project.tasks:
                icon = "✅" if t.status == "Done" else ("🔄" if t.status == "In Progress" else "⬜")
                lines.append(f"- {icon} [{t.status}] **{t.title}** (Phase: {t.phase or 'N/A'}, Priority: {t.priority})")
            lines.append("")

        # Artifact status
        art_total = len(project.artifacts)
        art_done = sum(1 for a in project.artifacts if a.path)
        lines.append(f"## Artifacts ({art_done}/{art_total} attached)")
        for a in project.artifacts:
            status_icon = "📎" if a.path else "❌"
            lines.append(f"- {status_icon} **{a.type}**: {a.status} — {a.path or 'Not submitted'}")
        lines.append("")

        # Recent audit log (last 5)
        try:
            if project.path:
                audit_logs = self.audit_repo.read_logs(Path(project.path))
                if audit_logs:
                    lines.append("## Recent Activity (last 5)")
                    for log in list(reversed(audit_logs))[:5]:
                        lines.append(f"- [{log.timestamp}] {log.action}: {log.file_name}")
                    lines.append("")
        except Exception:
            pass  # Non-critical

        # Deliveries
        if project.deliveries:
            lines.append(f"## Deliveries ({len(project.deliveries)} releases)")
            for d in project.deliveries:
                lines.append(f"- v{d.version} — {d.generated_time} — {d.approval_state}")
            lines.append("")

        return "\n".join(lines)

    def analyze_project(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        project = self._resolve_project(payload["project_id"])
        settings = self.settings_repo.load_settings()
        if settings.ai_provider == "None":
            raise Exception("AI provider not configured. Go to Settings to add an API key.")

        ai_service = AIService(settings.ai_provider, settings.ai_api_key)
        context = self._build_project_context(project)

        system_prompt = (
            "You are a senior IT Project Manager assistant. "
            "You are reviewing a project's current status. "
            "Answer in the same language the user uses. "
            "Be concise, actionable, and data-driven based on the context below.\n\n"
            f"{context}\n"
        )
        full_prompt = f"{system_prompt}---\nUser request: {payload['prompt']}"
        result = ai_service.analyze_project(full_prompt)
        return {"result": result}
