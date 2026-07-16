import customtkinter as ctk
from typing import List, Optional

from app.config.settings import AppSettings
from app.repositories.settings_repository import SettingsRepository
from app.repositories.project_repository import ProjectRepository
from app.services.workspace_scan_service import WorkspaceScanService
from app.services.project_service import ProjectService
from app.services.file_service import FileService
from app.services.delivery_service import DeliveryService
from app.repositories.audit_repository import AuditRepository
from app.repositories.checklist_repository import ChecklistRepository
from app.ui.dashboard_view import DashboardView
from app.ui.settings_view import SettingsView
from app.ui.create_project_dialog import CreateProjectDialog
from app.ui.project_view import ProjectView
from app.models.project import Project

class MainWindow(ctk.CTk):  # type: ignore
    def __init__(self, settings_repo: SettingsRepository, project_repo: ProjectRepository, scan_service: WorkspaceScanService, project_service: ProjectService, file_service: FileService, delivery_service: DeliveryService, audit_repo: AuditRepository, checklist_repo: ChecklistRepository):
        super().__init__()
        
        self.settings_repo = settings_repo
        self.project_repo = project_repo
        self.scan_service = scan_service
        self.project_service = project_service
        self.file_service = file_service
        self.delivery_service = delivery_service
        self.audit_repo = audit_repo
        self.checklist_repo = checklist_repo
        
        self.settings = self.settings_repo.load_settings()
        
        self.title("Project OS")
        self.geometry("900x600")
        
        # Grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=("gray90", "gray15"))
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Project OS", font=ctk.CTkFont(family="Roboto", size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20))
        
        self.btn_dashboard = ctk.CTkButton(self.sidebar_frame, text="Dashboard", command=self.show_dashboard, fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray75", "gray25"), anchor="w")
        self.btn_dashboard.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.btn_settings = ctk.CTkButton(self.sidebar_frame, text="Settings", command=self.show_settings, fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray75", "gray25"), anchor="w")
        self.btn_settings.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        self.btn_refresh = ctk.CTkButton(self.sidebar_frame, text="Refresh Projects", command=self.refresh_projects, anchor="center")
        self.btn_refresh.grid(row=3, column=0, padx=20, pady=(40, 10), sticky="ew")
        
        # Views
        self.dashboard_view = DashboardView(self, on_new_project=self.open_create_project_dialog, on_project_select=self.show_project_view)
        self.settings_view = SettingsView(self, self.settings, self.save_settings)
        self.current_project_view: Optional[ProjectView] = None
        
        # Show default view
        self.show_dashboard()
        
    def show_dashboard(self) -> None:
        self.settings_view.grid_forget()
        if self.current_project_view:
            self.current_project_view.grid_forget()
        self.dashboard_view.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
    def show_settings(self) -> None:
        self.dashboard_view.grid_forget()
        if self.current_project_view:
            self.current_project_view.grid_forget()
        self.settings_view.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
    def show_project_view(self, project: Project) -> None:
        self.dashboard_view.grid_forget()
        self.settings_view.grid_forget()
        
        if self.current_project_view:
            self.current_project_view.destroy()
            
        self.current_project_view = ProjectView(self, project, self.settings, self.file_service, self.delivery_service, self.audit_repo, self.checklist_repo, self.show_dashboard)
        self.current_project_view.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
    def refresh_projects(self) -> None:
        self.btn_refresh.configure(state="disabled")
        self.dashboard_view.set_status("Scanning")
        
        # Run scan in background
        self.scan_service.scan_workspaces_async(
            self.settings,
            on_complete=self.on_scan_complete,
            on_error=self.on_scan_error
        )
        
    def on_scan_complete(self, projects: List[Project], warnings: List[str]) -> None:
        # Update UI safely
        self.after(0, self._update_ui_complete, projects, warnings)
        
    def _update_ui_complete(self, projects: List[Project], warnings: List[str]) -> None:
        self.dashboard_view.update_projects(projects, warnings)
        self.dashboard_view.set_status("Completed")
        self.btn_refresh.configure(state="normal")
        
    def on_scan_error(self, error: str) -> None:
        self.after(0, self._update_ui_error, error)
        
    def _update_ui_error(self, error: str) -> None:
        self.dashboard_view.set_status("Failed")
        self.dashboard_view.warnings_label.configure(text=f"Scan failed: {error}")
        self.btn_refresh.configure(state="normal")
        
    def open_create_project_dialog(self) -> None:
        if not self.settings.workspace_roots:
            self.dashboard_view.warnings_label.configure(text="Warning: Please add a workspace root in Settings first.")
            return
            
        _ = CreateProjectDialog(self, on_create=self.handle_create_project)
        # We don't block here because dialog handles its own flow and calls on_create
        
    def handle_create_project(self, name: str, customer: str, p_type: str) -> None:
        from pathlib import Path
        try:
            # For phase 2, pick the first workspace root
            root_path = Path(self.settings.workspace_roots[0])
            self.project_service.create_new_project(
                root_path=root_path,
                project_name=name,
                customer_name=customer,
                project_type=p_type
            )
            # Refresh projects to show the new one
            self.refresh_projects()
            self.dashboard_view.set_status("Project created successfully")
        except Exception as e:
            self.dashboard_view.warnings_label.configure(text=f"Failed to create project: {e}")

    def save_settings(self, settings: AppSettings) -> None:
        self.settings_repo.save_settings(settings)
        # Update local settings instance
        self.settings = settings
        
    def destroy(self) -> None:
        self.scan_service.shutdown()
        super().destroy()
