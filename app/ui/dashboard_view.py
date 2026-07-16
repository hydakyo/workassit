import customtkinter as ctk
from typing import List, Any, Callable

from app.models.project import Project

class DashboardView(ctk.CTkFrame):  # type: ignore
    def __init__(self, master: Any, on_new_project: Callable[[], None], on_project_select: Callable[[Project], None], **kwargs: Any):
        super().__init__(master, **kwargs)
        
        self.on_new_project = on_new_project
        self.on_project_select = on_project_select
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header
        self.header = ctk.CTkLabel(self, text="Project OS Dashboard", font=("Roboto", 24, "bold"))
        self.header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # New Project Button
        self.btn_new_project = ctk.CTkButton(self, text="+ New Project", command=self.on_new_project)
        self.btn_new_project.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="e")
        
        # Status
        self.status_label = ctk.CTkLabel(self, text="Status: Idle", text_color="gray")
        self.status_label.grid(row=0, column=2, padx=20, pady=(20, 10), sticky="e")
        
        # Project List Frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.grid(row=1, column=0, columnspan=3, padx=20, pady=10, sticky="nsew")
        
        self.empty_label = ctk.CTkLabel(self.scrollable_frame, text="No projects found. Add a workspace root in Settings.")
        self.empty_label.pack(pady=20)
        
        # Warnings
        self.warnings_label = ctk.CTkLabel(self, text="", text_color="orange")
        self.warnings_label.grid(row=2, column=0, columnspan=3, padx=20, pady=10, sticky="w")

    def set_status(self, status: str) -> None:
        self.status_label.configure(text=f"Status: {status}")

    def update_projects(self, projects: List[Project], warnings: List[str]) -> None:
        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        if not projects:
            self.empty_label = ctk.CTkLabel(self.scrollable_frame, text="No projects found.")
            self.empty_label.pack(pady=20)
        else:
            for project in projects:
                # Card frame
                frame = ctk.CTkFrame(self.scrollable_frame, fg_color=("gray85", "gray20"), corner_radius=10)
                frame.pack(fill="x", pady=8, padx=10)
                
                # Title
                title = ctk.CTkLabel(frame, text=project.metadata.project_name, font=("Roboto", 16, "bold"))
                title.pack(anchor="w", padx=15, pady=(15, 5))
                
                # Info
                info = ctk.CTkLabel(frame, text=f"Stage: {project.metadata.stage.title()} | Path: {project.path}", text_color="gray")
                info.pack(side="left", padx=15, pady=(0, 15))
                
                # View Button
                btn_view = ctk.CTkButton(frame, text="View", width=80, command=lambda p=project: self.on_project_select(p))
                btn_view.pack(side="right", padx=15, pady=15)
                
        if warnings:
            self.warnings_label.configure(text=f"Warnings: {len(warnings)} issue(s) detected during scan.")
        else:
            self.warnings_label.configure(text="")
