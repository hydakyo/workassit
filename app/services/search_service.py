"""Read-only query service for the local SQLite project index."""

from typing import Dict, List

from app.database.connection import DatabaseManager


class SearchService:
    """Provide lightweight dashboard metrics and project search from the local index."""

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def search_projects(self, query: str, limit: int = 100) -> List[Dict[str, str]]:
        """Find indexed projects by case-insensitive name, customer, type, or stage."""
        normalized_query = query.strip()
        if not normalized_query:
            return []
        escaped_query = normalized_query.replace("%", "\\%").replace("_", "\\_")
        like_query = f"%{escaped_query}%"
        with self.database.get_connection() as connection:
            rows = connection.execute(
                """
                SELECT id, path, name, customer, type, stage, updated_at
                FROM projects
                WHERE name LIKE ? ESCAPE '\\' OR customer LIKE ? ESCAPE '\\'
                    OR type LIKE ? ESCAPE '\\' OR stage LIKE ? ESCAPE '\\'
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (like_query, like_query, like_query, like_query, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_dashboard_metrics(self) -> Dict[str, int]:
        """Return aggregate counts used by the local dashboard."""
        with self.database.get_connection() as connection:
            projects = connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
            tasks_total = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            tasks_done = connection.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Done'").fetchone()[0]
            artifacts_attached = connection.execute(
                "SELECT COUNT(*) FROM artifacts WHERE path <> ''"
            ).fetchone()[0]
        return {
            "projects": int(projects),
            "tasks_total": int(tasks_total),
            "tasks_done": int(tasks_done),
            "artifacts_attached": int(artifacts_attached),
        }
