import shutil
import logging
from pathlib import Path
from typing import Optional

from app.models.project import Project

logger = logging.getLogger(__name__)

class DeliveryService:
    def create_delivery_package(self, project: Project) -> Optional[str]:
        project_dir = Path(project.path)
        if not project_dir.exists():
            return None
            
        package_name = f"{project.metadata.project_name}_Delivery"
        # Clean the name
        package_name = "".join(c if c.isalnum() else "_" for c in package_name).strip("_")
        
        # We will create a zip file inside the project directory (or user's desktop, but let's put it next to project root for safety in testing, actually inside 04_Delivery)
        delivery_dir = project_dir / "04_Delivery"
        delivery_dir.mkdir(exist_ok=True)
        
        output_path = delivery_dir / package_name
        
        try:
            # Create a temporary staging directory to filter out .versions and .json
            staging_dir = project_dir / ".staging_delivery"
            if staging_dir.exists():
                shutil.rmtree(staging_dir)
            staging_dir.mkdir()
            
            for item in project_dir.iterdir():
                # Skip staging, delivery dir itself to avoid recursion, and internals
                if item.name in [".staging_delivery", "04_Delivery", ".versions", "project.json", "audit.jsonl", "checklist.json"]:
                    continue
                    
                if item.is_dir():
                    shutil.copytree(item, staging_dir / item.name)
                elif item.is_file():
                    shutil.copy2(item, staging_dir / item.name)
            
            archive_path = shutil.make_archive(str(output_path), 'zip', str(staging_dir))
            
            # Clean up staging
            shutil.rmtree(staging_dir)
            
            logger.info(f"Created delivery package at {archive_path}")
            return archive_path
        except Exception as e:
            logger.error(f"Failed to create delivery package: {e}")
            return None
