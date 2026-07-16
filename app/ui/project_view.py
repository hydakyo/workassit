import customtkinter as ctk
from typing import Callable, Any
from pathlib import Path
from tkinter import filedialog

from app.models.project import Project
from app.services.file_service import FileService
from app.services.delivery_service import DeliveryService
from app.services.ai_service import AIService
from app.repositories.audit_repository import AuditRepository
from app.repositories.checklist_repository import ChecklistRepository
from app.models.checklist import ChecklistItem
from app.config.settings import AppSettings
import threading

class ProjectView(ctk.CTkFrame): # type: ignore
    def __init__(self, master: Any, project: Project, settings: AppSettings, file_service: FileService, delivery_service: DeliveryService, audit_repo: AuditRepository, checklist_repo: ChecklistRepository, on_back: Callable[[], None], **kwargs: Any):
        super().__init__(master, **kwargs)
        
        self.project = project
        self.settings = settings
        self.file_service = file_service
        self.delivery_service = delivery_service
        self.audit_repo = audit_repo
        self.checklist_repo = checklist_repo
        self.on_back = on_back
        
        self.checklist_items: list[ChecklistItem] = []
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        self.btn_back = ctk.CTkButton(header_frame, text="< Back", width=60, fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray75", "gray25"), command=self.on_back)
        self.btn_back.pack(side="left")
        
        self.header = ctk.CTkLabel(header_frame, text=f"Project: {self.project.metadata.project_name}", font=("Roboto", 24, "bold"))
        self.header.pack(side="left", padx=20)
        
        # Actions
        actions_frame = ctk.CTkFrame(self, corner_radius=10)
        actions_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.btn_import = ctk.CTkButton(actions_frame, text="Import File", font=("Roboto", 13, "bold"), command=self.import_file)
        self.btn_import.pack(side="left", padx=15, pady=15)
        
        self.btn_package = ctk.CTkButton(actions_frame, text="Create Package", font=("Roboto", 13, "bold"), command=self.create_package, fg_color="#2EA043", hover_color="#238636")
        self.btn_package.pack(side="left", padx=15, pady=15)
        
        self.btn_undo = ctk.CTkButton(actions_frame, text="Undo Last Action", font=("Roboto", 13), command=self.undo_action, fg_color="transparent", border_width=1, border_color="orange", text_color="orange", hover_color=("gray85", "gray25"))
        self.btn_undo.pack(side="left", padx=15, pady=15)
        
        if self.settings.ai_provider != "None":
            self.btn_ai = ctk.CTkButton(actions_frame, text="✨ AI Analyze", font=("Roboto", 13, "bold"), command=self.analyze_project, fg_color="#8957e5", hover_color="#6e46b8")
            self.btn_ai.pack(side="left", padx=15, pady=15)
        
        self.status_label = ctk.CTkLabel(actions_frame, text="")
        self.status_label.pack(side="right", padx=20)
        
        # Tabs for Checklist and Audit Log
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.tabview.add("Checklist")
        self.tabview.add("Audit Log")
        
        # Checklist Tab
        self.checklist_frame = ctk.CTkScrollableFrame(self.tabview.tab("Checklist"))
        self.checklist_frame.pack(fill="both", expand=True)
        
        add_task_frame = ctk.CTkFrame(self.tabview.tab("Checklist"))
        add_task_frame.pack(fill="x", pady=5)
        
        self.entry_task = ctk.CTkEntry(add_task_frame, placeholder_text="New task...")
        self.entry_task.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_add_task = ctk.CTkButton(add_task_frame, text="Add", width=60, command=self.add_task)
        self.btn_add_task.pack(side="right", padx=5)
        
        # Audit Tab
        self.audit_frame = ctk.CTkScrollableFrame(self.tabview.tab("Audit Log"))
        self.audit_frame.pack(fill="both", expand=True)
        
        self.refresh_audit_log()
        self.refresh_checklist()
        
    def import_file(self) -> None:
        file_path = filedialog.askopenfilename()
        if file_path:
            success = self.file_service.import_file(self.project, file_path)
            if success:
                self.status_label.configure(text="File imported successfully", text_color="green")
                self.refresh_audit_log()
            else:
                self.status_label.configure(text="Failed to import file", text_color="red")
                
    def undo_action(self) -> None:
        success = self.file_service.undo_last_import(self.project)
        if success:
            self.status_label.configure(text="Undo successful", text_color="green")
            self.refresh_audit_log()
        else:
            self.status_label.configure(text="Nothing to undo or failed", text_color="red")
            
    def create_package(self) -> None:
        self.status_label.configure(text="Creating package...", text_color="black")
        path = self.delivery_service.create_delivery_package(self.project)
        if path:
            self.status_label.configure(text=f"Package created: {Path(path).name}", text_color="green")
        else:
            self.status_label.configure(text="Failed to create package", text_color="red")
            
    def add_task(self) -> None:
        title = self.entry_task.get().strip()
        if not title:
            return
            
        import uuid
        item = ChecklistItem(id=str(uuid.uuid4()), title=title, is_completed=False)
        self.checklist_items.append(item)
        self.checklist_repo.save_checklist(Path(self.project.path), self.checklist_items)
        self.entry_task.delete(0, 'end')
        self.refresh_checklist()
        
    def toggle_task(self, item: ChecklistItem, val: str) -> None:
        item.is_completed = (val == "on")
        self.checklist_repo.save_checklist(Path(self.project.path), self.checklist_items)
        
    def refresh_checklist(self) -> None:
        for widget in self.checklist_frame.winfo_children():
            widget.destroy()
            
        self.checklist_items = self.checklist_repo.load_checklist(Path(self.project.path))
        
        for item in self.checklist_items:
            # We capture `item` in lambda using default arg `i=item`
            cb = ctk.CTkCheckBox(
                self.checklist_frame, 
                text=item.title, 
                command=lambda i=item: self.toggle_task(i, cb.get()), # type: ignore
                onvalue="on", 
                offvalue="off"
            )
            if item.is_completed:
                cb.select()
            cb.pack(anchor="w", padx=10, pady=5)
            
    def refresh_audit_log(self) -> None:
        for widget in self.audit_frame.winfo_children():
            widget.destroy()
            
        logs = self.audit_repo.read_logs(Path(self.project.path))
        if not logs:
            ctk.CTkLabel(self.audit_frame, text="No activity found.").pack(pady=10)
            return
            
        # Reverse to show newest first
        for entry in reversed(logs):
            frame = ctk.CTkFrame(self.audit_frame)
            frame.pack(fill="x", pady=2, padx=5)
            
            text = f"[{entry.timestamp}] {entry.action}: {entry.file_name} -> {entry.destination_path}"
            lbl = ctk.CTkLabel(frame, text=text, anchor="w", justify="left")
            lbl.pack(fill="x", padx=10, pady=5)
            
    def analyze_project(self) -> None:
        self.status_label.configure(text="AI is analyzing...", text_color="blue")
        
        def run_ai() -> None:
            ai_service = AIService(self.settings.ai_provider, self.settings.ai_api_key)
            
            # Gather context
            completed = sum(1 for t in self.checklist_items if t.is_completed)
            total = len(self.checklist_items)
            prompt = (
                f"Analyze the following project status:\n"
                f"Name: {self.project.metadata.project_name}\n"
                f"Type: {self.project.metadata.project_type}\n"
                f"Stage: {self.project.metadata.stage}\n"
                f"Tasks: {completed}/{total} completed.\n"
                f"Tasks list: {[t.title for t in self.checklist_items]}\n\n"
                "Provide a brief 3-sentence summary of the status and any recommendations."
            )
            
            result = ai_service.analyze_project(prompt)
            
            self.after(0, self._show_ai_result, result)
            
        threading.Thread(target=run_ai, daemon=True).start()
        
    def _show_ai_result(self, result: str | None) -> None:
        self.status_label.configure(text="AI analysis complete.", text_color="green")
        if not result:
            result = "No output."
            
        # Show in a simple dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("✨ AI Analysis")
        dialog.geometry("600x400")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        
        dialog.grid_rowconfigure(0, weight=1)
        dialog.grid_columnconfigure(0, weight=1)
        
        text = ctk.CTkTextbox(dialog, wrap="word", font=("Roboto", 14))
        text.grid(row=0, column=0, sticky="nsew", padx=20, pady=(20, 10))
        text.insert("0.0", result)
        text.configure(state="disabled")
        
        btn_close = ctk.CTkButton(dialog, text="Close", command=dialog.destroy)
        btn_close.grid(row=1, column=0, pady=(10, 20))
