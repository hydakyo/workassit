import os
from pathlib import Path

APP_NAME = "ProjectOS"
APP_DATA_DIR = Path(os.getenv("APPDATA", os.path.expanduser("~"))) / APP_NAME
SETTINGS_FILE = APP_DATA_DIR / "settings.json"
LOG_DIR = APP_DATA_DIR / "logs"

PROJECT_FILENAME = "project.json"
