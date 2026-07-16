from app.repositories.audit_repository import AuditRepository
from app.models.audit import AuditEntry
from unittest.mock import patch

def test_audit_repo_read_empty(tmp_path):
    repo = AuditRepository()
    assert repo.read_logs(tmp_path) == []

def test_audit_repo_append_exception(tmp_path, caplog):
    repo = AuditRepository()
    # Mock open to raise exception
    with patch("builtins.open", side_effect=PermissionError("Denied")):
        repo.append_log(tmp_path, AuditEntry(timestamp="2026", action="Action", file_name="File", destination_path="Dest"))
    assert "Failed to append audit log" in caplog.text

def test_audit_repo_read_exception(tmp_path, caplog):
    repo = AuditRepository()
    (tmp_path / "audit.jsonl").write_text('{"action": "test"}')
    with patch("builtins.open", side_effect=PermissionError("Denied")):
        logs = repo.read_logs(tmp_path)
    assert logs == []
    assert "Failed to read audit logs" in caplog.text

def test_audit_repo_read_empty_lines(tmp_path):
    repo = AuditRepository()
    (tmp_path / "audit.jsonl").write_text('\n{"action": "Action", "file_name": "F", "destination_path": "D", "timestamp": "2026", "user": "sys"}\n\n')
    logs = repo.read_logs(tmp_path)
    assert len(logs) == 1
    assert logs[0].action == "Action"
