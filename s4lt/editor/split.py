"""Package split functionality."""

from pathlib import Path
from collections import defaultdict

from s4lt.core import Package, get_type_name
from s4lt.core.writer import write_package


def split_by_type(
    package_path: str,
    output_dir: str,
    prefix: str | None = None,
) -> list[str]:
    """Split a package into multiple packages by resource type.

    Args:
        package_path: Path to source package
        output_dir: Directory for output packages
        prefix: Prefix for output files (defaults to source filename)

    Returns:
        List of created package paths
    """
    pkg_path = Path(package_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if prefix is None:
        prefix = pkg_path.stem

    # Group resources by type
    by_type: dict[int, list[dict]] = defaultdict(list)

    with Package.open(package_path) as pkg:
        for res in pkg.resources:
            by_type[res.type_id].append({
                "type_id": res.type_id,
                "group_id": res.group_id,
                "instance_id": res.instance_id,
                "data": res.extract(),
                "compress": res.is_compressed,
            })

    # Write one package per type
    created = []
    for type_id, resources in by_type.items():
        type_name = get_type_name(type_id)
        output_path = out_dir / f"{prefix}_{type_name}.package"
        write_package(output_path, resources, create_backup=False)
        created.append(str(output_path))

    return created


def split_by_group(
    package_path: str,
    output_dir: str,
    prefix: str | None = None,
) -> list[str]:
    """Split a package into multiple packages by group ID.

    Args:
        package_path: Path to source package
        output_dir: Directory for output packages
        prefix: Prefix for output files

    Returns:
        List of created package paths
    """
    pkg_path = Path(package_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if prefix is None:
        prefix = pkg_path.stem

    # Group resources by group ID
    by_group: dict[int, list[dict]] = defaultdict(list)

    with Package.open(package_path) as pkg:
        for res in pkg.resources:
            by_group[res.group_id].append({
                "type_id": res.type_id,
                "group_id": res.group_id,
                "instance_id": res.instance_id,
                "data": res.extract(),
                "compress": res.is_compressed,
            })

    # Write one package per group
    created = []
    for group_id, resources in by_group.items():
        output_path = out_dir / f"{prefix}_G{group_id:08X}.package"
        write_package(output_path, resources, create_backup=False)
        created.append(str(output_path))

    return created


def extract_all(
    package_path: str,
    output_dir: str,
) -> list[str]:
    """Extract all resources as individual files.

    Args:
        package_path: Path to source package
        output_dir: Directory for output files

    Returns:
        List of created file paths
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    created = []
    with Package.open(package_path) as pkg:
        for res in pkg.resources:
            type_name = get_type_name(res.type_id)
            filename = f"{type_name}_{res.group_id:08X}_{res.instance_id:016X}.bin"
            output_path = out_dir / filename
            output_path.write_bytes(res.extract())
            created.append(str(output_path))

    return created
