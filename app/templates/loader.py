import json
from pathlib import Path
from typing import List, Dict, Optional
from app.models.template import ProjectTemplate
from app.models.domain import Phase, Task

class TemplateLoader:
    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            self.templates_dir = Path(__file__).parent
            
    def list_templates(self) -> List[Dict[str, str]]:
        templates = []
        for p in self.templates_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding='utf-8'))
                templates.append({
                    "id": p.stem,
                    "name": data.get("name", p.stem),
                    "description": data.get("description", "")
                })
            except Exception:
                pass
        return templates
        
    def load_template(self, template_id: str) -> Optional[ProjectTemplate]:
        p = self.templates_dir / f"{template_id}.json"
        if not p.exists():
            return None
            
        data = json.loads(p.read_text(encoding='utf-8'))
        
        phases = []
        for ph in data.get("phases", []):
            phases.append(Phase(**ph))
            
        tasks = []
        for t in data.get("default_tasks", []):
            tasks.append(Task(**t))
            
        return ProjectTemplate(
            template_id=template_id,
            name=data.get("name", template_id),
            description=data.get("description", ""),
            folder_structure=data.get("folder_structure", []),
            phases=phases,
            default_tasks=tasks,
            required_artifacts=data.get("required_artifacts", [])
        )
