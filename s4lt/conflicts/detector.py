"""Conflict detection for Sims 4 packages."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from s4lt.core.package import Package
from s4lt.core.types import RESOURCE_TYPES

logger = logging.getLogger(__name__)


class ConflictSeverity(str, Enum):
    """Severity level for conflicts."""
    ERROR = "error"      # Definite problem - will cause issues
    WARNING = "warning"  # Potential problem - may cause issues
    INFO = "info"        # Informational - intentional override


@dataclass
class Conflict:
    """A detected conflict between packages."""

    type: str  # "duplicate", "override", "missing_dep"
    severity: ConflictSeverity
    resource_type: int
    resource_type_name: str
    instance_id: int
    group_id: int
    packages: list[str]  # List of package paths involved
    description: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "severity": self.severity.value,
            "resource_type": self.resource_type,
            "resource_type_name": self.resource_type_name,
            "instance_id": self.instance_id,
            "group_id": self.group_id,
            "packages": self.packages,
            "description": self.description,
        }


@dataclass
class ConflictReport:
    """Report of all detected conflicts."""

    conflicts: list[Conflict] = field(default_factory=list)
    packages_scanned: int = 0
    total_resources: int = 0
    scan_errors: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for c in self.conflicts if c.severity == ConflictSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.conflicts if c.severity == ConflictSeverity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for c in self.conflicts if c.severity == ConflictSeverity.INFO)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "conflicts": [c.to_dict() for c in self.conflicts],
            "packages_scanned": self.packages_scanned,
            "total_resources": self.total_resources,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "scan_errors": self.scan_errors,
        }


# Resource types that are commonly overridden intentionally
OVERRIDE_OK_TYPES = {
    0x0333406C,  # Tuning - mods often override game tuning
    0x025ED6F4,  # SimData
    0x545AC67A,  # CombinedTuning
    0x220557DA,  # StringTable - translation overrides
}

# Resource types that should never conflict (always warning/error)
CRITICAL_TYPES = {
    0x034AEECB,  # CASPart - duplicate CAS parts cause issues
    0xC0DB5AE7,  # ObjectDefinition
    0x319E4F1D,  # ObjectCatalog
}


def detect_conflicts(
    package_paths: list[Path],
    progress_callback: Optional[callable] = None,
) -> ConflictReport:
    """Scan packages for conflicts.

    Args:
        package_paths: List of package paths to scan
        progress_callback: Optional callback(current, total, package_name)

    Returns:
        ConflictReport with all detected conflicts
    """
    report = ConflictReport()
    report.packages_scanned = len(package_paths)

    # Map of (type, group, instance) -> list of packages
    tgi_map: dict[tuple[int, int, int], list[str]] = {}

    # Scan all packages
    for i, path in enumerate(package_paths):
        if progress_callback:
            progress_callback(i + 1, len(package_paths), path.name)

        try:
            with Package.open(path) as pkg:
                for resource in pkg.resources:
                    report.total_resources += 1
                    tgi = (resource.type_id, resource.group_id, resource.instance_id)

                    if tgi not in tgi_map:
                        tgi_map[tgi] = []
                    tgi_map[tgi].append(str(path))

        except Exception as e:
            error_msg = f"Failed to scan {path.name}: {e}"
            logger.warning(error_msg)
            report.scan_errors.append(error_msg)

    # Find conflicts (TGIs appearing in multiple packages)
    for (type_id, group_id, instance_id), packages in tgi_map.items():
        if len(packages) > 1:
            # Determine severity
            if type_id in CRITICAL_TYPES:
                severity = ConflictSeverity.ERROR
            elif type_id in OVERRIDE_OK_TYPES:
                severity = ConflictSeverity.INFO
            else:
                severity = ConflictSeverity.WARNING

            type_name = RESOURCE_TYPES.get(type_id, f"Unknown_{type_id:08X}")

            # Create descriptive message
            if len(packages) == 2:
                desc = f"Duplicate {type_name} found in 2 packages"
            else:
                desc = f"Duplicate {type_name} found in {len(packages)} packages"

            conflict = Conflict(
                type="duplicate",
                severity=severity,
                resource_type=type_id,
                resource_type_name=type_name,
                instance_id=instance_id,
                group_id=group_id,
                packages=packages,
                description=desc,
            )
            report.conflicts.append(conflict)

    # Sort conflicts by severity (errors first)
    severity_order = {
        ConflictSeverity.ERROR: 0,
        ConflictSeverity.WARNING: 1,
        ConflictSeverity.INFO: 2,
    }
    report.conflicts.sort(key=lambda c: severity_order[c.severity])

    logger.info(
        f"Conflict scan complete: {report.error_count} errors, "
        f"{report.warning_count} warnings, {report.info_count} info"
    )

    return report


def detect_script_conflicts(script_paths: list[Path]) -> list[Conflict]:
    """Detect conflicts between .ts4script files.

    Script mods can conflict if they have the same module name
    (internal Python package name).
    """
    conflicts = []

    # For now, just check for filename duplicates
    # Full implementation would extract and check Python module names
    name_map: dict[str, list[str]] = {}

    for path in script_paths:
        name = path.stem.lower()
        if name not in name_map:
            name_map[name] = []
        name_map[name].append(str(path))

    for name, paths in name_map.items():
        if len(paths) > 1:
            conflicts.append(Conflict(
                type="script_duplicate",
                severity=ConflictSeverity.WARNING,
                resource_type=0,
                resource_type_name="Script",
                instance_id=0,
                group_id=0,
                packages=paths,
                description=f"Multiple script mods with same name: {name}",
            ))

    return conflicts


def get_conflict_resolution_options(conflict: Conflict) -> list[dict]:
    """Get available resolution options for a conflict."""
    options = []

    if len(conflict.packages) == 2:
        options.append({
            "action": "keep_first",
            "label": f"Keep {Path(conflict.packages[0]).name}",
            "description": f"Disable {Path(conflict.packages[1]).name}",
        })
        options.append({
            "action": "keep_second",
            "label": f"Keep {Path(conflict.packages[1]).name}",
            "description": f"Disable {Path(conflict.packages[0]).name}",
        })
    else:
        options.append({
            "action": "keep_first",
            "label": f"Keep {Path(conflict.packages[0]).name}",
            "description": f"Disable {len(conflict.packages) - 1} other packages",
        })

    options.append({
        "action": "disable_all",
        "label": "Disable All",
        "description": "Disable all conflicting packages",
    })

    options.append({
        "action": "ignore",
        "label": "Ignore",
        "description": "Mark as reviewed and ignore this conflict",
    })

    return options
