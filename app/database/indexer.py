import logging

from app.database.connection import DatabaseManager
from app.models.project import Project

logger = logging.getLogger(__name__)

class Indexer:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def sync_project(self, project: Project) -> None:
        """Sync a parsed project into the global SQLite index."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if project exists by path
                cursor.execute("SELECT id FROM projects WHERE path = ?", (str(project.path),))
                row = cursor.fetchone()
                
                # We need to ensure the project has an ID
                # For backward compatibility, if it doesn't have an ID, we'll assign one when parsing
                # But wait, Project.metadata should have an ID now.
                # Assuming Project model will be updated.
                project_id = getattr(project.metadata, 'project_id', None)
                if not project_id:
                    if row:
                        project_id = row['id']
                    else:
                        import uuid
                        project_id = str(uuid.uuid4())
                        project.metadata.project_id = project_id # Update the object
                
                # Upsert Project
                cursor.execute("""
                    INSERT INTO projects (id, path, name, customer, type, stage, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        path=excluded.path,
                        name=excluded.name,
                        customer=excluded.customer,
                        type=excluded.type,
                        stage=excluded.stage,
                        updated_at=excluded.updated_at
                """, (
                    project_id,
                    str(project.path),
                    project.metadata.project_name,
                    project.metadata.customer_name,
                    project.metadata.project_type,
                    getattr(project.metadata.stage, 'value', project.metadata.stage),
                    project.metadata.updated_at
                ))
                
                # Sync Tasks (Clear and Insert)
                cursor.execute("DELETE FROM tasks WHERE project_id = ?", (project_id,))
                if hasattr(project, 'tasks') and project.tasks:
                    for t in project.tasks:
                        cursor.execute("""
                            INSERT INTO tasks (id, project_id, title, description, status, priority, owner, due_date, phase, category, created_at, completed_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            t.id, project_id, t.title, t.description, t.status, t.priority,
                            t.owner, t.due_date, t.phase, t.category, t.created_at, t.completed_at
                        ))
                        
                # Sync Artifacts
                cursor.execute("DELETE FROM artifacts WHERE project_id = ?", (project_id,))
                if hasattr(project, 'artifacts') and project.artifacts:
                    for a in project.artifacts:
                        cursor.execute("""
                            INSERT INTO artifacts (id, project_id, type, path, status, version, checksum, updated_at, owner)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            a.artifact_id, project_id, a.type, a.path, a.status, a.version,
                            a.checksum, a.updated_at, a.owner
                        ))
                
                # Sync Deliveries
                cursor.execute("DELETE FROM deliveries WHERE project_id = ?", (project_id,))
                if hasattr(project, 'deliveries') and project.deliveries:
                    for d in project.deliveries:
                        cursor.execute("""
                            INSERT INTO deliveries (id, project_id, version, checksum, generated_time, generated_by, approval_state, release_notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            d.release_id, project_id, d.version, d.checksum, d.generated_time,
                            d.generated_by, d.approval_state, d.release_notes
                        ))
                
                conn.commit()
                logger.info(f"Synced project '{project.metadata.project_name}' to global index.")
        except Exception as e:
            logger.error(f"Failed to sync project at {project.path}: {e}")
            raise
