import logging
from pathlib import Path

from app.config.settings import AppSettings, normalize_ai_provider
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
        except (OSError, ValueError) as exc:
            logger.error("Failed to load settings JSON: %s", exc)
            return AppSettings()

        if data.get("schema_version") != 1:
            logger.warning("Unknown schema version in settings.")
        try:
            api_key = keyring.get_password("ProjectOS", "ai_api_key") or ""
        except Exception:
            logger.error("Could not read AI key from the operating-system keyring.")
            api_key = ""

        try:
            provider = normalize_ai_provider(str(data.get("ai_provider", "none")))
        except ValueError:
            logger.warning("Unsupported AI provider type in settings; AI has been disabled.")
            provider = "none"

        return AppSettings(
            schema_version=data.get("schema_version", 1),
            workspace_roots=data.get("workspace_roots", []),
            theme=data.get("theme", "dark"),
            default_author=data.get("default_author", ""),
            ai_provider=provider,
            ai_api_key=api_key,
            ai_base_url=data.get("ai_base_url", ""),
            ai_model=data.get("ai_model", "gpt-4o-mini"),
            ai_streaming=data.get("ai_streaming", True),
        )

    def save_settings(self, settings: AppSettings) -> None:
        data = {
            "schema_version": settings.schema_version,
            "workspace_roots": settings.workspace_roots,
            "theme": settings.theme,
            "default_author": settings.default_author,
            "ai_provider": normalize_ai_provider(settings.ai_provider),
            "ai_base_url": settings.ai_base_url,
            "ai_model": settings.ai_model,
            "ai_streaming": settings.ai_streaming,
        }
        
        if settings.ai_api_key:
            try:
                keyring.set_password("ProjectOS", "ai_api_key", settings.ai_api_key)
            except Exception as exc:
                logger.error("Could not save AI key to the operating-system keyring.")
                raise RuntimeError("AI key could not be stored securely.") from exc
        write_json_atomic(self.file_path, data)
