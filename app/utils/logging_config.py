import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging() -> None:
    """
    Sets up application logging.
    Logs are stored in %APPDATA%/ProjectOS/logs/.
    """
    app_data = os.getenv("APPDATA")
    if not app_data:
        app_data = os.path.expanduser("~")
        
    log_dir = Path(app_data) / "ProjectOS" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "app.log"
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File handler
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
