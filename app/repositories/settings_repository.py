import logging
from pathlib import Path

from app.config.settings import AppSettings
from app.config.constants import SETTINGS_FILE
from app.utils.atomic_json import read_json, write_json_atomic
import keyring

logger = logging.getLogger(__name__)

class SettingsRepository:
    def __init__(self, file_path: Path = SETTINGS_FILE):
        self.file_path = file_path

    def load_settings(self) -> AppSettings:
        if not self.file_path.exists():
            default_settings = AppSettings()
            self.save_settings(default_settings)
            return default_settings
        
        try:
            data = read_json(self.file_path)
            # Basic validation
            if data.get("schema_version") != 1:
                logger.warning("Unknown schema version in settings.")
                
            # Load secure API key from keyring
            api_key = keyring.get_password("ProjectOS", "ai_api_key") or ""
            
            return AppSettings(
                schema_version=data.get("schema_version", 1),
                workspace_roots=data.get("workspace_roots", []),
                theme=data.get("theme", "dark"),
                default_author=data.get("default_author", ""),
                ai_provider=data.get("ai_provider", "None"),
                ai_api_key=api_key
            )
        except Exception as e:
            logger.error(f"Failed to load settings: {e}. Returning default settings.")
            return AppSettings()

    def save_settings(self, settings: AppSettings) -> None:
        data = {
            "schema_version": settings.schema_version,
            "workspace_roots": settings.workspace_roots,
            "theme": settings.theme,
            "default_author": settings.default_author,
            "ai_provider": settings.ai_provider
        }
        
        # Save secure API key to keyring if provided
        try:
            if settings.ai_api_key:
                keyring.set_password("ProjectOS", "ai_api_key", settings.ai_api_key)
            else:
                # If empty, try to delete it
                try:
                    keyring.delete_password("ProjectOS", "ai_api_key")
                except keyring.errors.PasswordDeleteError:
                    pass
        except Exception as e:
            logger.error(f"Failed to securely save API key: {e}")
            
        write_json_atomic(self.file_path, data)
