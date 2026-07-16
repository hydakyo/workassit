import os
import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

def read_json(file_path: Path) -> Dict[str, Any]:
    """Reads and parses a JSON file."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("JSON content is not a dictionary.")
        return data

def write_json_atomic(file_path: Path, data: Dict[str, Any]) -> None:
    """
    Writes data to a JSON file atomically.
    1. Writes to a temp file in the same directory.
    2. Flushes and fsyncs to ensure data is written to disk.
    3. Reads back to validate JSON.
    4. Backups the existing file.
    5. Replaces the old file with the new file.
    """
    temp_path = file_path.with_suffix(".tmp")
    bak_path = file_path.with_suffix(".bak")
    
    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Write to temp file
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
            
        # Read back to validate
        with open(temp_path, "r", encoding="utf-8") as f:
            json.load(f)
            
        # Backup existing file if it exists
        if file_path.exists():
            shutil.copy2(file_path, bak_path)
            
        # Atomically replace
        os.replace(temp_path, file_path)
        
    except Exception as e:
        logger.error(f"Failed to write JSON atomically to {file_path}: {e}")
        # Clean up temp file on failure
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise
