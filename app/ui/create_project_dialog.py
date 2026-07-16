import customtkinter as ctk
from typing import Callable, Any

class CreateProjectDialog(ctk.CTkToplevel):  # type: ignore
    def __init__(self, master: Any, on_create: Callable[[str, str, str], None], **kwargs: Any):
        super().__init__(master, **kwargs)
        
        self.title("New Project")
        self.geometry("450x350")
        
        self.on_create = on_create
        
        # Make modal
        self.transient(master)
        self.grab_set()
        
        # Bind Enter to submit
        self.bind("<Return>", lambda event: self._on_submit())
        
        self.grid_columnconfigure(1, weight=1)
        
        # Project Name
        ctk.CTkLabel(self, text="Project Name:", font=("Roboto", 14)).grid(row=0, column=0, padx=20, pady=(30, 10), sticky="w")
        self.entry_name = ctk.CTkEntry(self, placeholder_text="e.g. Core Network Upgrade", font=("Roboto", 14))
        self.entry_name.grid(row=0, column=1, padx=20, pady=(30, 10), sticky="ew")
        self.entry_name.focus_set()
        
        # Customer Name
        ctk.CTkLabel(self, text="Customer Name:").grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.entry_customer = ctk.CTkEntry(self, placeholder_text="e.g. ACME Corp")
        self.entry_customer.grid(row=1, column=1, padx=20, pady=10, sticky="ew")
        
        # Project Type
        ctk.CTkLabel(self, text="Project Type:").grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.combo_type = ctk.CTkComboBox(self, values=["network_deployment", "security_audit", "infrastructure_design"])
        self.combo_type.grid(row=2, column=1, padx=20, pady=10, sticky="ew")
        
        # Error Label
        self.lbl_error = ctk.CTkLabel(self, text="", text_color="red", font=("Roboto", 13, "bold"))
        self.lbl_error.grid(row=3, column=0, columnspan=2, padx=20, pady=5)
        
        # Buttons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        self.btn_cancel = ctk.CTkButton(self.btn_frame, text="Cancel", command=self.destroy, fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE"))
        self.btn_cancel.pack(side="left", padx=10)
        
        self.btn_create = ctk.CTkButton(self.btn_frame, text="Create", command=self._on_submit)
        self.btn_create.pack(side="right", padx=10)
        
    def _on_submit(self) -> None:
        name = self.entry_name.get().strip()
        customer = self.entry_customer.get().strip()
        p_type = self.combo_type.get()
        
        if not name:
            self.lbl_error.configure(text="Project Name is required.")
            return
            
        if not customer:
            self.lbl_error.configure(text="Customer Name is required.")
            return
            
        self.on_create(name, customer, p_type)
        self.destroy()
