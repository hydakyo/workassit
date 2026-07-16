from pathlib import Path
from unittest.mock import patch

import pytest
from app.repositories.settings_repository import SettingsRepository
from app.config.settings import AppSettings

def test_load_default_settings(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    repo = SettingsRepository(file_path=settings_file)
    
    with patch("app.repositories.settings_repository.keyring"):
        settings = repo.load_settings()
    assert settings.schema_version == 1
    assert settings.workspace_roots == []
    assert settings.theme == "dark"
    assert settings_file.exists()

def test_save_and_load_settings(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    repo = SettingsRepository(file_path=settings_file)
    
    settings = AppSettings(
        schema_version=1,
        workspace_roots=["root1", "root2"],
        theme="light",
        default_author="tester",
        ai_provider="openai",
        ai_api_key="secret",
        ai_base_url="https://gateway.example/v1",
        ai_model="gateway-model",
        ai_streaming=False,
    )
    with patch("app.repositories.settings_repository.keyring") as keyring_mock:
        keyring_mock.get_password.return_value = "secret"
        repo.save_settings(settings)
        loaded = repo.load_settings()
    assert loaded.workspace_roots == ["root1", "root2"]
    assert loaded.theme == "light"
    assert loaded.ai_provider == "openai"
    assert loaded.ai_api_key == "secret"
    assert loaded.ai_base_url == "https://gateway.example/v1"
    assert loaded.ai_model == "gateway-model"
    assert loaded.ai_streaming is False


def test_load_settings_preserves_json_when_keyring_fails(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    repo = SettingsRepository(file_path=settings_file)
    with patch("app.repositories.settings_repository.keyring") as keyring_mock:
        repo.save_settings(AppSettings(workspace_roots=["workspace"]))
        keyring_mock.get_password.side_effect = RuntimeError("Unavailable")
        loaded = repo.load_settings()

    assert loaded.workspace_roots == ["workspace"]
    assert loaded.ai_api_key == ""


def test_save_settings_fails_when_keyring_cannot_store_key(tmp_path: Path) -> None:
    repo = SettingsRepository(file_path=tmp_path / "settings.json")
    with patch("app.repositories.settings_repository.keyring") as keyring_mock:
        keyring_mock.set_password.side_effect = RuntimeError("Unavailable")
        with pytest.raises(RuntimeError, match="could not be stored"):
            repo.save_settings(AppSettings(ai_api_key="secret"))
