import json
import logging
import os
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
                    "event_id": entry.event_id,
                    "timestamp": entry.timestamp,
                    "action": entry.action,
                    "file_name": entry.file_name,
                    "destination_path": entry.destination_path,
                    "previous_version_path": entry.previous_version_path,
                    "undo_of_event_id": entry.undo_of_event_id,
                    "user": entry.user
                }
                f.write(json.dumps(data) + "\n")
                f.flush()
                os.fsync(f.fileno())
        except OSError as exc:
            logger.error("Failed to append audit log to %s", audit_file)
            raise RuntimeError("Audit log could not be written.") from exc

    def read_logs(self, project_path: Path) -> List[AuditEntry]:
        audit_file = project_path / self.filename
        entries: List[AuditEntry] = []
        if not audit_file.exists():
            return entries
            
        try:
            with open(audit_file, "r", encoding="utf-8") as f:
                for index, line in enumerate(f):
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    entries.append(AuditEntry(
                        event_id=data.get("event_id", f"legacy-{index}-{data['timestamp']}"),
                        timestamp=data["timestamp"],
                        action=data["action"],
                        file_name=data["file_name"],
                        destination_path=data["destination_path"],
                        previous_version_path=data.get("previous_version_path"),
                        undo_of_event_id=data.get("undo_of_event_id"),
                        user=data.get("user", "System")
                    ))
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            logger.error("Failed to read audit logs from %s", audit_file)
            raise RuntimeError("Audit log could not be read.") from exc
        return entries
