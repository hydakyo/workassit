from pathlib import Path
from app.repositories.settings_repository import SettingsRepository
from app.config.settings import AppSettings

def test_load_default_settings(tmp_path: Path):
    settings_file = tmp_path / "settings.json"
    repo = SettingsRepository(file_path=settings_file)
    
    settings = repo.load_settings()
    assert settings.schema_version == 1
    assert settings.workspace_roots == []
    assert settings.theme == "dark"
    assert settings_file.exists()

def test_save_and_load_settings(tmp_path: Path):
    settings_file = tmp_path / "settings.json"
    repo = SettingsRepository(file_path=settings_file)
    
    settings = AppSettings(
        schema_version=1,
        workspace_roots=["root1", "root2"],
        theme="light",
        default_author="tester",
        ai_provider="OpenAI",
        ai_api_key="secret",
        ai_base_url="https://gateway.example/v1",
        ai_model="gateway-model",
    )
    repo.save_settings(settings)
    
    loaded = repo.load_settings()
    assert loaded.workspace_roots == ["root1", "root2"]
    assert loaded.theme == "light"
    assert loaded.ai_provider == "OpenAI"
    assert loaded.ai_api_key == "secret"
    assert loaded.ai_base_url == "https://gateway.example/v1"
    assert loaded.ai_model == "gateway-model"
