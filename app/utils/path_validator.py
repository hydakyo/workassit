import os
from pathlib import Path

def is_safe_path(base_path: Path, target_path: Path) -> bool:
    """
    Checks if target_path is safely contained within base_path.
    Prevents directory traversal attacks and infinite symlink recursion
    by fully resolving both paths and checking commonpath.
    """
    try:
        resolved_base = base_path.resolve(strict=True)
        resolved_target = target_path.resolve(strict=True)
        
        common = os.path.commonpath([str(resolved_base), str(resolved_target)])
        return common == str(resolved_base)
    except (OSError, RuntimeError):
        # strict=True raises OSError if path doesn't exist
        # RuntimeError can occur on infinite recursion
        return False

def normalize_path(path_str: str) -> Path:
    """
    Normalizes a string path into a resolved Path object.
    """
    return Path(path_str).resolve()
