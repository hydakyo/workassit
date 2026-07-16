import json
import logging
from pathlib import Path
from typing import List

from app.models.audit import AuditEntry

logger = logging.getLogger(__name__)

class AuditRepository:
    def __init__(self, filename: str = "audit.jsonl"):
        self.filename = filename

    def append_log(self, project_path: Path, entry: AuditEntry) -> None:
        audit_file = project_path / self.filename
        try:
            with open(audit_file, "a", encoding="utf-8") as f:
                data = {
                    "timestamp": entry.timestamp,
                    "action": entry.action,
                    "file_name": entry.file_name,
                    "destination_path": entry.destination_path,
                    "previous_version_path": entry.previous_version_path,
                    "user": entry.user
                }
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            logger.error(f"Failed to append audit log to {audit_file}: {e}")

    def read_logs(self, project_path: Path) -> List[AuditEntry]:
        audit_file = project_path / self.filename
        entries: List[AuditEntry] = []
        if not audit_file.exists():
            return entries
            
        try:
            with open(audit_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    entries.append(AuditEntry(
                        timestamp=data["timestamp"],
                        action=data["action"],
                        file_name=data["file_name"],
                        destination_path=data["destination_path"],
                        previous_version_path=data.get("previous_version_path"),
                        user=data.get("user", "System")
                    ))
        except Exception as e:
            logger.error(f"Failed to read audit logs from {audit_file}: {e}")
            
        return entries
