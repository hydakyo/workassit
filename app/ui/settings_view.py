import customtkinter as ctk
from typing import Callable, Any
from pathlib import Path

from app.config.settings import AppSettings
from app.config.constants import SETTINGS_FILE

class SettingsView(ctk.CTkFrame):  # type: ignore
    def __init__(self, master: Any, settings: AppSettings, on_save: Callable[[AppSettings], None], **kwargs: Any):
        super().__init__(master, **kwargs)
        self.settings = settings
        self.on_save_callback = on_save
        
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        self.header = ctk.CTkLabel(self, text="Settings", font=("Roboto", 24, "bold"))
        self.header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Settings Path Info
        self.path_info = ctk.CTkLabel(self, text=f"Settings File: {SETTINGS_FILE}", text_color="gray")
        self.path_info.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        
        # Workspace Roots
        self.roots_label = ctk.CTkLabel(self, text="Workspace Roots:", font=("Roboto", 16, "bold"))
        self.roots_label.grid(row=2, column=0, padx=20, pady=5, sticky="w")
        
        self.roots_frame = ctk.CTkScrollableFrame(self, height=150)
        self.roots_frame.grid(row=3, column=0, columnspan=2, padx=20, pady=5, sticky="nsew")
        self.grid_rowconfigure(3, weight=1)
        
        # AI Config Section
        ctk.CTkLabel(self, text="AI Configuration (Opt-in):", font=("Roboto", 16, "bold")).grid(row=4, column=0, columnspan=2, padx=20, pady=(20, 5), sticky="w")
        
        self.ai_provider_var = ctk.StringVar(value=self.settings.ai_provider)
        self.combo_ai = ctk.CTkComboBox(self, values=["None", "Gemini", "OpenAI"], variable=self.ai_provider_var)
        self.combo_ai.grid(row=5, column=0, padx=20, pady=5, sticky="ew")
        
        self.entry_ai_key = ctk.CTkEntry(self, placeholder_text="API Key (Not saved to logs)")
        self.entry_ai_key.insert(0, self.settings.ai_api_key)
        self.entry_ai_key.configure(show="*")
        self.entry_ai_key.grid(row=5, column=1, padx=20, pady=5, sticky="ew")
        
        self.root_widgets: list[Any] = []
        self._render_roots()
        
        # Controls
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=6, column=0, columnspan=2, padx=20, pady=20, sticky="ew")
        
        self.add_btn = ctk.CTkButton(self.controls_frame, text="Add Workspace Root", command=self._add_root)
        self.add_btn.pack(side="left", padx=10, pady=10)
        
        self.save_btn = ctk.CTkButton(self.controls_frame, text="Save Settings", command=self.save_changes)
        self.save_btn.pack(side="right", padx=10, pady=10)
        
        # Status Label
        self.status_label = ctk.CTkLabel(self.controls_frame, text="", text_color="green", font=("Roboto", 14, "bold"))
        self.status_label.pack(side="right", padx=20, pady=10)
        
    def _render_roots(self) -> None:
        for w in self.roots_frame.winfo_children():
            w.destroy()
            
        for i, root in enumerate(self.settings.workspace_roots):
            frame = ctk.CTkFrame(self.roots_frame)
            frame.pack(fill="x", pady=2)
            
            lbl = ctk.CTkLabel(frame, text=root)
            lbl.pack(side="left", padx=10)
            
            del_btn = ctk.CTkButton(frame, text="Remove", width=60, fg_color="red", hover_color="darkred",
                                    command=lambda idx=i: self._remove_root(idx))
            del_btn.pack(side="right", padx=10, pady=5)
            
    def _add_root(self) -> None:
        # In a real app, use ctk.filedialog.askdirectory
        # For this phase, we use a simple dialog
        dialog = ctk.CTkInputDialog(text="Enter full path to workspace root:", title="Add Workspace Root")
        path_str = dialog.get_input()
        if path_str:
            path = Path(path_str)
            if path.is_dir():
                if path_str not in self.settings.workspace_roots:
                    self.settings.workspace_roots.append(path_str)
                    self._render_roots()
            else:
                # Basic warning
                print(f"Path is not a valid directory: {path_str}")
                
    def _remove_root(self, index: int) -> None:
        if 0 <= index < len(self.settings.workspace_roots):
            self.settings.workspace_roots.pop(index)
            self._render_roots()
            
    def save_changes(self) -> None:
        self.settings.ai_provider = self.ai_provider_var.get()
        self.settings.ai_api_key = self.entry_ai_key.get().strip()
        self.on_save_callback(self.settings)
        
        # UI Feedback
        self.status_label.configure(text="✅ Settings saved successfully!")
        self.after(3000, lambda: self.status_label.configure(text=""))
