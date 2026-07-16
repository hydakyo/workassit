from pathlib import Path

import pytest

from app.models.project import Project, ProjectMetadata
from app.services.rollout_service import RolloutImportError, RolloutService


def test_csv_import_creates_sites_and_devices_atomically(tmp_path: Path) -> None:
    source_file = tmp_path / "inventory.csv"
    source_file.write_text(
        "site_name,serial_number,management_ip,model,deployment_wave\n"
        "Hanoi,SERIAL-1,10.0.0.1,FG-100F,Wave 1\n"
        "Danang,SERIAL-2,10.0.0.2,FG-100F,Wave 2\n",
        encoding="utf-8",
    )
    project = Project(path=str(tmp_path), metadata=ProjectMetadata.create_new("Project", "Customer", "Network"))

    count = RolloutService().import_devices_csv(project, str(source_file))

    assert count == 2
    assert {site.name for site in project.sites} == {"Hanoi", "Danang"}
    assert project.devices[0].deployment_wave == "Wave 1"


def test_csv_import_rejects_invalid_row_without_mutating_project(tmp_path: Path) -> None:
    source_file = tmp_path / "invalid.csv"
    source_file.write_text("site_name,serial_number,management_ip\nHanoi,SERIAL-1,not-an-ip\n", encoding="utf-8")
    project = Project(path=str(tmp_path), metadata=ProjectMetadata.create_new("Project", "Customer", "Network"))

    with pytest.raises(RolloutImportError, match="invalid management_ip"):
        RolloutService().import_devices_csv(project, str(source_file))

    assert project.sites == []
    assert project.devices == []
