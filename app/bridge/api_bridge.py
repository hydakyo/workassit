import logging
import threading
import ipaddress
import uuid
from pathlib import Path
from typing import Any, Dict, List

from app.models.project import Project
from app.models.domain import Artifact, ArtifactStatus, Device, Priority, Site, Task, TaskStatus
from app.models.audit import UndoStatus
from app.services.workspace_scan_service import WorkspaceScanService
from app.services.project_service import ProjectService
from app.services.file_service import FileService
from app.services.delivery_service import DeliveryService
from app.repositories.settings_repository import SettingsRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.checklist_repository import ChecklistRepository
from app.services.ai_service import AIService
from app.services.data_scrubber import DataScrubber
from app.services.search_service import SearchService
from app.services.backup_service import BackupService
from app.services.rollout_service import RolloutService
from app.templates.loader import TemplateLoader
from app.config.settings import AI_PROVIDER_NONE, normalize_ai_provider

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
        template_loader: TemplateLoader,
        data_scrubber: DataScrubber | None = None,
        search_service: SearchService | None = None,
        backup_service: BackupService | None = None,
        rollout_service: RolloutService | None = None,
    ) -> None:
        self.settings_repo = settings_repo
        self.project_repo = project_repo
        self.scan_service = scan_service
        self.project_service = project_service
        self.file_service = file_service
        self.delivery_service = delivery_service
        self.audit_repo = audit_repo
        self.checklist_repo = checklist_repo
        self.template_loader = template_loader
        self.data_scrubber = data_scrubber or DataScrubber()
        self.search_service = search_service
        self.backup_service = backup_service or BackupService()
        self.rollout_service = rollout_service or RolloutService()
        
        self.project_registry: Dict[str, Path] = {}
        self._registry_lock = threading.RLock()
        self._project_locks: Dict[str, threading.Lock] = {}
        self._operations: Dict[str, Dict[str, str]] = {}

    def _get_project_lock(self, project_id: str) -> threading.Lock:
        with self._registry_lock:
            lock = self._project_locks.get(project_id)
            if lock is None:
                lock = threading.Lock()
                self._project_locks[project_id] = lock
            return lock

    def _resolve_project(self, project_id: str) -> Project:
        with self._registry_lock:
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
            "ai_key_configured": bool(settings.ai_api_key),
            "ai_base_url": settings.ai_base_url,
            "ai_model": settings.ai_model,
            "ai_streaming": settings.ai_streaming,
        }
        
    def update_settings(self, payload: Dict[str, Any]) -> Dict[str, str]:
        settings = self.settings_repo.load_settings()
        settings.theme = payload.get("theme", settings.theme)
        settings.workspace_roots = payload.get("workspace_roots", settings.workspace_roots)
        requested_provider = payload.get("ai_provider", settings.ai_provider)
        if not isinstance(requested_provider, str):
            raise ValueError("AI provider type must be a string.")
        settings.ai_provider = normalize_ai_provider(requested_provider)
        settings.ai_base_url = payload.get("ai_base_url", settings.ai_base_url).strip()
        settings.ai_model = payload.get("ai_model", settings.ai_model).strip()
        settings.ai_streaming = bool(payload.get("ai_streaming", settings.ai_streaming))
        
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
            registry: Dict[str, Path] = {}
            project_dicts = []
            for p in projects:
                pid = p.metadata.project_id
                if pid in registry:
                    warnings.append(f"Duplicate project ID ignored: {p.metadata.project_name}")
                    continue
                registry[pid] = Path(p.path)
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
            with self._registry_lock:
                self.project_registry = registry
            result_data["projects"] = project_dicts
            result_data["warnings"] = warnings
            event.set()
            
        def on_error(err: str) -> None:
            result_data["error"] = err
            event.set()
            
        self.scan_service.scan_workspaces_async(settings, on_complete, on_error)
        if not event.wait(timeout=60):
            raise TimeoutError("Workspace scan timed out after 60 seconds.")
        
        if "error" in result_data:
            raise Exception(result_data["error"])
            
        return result_data

    def search_projects(self, query: str) -> List[Dict[str, str]]:
        """Search the local index without exposing filesystem paths to the frontend."""
        if self.search_service is None:
            return []
        indexed_projects = self.search_service.search_projects(query)
        with self._registry_lock:
            return [
                {
                    "id": project["id"],
                    "project_name": project["name"],
                    "customer_name": project["customer"],
                    "project_type": project["type"],
                    "stage": project["stage"],
                }
                for project in indexed_projects
                if project["id"] in self.project_registry
            ]

    def get_dashboard_metrics(self) -> Dict[str, int]:
        """Return aggregate local index metrics for the dashboard."""
        if self.search_service is None:
            return {"projects": 0, "tasks_total": 0, "tasks_done": 0, "artifacts_attached": 0}
        return self.search_service.get_dashboard_metrics()

    def create_backup(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Start project backup in a background thread and return an operation ID immediately."""
        project_id = payload["project_id"]
        operation_id = str(uuid.uuid4())
        with self._registry_lock:
            self._operations[operation_id] = {"status": "running", "path": ""}

        def run_backup() -> None:
            try:
                with self._get_project_lock(project_id):
                    project = self._resolve_project(project_id)
                    backup_path = self.backup_service.create_backup(project)
                with self._registry_lock:
                    self._operations[operation_id] = {"status": "success", "path": backup_path}
            except Exception:
                logger.exception("Project backup failed for project ID %s", project_id)
                with self._registry_lock:
                    self._operations[operation_id] = {"status": "failed", "path": ""}

        threading.Thread(target=run_backup, daemon=True).start()
        return {"status": "running", "operation_id": operation_id}

    def get_operation(self, operation_id: str) -> Dict[str, str]:
        """Return the latest state of an asynchronous project operation."""
        with self._registry_lock:
            operation = self._operations.get(operation_id)
            if operation is None:
                raise ValueError("Operation ID not found.")
            return dict(operation)

    def list_backups(self, project_id: str) -> List[str]:
        """List local backups available for a project."""
        project = self._resolve_project(project_id)
        return self.backup_service.list_backups(project)

    def restore_backup(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Start a non-destructive restore into a new configured workspace directory."""
        project_id = payload["project_id"]
        backup_path = payload.get("backup_path")
        if not isinstance(backup_path, str):
            raise ValueError("Backup path is required.")
        settings = self.settings_repo.load_settings()
        if not settings.workspace_roots:
            raise ValueError("No workspace root is configured for restore.")
        operation_id = str(uuid.uuid4())
        with self._registry_lock:
            self._operations[operation_id] = {"status": "running", "path": ""}

        def run_restore() -> None:
            try:
                with self._get_project_lock(project_id):
                    project = self._resolve_project(project_id)
                    destination = self.backup_service.restore_backup(
                        project, backup_path, Path(settings.workspace_roots[0])
                    )
                with self._registry_lock:
                    self._operations[operation_id] = {"status": "success", "path": str(destination)}
            except Exception:
                logger.exception("Project restore failed for project ID %s", project_id)
                with self._registry_lock:
                    self._operations[operation_id] = {"status": "failed", "path": ""}

        threading.Thread(target=run_restore, daemon=True).start()
        return {"status": "running", "operation_id": operation_id}

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
        project_id = payload["project_id"]
        with self._get_project_lock(project_id):
            project = self._resolve_project(project_id)
            artifact_id = payload["artifact_id"]
            file_path = payload["file_path"]
            target_art = next((a for a in project.artifacts if a.artifact_id == artifact_id), None)
            if not target_art:
                raise ValueError("Artifact ID not found in project.")

            rel_path = self.file_service.import_file_for_artifact(project, file_path)
            if not rel_path:
                raise RuntimeError("Artifact import failed; project metadata was not changed.")

            target_art.path = rel_path
            self.project_repo.save_project(project)
            return {"status": "success", "path": rel_path}

    def undo_import(self, payload: Dict[str, Any]) -> Dict[str, str]:
        project_id = payload["project_id"]
        with self._get_project_lock(project_id):
            project = self._resolve_project(project_id)
            result = self.file_service.undo_last_import(project)
            if result.status != UndoStatus.SUCCESS:
                raise RuntimeError(f"Undo failed: {result.status.value}")
            return {"status": "success"}

    def create_package(self, payload: Dict[str, Any]) -> Dict[str, str]:
        project_id = payload["project_id"]
        with self._get_project_lock(project_id):
            project = self._resolve_project(project_id)
            path = self.delivery_service.create_delivery_package(project)
            if not path:
                raise RuntimeError("Failed to create package")
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

    def get_project_details(self, project_id: str) -> Dict[str, Any]:
        """Return editable project metadata and lifecycle data for the selected project."""
        import dataclasses

        project = self._resolve_project(project_id)
        return {
            "metadata": dataclasses.asdict(project.metadata),
            "phases": [dataclasses.asdict(phase) for phase in project.phases],
            "sites": [dataclasses.asdict(site) for site in project.sites],
            "devices": [dataclasses.asdict(device) for device in project.devices],
            "deliveries": [dataclasses.asdict(delivery) for delivery in project.deliveries],
        }

    def update_project_metadata(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Update the user-editable project metadata without moving project files."""
        project_id = payload["project_id"]
        allowed_stages = {"planning", "active", "blocked", "closed", "archived"}
        with self._get_project_lock(project_id):
            project = self._resolve_project(project_id)
            for field_name in ("project_name", "customer_name", "project_type"):
                value = payload.get(field_name)
                if value is not None:
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(f"{field_name} must be a non-empty string.")
                    setattr(project.metadata, field_name, value.strip())
            stage = payload.get("stage")
            if stage is not None:
                if stage not in allowed_stages:
                    raise ValueError("Invalid project stage.")
                project.metadata.stage = stage
            self.project_repo.save_project(project)
        return {"status": "success"}

    def create_task(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Create a task in the selected project."""
        project_id = payload["project_id"]
        title = payload.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Task title is required.")
        try:
            priority = Priority(payload.get("priority", Priority.MEDIUM.value))
        except ValueError as exc:
            raise ValueError("Invalid task priority.") from exc
        with self._get_project_lock(project_id):
            project = self._resolve_project(project_id)
            task = Task(
                title=title.strip(),
                description=str(payload.get("description", "")),
                priority=priority.value,
                owner=payload.get("owner"),
                due_date=payload.get("due_date"),
                phase=payload.get("phase"),
            )
            project.tasks.append(task)
            self.project_repo.save_project(project)
        return {"status": "success", "task_id": task.id}

    def update_task(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Update the editable fields of a single task."""
        project_id = payload["project_id"]
        task_id = payload.get("task_id")
        if not isinstance(task_id, str):
            raise ValueError("Task ID is required.")
        with self._get_project_lock(project_id):
            project = self._resolve_project(project_id)
            task = next((item for item in project.tasks if item.id == task_id), None)
            if task is None:
                raise ValueError("Task ID not found in project.")
            if "title" in payload:
                title = payload["title"]
                if not isinstance(title, str) or not title.strip():
                    raise ValueError("Task title must be a non-empty string.")
                task.title = title.strip()
            if "status" in payload:
                try:
                    task.status = TaskStatus(payload["status"]).value
                except ValueError as exc:
                    raise ValueError("Invalid task status.") from exc
            if "priority" in payload:
                try:
                    task.priority = Priority(payload["priority"]).value
                except ValueError as exc:
                    raise ValueError("Invalid task priority.") from exc
            for field_name in ("description", "owner", "due_date", "phase", "category"):
                if field_name in payload:
                    setattr(task, field_name, payload[field_name])
            self.project_repo.save_project(project)
        return {"status": "success"}

    def delete_task(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Remove a task record without deleting any project files."""
        project_id = payload["project_id"]
        task_id = payload.get("task_id")
        if not isinstance(task_id, str):
            raise ValueError("Task ID is required.")
        with self._get_project_lock(project_id):
            project = self._resolve_project(project_id)
            remaining_tasks = [task for task in project.tasks if task.id != task_id]
            if len(remaining_tasks) == len(project.tasks):
                raise ValueError("Task ID not found in project.")
            project.tasks = remaining_tasks
            self.project_repo.save_project(project)
        return {"status": "success"}

    def create_artifact(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Add a required artifact record; file attachment remains a separate explicit action."""
        project_id = payload["project_id"]
        artifact_type = payload.get("type")
        if not isinstance(artifact_type, str) or not artifact_type.strip():
            raise ValueError("Artifact type is required.")
        with self._get_project_lock(project_id):
            project = self._resolve_project(project_id)
            artifact = Artifact(type=artifact_type.strip(), path="", owner=payload.get("owner"))
            project.artifacts.append(artifact)
            self.project_repo.save_project(project)
        return {"status": "success", "artifact_id": artifact.artifact_id}

    def update_artifact(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Update approval metadata of an artifact without changing its attached file."""
        project_id = payload["project_id"]
        artifact_id = payload.get("artifact_id")
        if not isinstance(artifact_id, str):
            raise ValueError("Artifact ID is required.")
        with self._get_project_lock(project_id):
            project = self._resolve_project(project_id)
            artifact = next((item for item in project.artifacts if item.artifact_id == artifact_id), None)
            if artifact is None:
                raise ValueError("Artifact ID not found in project.")
            if "status" in payload:
                try:
                    artifact.status = ArtifactStatus(payload["status"]).value
                except ValueError as exc:
                    raise ValueError("Invalid artifact status.") from exc
            for field_name in ("owner", "version"):
                if field_name in payload:
                    value = payload[field_name]
                    if not isinstance(value, str):
                        raise ValueError(f"{field_name} must be a string.")
                    setattr(artifact, field_name, value)
            self.project_repo.save_project(project)
        return {"status": "success"}

    def delete_artifact(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Remove artifact metadata while intentionally retaining any attached file on disk."""
        project_id = payload["project_id"]
        artifact_id = payload.get("artifact_id")
        if not isinstance(artifact_id, str):
            raise ValueError("Artifact ID is required.")
        with self._get_project_lock(project_id):
            project = self._resolve_project(project_id)
            remaining_artifacts = [artifact for artifact in project.artifacts if artifact.artifact_id != artifact_id]
            if len(remaining_artifacts) == len(project.artifacts):
                raise ValueError("Artifact ID not found in project.")
            project.artifacts = remaining_artifacts
            self.project_repo.save_project(project)
        return {"status": "success"}

    def create_site(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Create a rollout site in the selected project."""
        project_id = payload["project_id"]
        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Site name is required.")
        with self._get_project_lock(project_id):
            project = self._resolve_project(project_id)
            site = Site(name=name.strip(), location=str(payload.get("location", "")), contact=payload.get("contact"))
            project.sites.append(site)
            self.project_repo.save_project(project)
        return {"status": "success", "site_id": site.site_id}

    def create_device(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Create a device assigned to an existing site with validated management IP."""
        project_id = payload["project_id"]
        site_id = payload.get("site_id")
        serial_number = payload.get("serial_number")
        if not isinstance(site_id, str) or not isinstance(serial_number, str) or not serial_number.strip():
            raise ValueError("Site ID and serial number are required.")
        management_ip = str(payload.get("management_ip", ""))
        if management_ip:
            try:
                ipaddress.ip_address(management_ip)
            except ValueError as exc:
                raise ValueError("Invalid management IP address.") from exc
        with self._get_project_lock(project_id):
            project = self._resolve_project(project_id)
            if not any(site.site_id == site_id for site in project.sites):
                raise ValueError("Site ID not found in project.")
            if any(device.serial_number == serial_number.strip() for device in project.devices):
                raise ValueError("Device serial number already exists in project.")
            device = Device(
                site_id=site_id,
                serial_number=serial_number.strip(),
                current_hostname=str(payload.get("current_hostname", "")),
                target_hostname=str(payload.get("target_hostname", "")),
                model=str(payload.get("model", "")),
                management_ip=management_ip,
                firmware=str(payload.get("firmware", "")),
                deployment_wave=str(payload.get("deployment_wave", "")),
            )
            project.devices.append(device)
            self.project_repo.save_project(project)
        return {"status": "success", "device_id": device.device_id}

    def delete_site(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Remove an empty site; devices must be reassigned or removed explicitly first."""
        project_id = payload["project_id"]
        site_id = payload.get("site_id")
        if not isinstance(site_id, str):
            raise ValueError("Site ID is required.")
        with self._get_project_lock(project_id):
            project = self._resolve_project(project_id)
            if any(device.site_id == site_id for device in project.devices):
                raise ValueError("Remove or reassign devices before deleting this site.")
            remaining_sites = [site for site in project.sites if site.site_id != site_id]
            if len(remaining_sites) == len(project.sites):
                raise ValueError("Site ID not found in project.")
            project.sites = remaining_sites
            self.project_repo.save_project(project)
        return {"status": "success"}

    def update_device(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Update deployment state or inventory fields of a device."""
        project_id = payload["project_id"]
        device_id = payload.get("device_id")
        if not isinstance(device_id, str):
            raise ValueError("Device ID is required.")
        allowed_statuses = {"Pending", "Passed", "Failed", "Blocked", "Not Applicable"}
        with self._get_project_lock(project_id):
            project = self._resolve_project(project_id)
            device = next((item for item in project.devices if item.device_id == device_id), None)
            if device is None:
                raise ValueError("Device ID not found in project.")
            if "management_ip" in payload:
                management_ip = str(payload["management_ip"])
                if management_ip:
                    try:
                        ipaddress.ip_address(management_ip)
                    except ValueError as exc:
                        raise ValueError("Invalid management IP address.") from exc
                device.management_ip = management_ip
            for field_name in ("current_hostname", "target_hostname", "model", "firmware", "deployment_wave"):
                if field_name in payload:
                    device_value = payload[field_name]
                    if not isinstance(device_value, str):
                        raise ValueError(f"{field_name} must be a string.")
                    setattr(device, field_name, device_value)
            for field_name in ("pre_check_status", "implementation_status", "post_check_status", "uat_status"):
                if field_name in payload:
                    status = payload[field_name]
                    if status not in allowed_statuses:
                        raise ValueError(f"Invalid {field_name}.")
                    setattr(device, field_name, status)
            self.project_repo.save_project(project)
        return {"status": "success"}

    def delete_device(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Remove a device record without deleting any external inventory source."""
        project_id = payload["project_id"]
        device_id = payload.get("device_id")
        if not isinstance(device_id, str):
            raise ValueError("Device ID is required.")
        with self._get_project_lock(project_id):
            project = self._resolve_project(project_id)
            remaining_devices = [device for device in project.devices if device.device_id != device_id]
            if len(remaining_devices) == len(project.devices):
                raise ValueError("Device ID not found in project.")
            project.devices = remaining_devices
            self.project_repo.save_project(project)
        return {"status": "success"}

    def import_devices_csv(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Start a transactional CSV inventory import in a background operation."""
        project_id = payload["project_id"]
        source_path = payload.get("source_path")
        if not isinstance(source_path, str):
            raise ValueError("CSV source path is required.")
        operation_id = str(uuid.uuid4())
        with self._registry_lock:
            self._operations[operation_id] = {"status": "running", "path": ""}

        def run_import() -> None:
            try:
                with self._get_project_lock(project_id):
                    project = self._resolve_project(project_id)
                    imported_count = self.rollout_service.import_devices_csv(project, source_path)
                    self.project_repo.save_project(project)
                with self._registry_lock:
                    self._operations[operation_id] = {"status": "success", "path": str(imported_count)}
            except Exception:
                logger.exception("Device CSV import failed for project ID %s", project_id)
                with self._registry_lock:
                    self._operations[operation_id] = {"status": "failed", "path": ""}

        threading.Thread(target=run_import, daemon=True).start()
        return {"status": "running", "operation_id": operation_id}

    def update_checklist(self, payload: Dict[str, Any]) -> Dict[str, str]:
        # Handle updating a specific task status
        project_id = payload["project_id"]
        task_id = payload.get("task_id")
        new_status = payload.get("status")
        if not isinstance(task_id, str) or not isinstance(new_status, str):
            raise ValueError("Task ID and status are required.")
        try:
            validated_status = TaskStatus(new_status)
        except ValueError as exc:
            raise ValueError("Invalid task status.") from exc
        with self._get_project_lock(project_id):
            project = self._resolve_project(project_id)
            task = next((item for item in project.tasks if item.id == task_id), None)
            if task is None:
                raise ValueError("Task ID not found in project.")
            task.status = validated_status.value
            self.project_repo.save_project(project)
            return {"status": "success"}

    def get_audit(self, project_id: str) -> List[str]:
        with self._registry_lock:
            if project_id not in self.project_registry:
                raise ValueError("Invalid project ID")
            project_path = self.project_registry[project_id]
        logs = self.audit_repo.read_logs(project_path)
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

    def preview_ai_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Return the exact redacted project context that would be sent to the configured cloud provider."""
        project = self._resolve_project(payload["project_id"])
        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("AI prompt is required.")
        settings = self.settings_repo.load_settings()
        if settings.ai_provider == AI_PROVIDER_NONE:
            raise ValueError("AI provider is not configured.")
        redacted_context = self.data_scrubber.scrub(self._build_project_context(project))
        redacted_prompt = self.data_scrubber.scrub(prompt)
        request_payload = f"{redacted_context}\n---\nUser request: {redacted_prompt}"
        return {
            "provider": settings.ai_provider,
            "endpoint": settings.ai_base_url or "Provider default endpoint",
            "model": settings.ai_model,
            "payload_preview": request_payload,
            "characters": len(request_payload),
            "warning": "Only the redacted preview shown here will be sent to the configured cloud provider.",
        }

    def analyze_project(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        project = self._resolve_project(payload["project_id"])
        settings = self.settings_repo.load_settings()
        if settings.ai_provider == AI_PROVIDER_NONE:
            raise Exception("AI provider not configured. Go to Settings to add an API key.")

        ai_service = AIService(
            settings.ai_provider,
            settings.ai_api_key,
            settings.ai_base_url,
            settings.ai_model,
            settings.ai_streaming,
        )
        context = self.data_scrubber.scrub(self._build_project_context(project))

        system_prompt = (
            "You are a senior IT Project Manager assistant. "
            "You are reviewing a project's current status. "
            "Answer in the same language the user uses. "
            "Be concise, actionable, and data-driven based on the context below.\n\n"
            f"{context}\n"
        )
        full_prompt = f"{system_prompt}---\nUser request: {self.data_scrubber.scrub(payload['prompt'])}"
        result = ai_service.analyze_project(full_prompt)
        return {"result": result}
