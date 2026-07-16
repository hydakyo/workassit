"""Transactional CSV inventory import for deployment rollout projects."""

import csv
import ipaddress
from pathlib import Path
from typing import Dict, List

from app.models.domain import Device, Site
from app.models.project import Project


class RolloutImportError(ValueError):
    """Raised when an inventory CSV cannot be imported without partial changes."""


class RolloutService:
    """Validate deployment inventory before applying it to a project in one save operation."""

    def import_devices_csv(self, project: Project, source_path: str) -> int:
        """Import rows from CSV, creating named sites only after all rows validate."""
        path = Path(source_path)
        if not path.is_file() or path.suffix.lower() != ".csv":
            raise RolloutImportError("Select an existing CSV inventory file.")
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as source_file:
                rows = list(csv.DictReader(source_file))
        except (OSError, csv.Error) as exc:
            raise RolloutImportError("Inventory CSV could not be read.") from exc
        if not rows:
            raise RolloutImportError("Inventory CSV has no data rows.")
        required_columns = {"site_name", "serial_number"}
        actual_columns = set(rows[0])
        if not required_columns.issubset(actual_columns):
            raise RolloutImportError("CSV must contain site_name and serial_number columns.")

        known_serials = {device.serial_number.casefold() for device in project.devices}
        imported_serials: set[str] = set()
        pending_rows: List[Dict[str, str]] = []
        for line_number, row in enumerate(rows, start=2):
            site_name = (row.get("site_name") or "").strip()
            serial_number = (row.get("serial_number") or "").strip()
            management_ip = (row.get("management_ip") or "").strip()
            if not site_name or not serial_number:
                raise RolloutImportError(f"Line {line_number} requires site_name and serial_number.")
            serial_key = serial_number.casefold()
            if serial_key in known_serials or serial_key in imported_serials:
                raise RolloutImportError(f"Line {line_number} has a duplicate serial number.")
            if management_ip:
                try:
                    ipaddress.ip_address(management_ip)
                except ValueError as exc:
                    raise RolloutImportError(f"Line {line_number} has an invalid management_ip.") from exc
            imported_serials.add(serial_key)
            pending_rows.append({key: (value or "").strip() for key, value in row.items() if key is not None})

        sites_by_name = {site.name.casefold(): site for site in project.sites}
        new_sites: List[Site] = []
        new_devices: List[Device] = []
        for row in pending_rows:
            site_name = row["site_name"]
            site = sites_by_name.get(site_name.casefold())
            if site is None:
                site = Site(name=site_name, location=row.get("site_location", ""), contact=row.get("site_contact") or None)
                sites_by_name[site_name.casefold()] = site
                new_sites.append(site)
            new_devices.append(
                Device(
                    site_id=site.site_id,
                    serial_number=row["serial_number"],
                    current_hostname=row.get("current_hostname", ""),
                    target_hostname=row.get("target_hostname", ""),
                    model=row.get("model", ""),
                    management_ip=row.get("management_ip", ""),
                    firmware=row.get("firmware", ""),
                    deployment_wave=row.get("deployment_wave", ""),
                )
            )
        project.sites.extend(new_sites)
        project.devices.extend(new_devices)
        return len(new_devices)
