import logging
from pathlib import Path

from app.config.settings import AppSettings
from app.config.constants import SETTINGS_FILE
from app.utils.atomic_json import read_json, write_json_atomic

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
            
            return AppSettings(
                schema_version=data.get("schema_version", 1),
                workspace_roots=data.get("workspace_roots", []),
                theme=data.get("theme", "dark"),
                default_author=data.get("default_author", "")
            )
        except Exception as e:
            logger.error(f"Failed to load settings: {e}. Returning default settings.")
            return AppSettings()

    def save_settings(self, settings: AppSettings) -> None:
        data = {
            "schema_version": settings.schema_version,
            "workspace_roots": settings.workspace_roots,
            "theme": settings.theme,
            "default_author": settings.default_author
        }
        write_json_atomic(self.file_path, data)
