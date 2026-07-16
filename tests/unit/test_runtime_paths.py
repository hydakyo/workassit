from pathlib import Path

from app.utils.runtime_paths import get_web_directory


def test_web_directory_resolves_source_assets() -> None:
    web_directory = get_web_directory()

    assert isinstance(web_directory, Path)
    assert (web_directory / "index.html").is_file()
