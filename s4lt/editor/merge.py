"""Package merge functionality."""

from dataclasses import dataclass
from pathlib import Path

from s4lt.core import Package
from s4lt.core.writer import write_package


@dataclass
class MergeConflict:
    """A merge conflict between packages."""

    type_id: int
    group_id: int
    instance_id: int
    sources: list[tuple[str, int]]  # (path, size) pairs


def find_conflicts(package_paths: list[str]) -> list[MergeConflict]:
    """Find resources that exist in multiple packages.

    Args:
        package_paths: Paths to packages to check

    Returns:
        List of conflicts found
    """
    # Map TGI -> list of (path, size)
    tgi_sources: dict[tuple, list[tuple[str, int]]] = {}

    for path in package_paths:
        with Package.open(path) as pkg:
            for res in pkg.resources:
                tgi = (res.type_id, res.group_id, res.instance_id)
                if tgi not in tgi_sources:
                    tgi_sources[tgi] = []
                tgi_sources[tgi].append((path, res.uncompressed_size))

    # Find conflicts (TGI in multiple packages)
    conflicts = []
    for tgi, sources in tgi_sources.items():
        if len(sources) > 1:
            conflicts.append(MergeConflict(
                type_id=tgi[0],
                group_id=tgi[1],
                instance_id=tgi[2],
                sources=sources,
            ))

    return conflicts


def merge_packages(
    package_paths: list[str],
    output_path: str,
    resolutions: dict[tuple, str] | None = None,
) -> None:
    """Merge multiple packages into one.

    Args:
        package_paths: Paths to source packages
        output_path: Path for output package
        resolutions: Map of TGI -> source path for conflict resolution
                    If not provided, last package wins
    """
    if resolutions is None:
        resolutions = {}

    # Collect all resources
    all_resources: dict[tuple, dict] = {}

    for path in package_paths:
        with Package.open(path) as pkg:
            for res in pkg.resources:
                tgi = (res.type_id, res.group_id, res.instance_id)

                # Check if we have a resolution for this conflict
                if tgi in resolutions:
                    if resolutions[tgi] != path:
                        continue  # Skip, another package was chosen

                # Add/replace resource
                all_resources[tgi] = {
                    "type_id": res.type_id,
                    "group_id": res.group_id,
                    "instance_id": res.instance_id,
                    "data": res.extract(),
                    "compress": res.is_compressed,
                }

    # Write merged package
    write_package(Path(output_path), list(all_resources.values()), create_backup=False)
