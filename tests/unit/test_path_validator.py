from pathlib import Path
import pytest

from app.utils.path_validator import PathViolationError, is_safe_path, normalize_path, resolve_project_path

def test_is_safe_path(tmp_path: Path):
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    
    target_inside = base_dir / "target"
    target_inside.mkdir()
    
    target_outside = tmp_path / "outside"
    target_outside.mkdir()
    
    assert is_safe_path(base_dir, target_inside) is True
    assert is_safe_path(base_dir, target_outside) is False
    
    # Test directory traversal
    traversal_path = base_dir / ".." / "outside"
    assert is_safe_path(base_dir, traversal_path) is False

def test_normalize_path():
    path_str = "C:/some/path"
    norm = normalize_path(path_str)
    assert isinstance(norm, Path)
    assert norm.is_absolute()


@pytest.mark.parametrize("unsafe_path", ["../outside.txt", "C:/outside.txt", "file.txt:secret", "CON.txt"])
def test_resolve_project_path_rejects_escape_paths(tmp_path: Path, unsafe_path: str) -> None:
    root = tmp_path / "project"
    root.mkdir()

    with pytest.raises(PathViolationError):
        resolve_project_path(root, unsafe_path)


def test_resolve_project_path_allows_relative_path(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()

    assert resolve_project_path(root, "00_Inbox/file.txt") == root / "00_Inbox" / "file.txt"


def test_resolve_project_path_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = root / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Symlink creation is unavailable: {exc}")

    with pytest.raises(PathViolationError):
        resolve_project_path(root, "linked/secret.txt")
