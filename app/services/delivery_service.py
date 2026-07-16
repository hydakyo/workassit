import shutil
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone

from app.models.project import Project
from app.models.domain import Delivery

logger = logging.getLogger(__name__)

class DeliveryService:
    def create_delivery_package(self, project: Project) -> Optional[str]:
        project_dir = Path(project.path)
        if not project_dir.exists():
            return None
            
        version = f"1.{len(project.deliveries)}"
        package_name = f"{project.metadata.project_name}_Release_v{version}"
        package_name = "".join(c if c.isalnum() or c in '._-' else "_" for c in package_name)
        
        delivery_dir = project_dir / "04_Delivery"
        delivery_dir.mkdir(exist_ok=True)
        
        output_path = delivery_dir / package_name
        
        try:
            staging_dir = project_dir / ".staging_delivery"
            if staging_dir.exists():
                shutil.rmtree(staging_dir)
            staging_dir.mkdir()
            
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
            
            # 2. Copy artifacts
            for art in project.artifacts:
                if art.path:
                    src = project_dir / art.path
                    if src.is_file():
                        # Copy to staging maintaining flat structure
                        dest = staging_dir / src.name
                        shutil.copy2(src, dest)
                        manifest_artifacts.append({
                            "id": art.artifact_id,
                            "type": art.type,
                            "file": src.name
                        })
                        included_artifacts.append(art.artifact_id)
                        
            # Write manifest.json
            with open(staging_dir / "manifest.json", "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=4)
                
            # 3. Zip
            archive_path = shutil.make_archive(str(output_path), 'zip', str(staging_dir))
            
            # Clean up staging
            shutil.rmtree(staging_dir)
            
            # 4. Create Delivery object
            delivery = Delivery(
                version=version,
                manifest=manifest,
                included_artifacts=included_artifacts,
                generated_by="System"
            )
            project.deliveries.append(delivery)
            
            logger.info(f"Created delivery package at {archive_path}")
            return str(Path(archive_path).relative_to(project_dir))
        except Exception as e:
            logger.error(f"Failed to create delivery package: {e}")
            return None
