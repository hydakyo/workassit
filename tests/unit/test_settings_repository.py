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
        workspace_roots=["C:/root1", "D:/root2"],
        theme="light",
        default_author="Admin"
    )
    
    repo.save_settings(settings)
    
    # Load again
    repo2 = SettingsRepository(file_path=settings_file)
    loaded = repo2.load_settings()
    
    assert loaded.theme == "light"
    assert len(loaded.workspace_roots) == 2
    assert "C:/root1" in loaded.workspace_roots
