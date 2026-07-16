from pathlib import Path
from app.utils.path_validator import is_safe_path, normalize_path

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
