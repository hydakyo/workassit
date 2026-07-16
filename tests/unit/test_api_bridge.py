from pathlib import Path

from app.bridge.api_bridge import ApiBridge
from app.config.settings import AppSettings
from app.models.project import Project, ProjectMetadata
from app.repositories.audit_repository import AuditRepository
from app.repositories.checklist_repository import ChecklistRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.settings_repository import SettingsRepository
from app.services.delivery_service import DeliveryService
from app.services.file_service import FileService
from app.services.project_service import ProjectService
from app.templates.loader import TemplateLoader


class ImmediateScanService:
    def __init__(self, project: Project) -> None:
        self.project = project

    def scan_workspaces_async(self, settings, on_complete, on_error) -> None:
        on_complete([self.project], [])


def test_scan_uses_persistent_project_id(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    project = Project(
        path=str(project_dir),
        metadata=ProjectMetadata.create_new("Project", "Customer", "Network"),
    )
    settings_file = tmp_path / "settings.json"
    settings_repo = SettingsRepository(file_path=settings_file)
    settings_repo.save_settings(AppSettings(workspace_roots=[str(tmp_path)]))
    project_repo = ProjectRepository()
    project_repo.create_project(project)
    bridge = ApiBridge(
        settings_repo,
        project_repo,
        ImmediateScanService(project),
        ProjectService(project_repo),
        FileService(AuditRepository()),
        DeliveryService(),
        AuditRepository(),
        ChecklistRepository(),
        TemplateLoader(),
    )

    first_scan = bridge.scan_projects()
    second_scan = bridge.scan_projects()

    assert first_scan["projects"][0]["id"] == project.metadata.project_id
    assert second_scan["projects"][0]["id"] == project.metadata.project_id


def test_task_and_artifact_crud_uses_persistent_ids(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    project = Project(
        path=str(project_dir),
        metadata=ProjectMetadata.create_new("Project", "Customer", "Network"),
    )
    settings_repo = SettingsRepository(file_path=tmp_path / "settings.json")
    project_repo = ProjectRepository()
    project_repo.create_project(project)
    bridge = ApiBridge(
        settings_repo,
        project_repo,
        ImmediateScanService(project),
        ProjectService(project_repo),
        FileService(AuditRepository()),
        DeliveryService(),
        AuditRepository(),
        ChecklistRepository(),
        TemplateLoader(),
    )
    project_id = bridge.scan_projects()["projects"][0]["id"]

    task_id = bridge.create_task({"project_id": project_id, "title": "Prepare"})["task_id"]
    bridge.update_task({"project_id": project_id, "task_id": task_id, "status": "Done"})
    artifact_id = bridge.create_artifact({"project_id": project_id, "type": "HLD"})["artifact_id"]
    bridge.update_artifact({"project_id": project_id, "artifact_id": artifact_id, "status": "Approved"})

    checklist = bridge.get_checklist(project_id)
    assert checklist["tasks"][0]["status"] == "Done"
    assert checklist["artifacts"][0]["status"] == "Approved"
    bridge.delete_task({"project_id": project_id, "task_id": task_id})
    bridge.delete_artifact({"project_id": project_id, "artifact_id": artifact_id})
    assert bridge.get_checklist(project_id) == {"tasks": [], "artifacts": []}


def test_site_and_device_rollout_crud(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    project = Project(path=str(project_dir), metadata=ProjectMetadata.create_new("Project", "Customer", "Network"))
    settings_repo = SettingsRepository(file_path=tmp_path / "settings.json")
    project_repo = ProjectRepository()
    project_repo.create_project(project)
    bridge = ApiBridge(
        settings_repo, project_repo, ImmediateScanService(project), ProjectService(project_repo),
        FileService(AuditRepository()), DeliveryService(), AuditRepository(), ChecklistRepository(), TemplateLoader(),
    )
    project_id = bridge.scan_projects()["projects"][0]["id"]

    site_id = bridge.create_site({"project_id": project_id, "name": "Hanoi"})["site_id"]
    device_id = bridge.create_device(
        {"project_id": project_id, "site_id": site_id, "serial_number": "SERIAL-1", "management_ip": "10.0.0.1"}
    )["device_id"]
    bridge.update_device({"project_id": project_id, "device_id": device_id, "pre_check_status": "Passed"})

    details = bridge.get_project_details(project_id)
    assert details["devices"][0]["pre_check_status"] == "Passed"
    bridge.delete_device({"project_id": project_id, "device_id": device_id})
    bridge.delete_site({"project_id": project_id, "site_id": site_id})
    assert bridge.get_project_details(project_id)["sites"] == []
