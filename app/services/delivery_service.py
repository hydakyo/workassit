import shutil
import logging
import json
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone

from app.models.project import Project
from app.models.domain import Delivery
from app.utils.path_validator import PathViolationError, resolve_project_path

logger = logging.getLogger(__name__)

class DeliveryService:
    def validate_readiness(self, project: Project) -> List[str]:
        """Return the delivery blockers for a project without mutating project data."""
        blockers: List[str] = []
        incomplete_tasks = [task.title for task in project.tasks if task.status != "Done"]
        if incomplete_tasks:
            blockers.append(f"{len(incomplete_tasks)} task(s) are not complete.")
        missing_artifacts = [artifact.type for artifact in project.artifacts if not artifact.path]
        if missing_artifacts:
            blockers.append(f"{len(missing_artifacts)} required artifact(s) are missing.")
        unapproved_artifacts = [
            artifact.type for artifact in project.artifacts if artifact.path and artifact.status != "Approved"
        ]
        if unapproved_artifacts:
            blockers.append(f"{len(unapproved_artifacts)} attached artifact(s) are not approved.")
        return blockers

    def _sha256_file(self, file_path: Path) -> str:
        digest = hashlib.sha256()
        with open(file_path, "rb") as source_file:
            for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def create_delivery_package(self, project: Project) -> Optional[str]:
        project_dir = Path(project.path)
        if not project_dir.exists():
            return None
        readiness_blockers = self.validate_readiness(project)
        if readiness_blockers:
            logger.warning("Delivery blocked for project %s: %s", project.metadata.project_name, readiness_blockers)
            return None
            
        version = f"1.{len(project.deliveries)}"
        package_name = f"{project.metadata.project_name}_Release_v{version}"
        package_name = "".join(c if c.isalnum() or c in '._-' else "_" for c in package_name)
        
        delivery_dir = project_dir / "05_Delivery"
        if not delivery_dir.exists() and (project_dir / "04_Delivery").exists():
            delivery_dir = project_dir / "04_Delivery"
        delivery_dir.mkdir(exist_ok=True)
        
        output_path = delivery_dir / package_name
        archive_output_path = output_path.with_suffix(".zip")
        if archive_output_path.exists():
            logger.warning("Refusing to overwrite existing delivery package: %s", archive_output_path)
            return None
        
        staging_dir: Optional[Path] = None
        try:
            staging_dir = Path(tempfile.mkdtemp(prefix=".staging_delivery_", dir=project_dir))
            
            # 1. Generate Manifest
            manifest_artifacts: List[Dict[str, str]] = []
            manifest = {
                "project_name": project.metadata.project_name,
                "customer": project.metadata.customer_name,
                "version": version,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "artifacts": manifest_artifacts
            }
            
            included_artifacts: List[str] = []
            used_filenames: set[str] = set()
            
            # 2. Copy artifacts
            for art in project.artifacts:
                if art.path:
                    src = resolve_project_path(project_dir, art.path)
                    if src.is_file():
                        artifact_filename = src.name
                        if artifact_filename in used_filenames:
                            artifact_filename = f"{art.artifact_id[:8]}_{src.name}"
                        used_filenames.add(artifact_filename)
                        dest = staging_dir / artifact_filename
                        shutil.copy2(src, dest)
                        art.checksum = self._sha256_file(src)
                        manifest_artifacts.append({
                            "id": art.artifact_id,
                            "type": art.type,
                            "file": artifact_filename,
                            "sha256": art.checksum,
                        })
                        included_artifacts.append(art.artifact_id)
                        
            # Write manifest.json
            with open(staging_dir / "manifest.json", "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=4)
                
            # 3. Zip
            archive_path = shutil.make_archive(str(output_path), 'zip', str(staging_dir))
            
            # 4. Create Delivery object
            delivery = Delivery(
                version=version,
                manifest=manifest,
                included_artifacts=included_artifacts,
                checksum=self._sha256_file(Path(archive_path)),
                generated_by="System"
            )
            project.deliveries.append(delivery)
            
            logger.info(f"Created delivery package at {archive_path}")
            return str(Path(archive_path).relative_to(project_dir))
        except (OSError, PathViolationError, ValueError) as e:
            logger.error(f"Failed to create delivery package: {e}")
            return None
        finally:
            if staging_dir and staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)
