"""Resolve paths that work both from source and PyInstaller bundles."""

import sys
from pathlib import Path


def get_application_root() -> Path:
    """Return the directory containing bundled assets or the repository root."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if isinstance(bundle_root, str):
        return Path(bundle_root)
    return Path(__file__).resolve().parents[2]


def get_web_directory() -> Path:
    """Return the directory containing the static PyWebView frontend assets."""
    return get_application_root() / "web"
