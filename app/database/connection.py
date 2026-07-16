import sqlite3
import os
from pathlib import Path
from typing import Optional

class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
            self.db_path = Path(app_data) / 'ProjectOS' / 'index.db'
        else:
            self.db_path = Path(db_path)
            
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Projects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    path TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    customer TEXT,
                    type TEXT,
                    stage TEXT,
                    updated_at TEXT
                )
            """)
            
            # Tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT,
                    priority TEXT,
                    owner TEXT,
                    due_date TEXT,
                    phase TEXT,
                    category TEXT,
                    created_at TEXT,
                    completed_at TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            
            # Artifacts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    type TEXT,
                    path TEXT,
                    status TEXT,
                    version TEXT,
                    checksum TEXT,
                    updated_at TEXT,
                    owner TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)

            # Deliveries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deliveries (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    version TEXT,
                    checksum TEXT,
                    generated_time TEXT,
                    generated_by TEXT,
                    approval_state TEXT,
                    release_notes TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)

            conn.commit()
