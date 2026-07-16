import os
import stat
from pathlib import Path


class PathViolationError(ValueError):
    """Raised when a project-relative path could escape its project root."""


_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def _is_reparse_point(path: Path) -> bool:
    """Return whether a path is a Windows symlink, junction, or other reparse point."""
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError as exc:
        raise PathViolationError(f"Cannot inspect path: {path}") from exc
    return path.is_symlink() or bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def resolve_project_path(project_root: Path, relative_path: str) -> Path:
    """Safely resolve a project-relative path without allowing root escape or reparse points."""
    if not relative_path or "\x00" in relative_path:
        raise PathViolationError("Project path must not be empty or contain null bytes.")

    candidate = Path(relative_path)
    if candidate.is_absolute() or ":" in relative_path:
        raise PathViolationError("Project path must be a relative non-ADS path.")
    if any(part.split(".", 1)[0].upper() in _WINDOWS_RESERVED_NAMES for part in candidate.parts):
        raise PathViolationError("Project path contains a reserved Windows device name.")

    try:
        root = project_root.resolve(strict=True)
    except OSError as exc:
        raise PathViolationError("Project root does not exist or cannot be resolved.") from exc
    if _is_reparse_point(project_root):
        raise PathViolationError("Project root cannot be a symlink or reparse point.")

    lexical_target = root.joinpath(*candidate.parts)
    current = root
    for part in candidate.parts:
        if part in ("", "."):
            continue
        current = current / part
        if current.exists() and _is_reparse_point(current):
            raise PathViolationError("Project path cannot traverse a symlink or reparse point.")

    try:
        resolved_target = lexical_target.resolve(strict=False)
    except OSError as exc:
        raise PathViolationError("Project path cannot be resolved.") from exc
    if resolved_target != root and root not in resolved_target.parents:
        raise PathViolationError("Project path escapes the project root.")
    return resolved_target


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
