"""Tests for package merge functionality."""

import tempfile
from pathlib import Path

from s4lt.editor.merge import find_conflicts, merge_packages, MergeConflict


def test_find_conflicts_detects_duplicates():
    """Should detect resources with same TGI in multiple packages."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg1 = Path(tmpdir) / "a.package"
        pkg2 = Path(tmpdir) / "b.package"

        # Create packages with same resource
        pkg1.write_bytes(create_package_with_resource(0x123, b"data1"))
        pkg2.write_bytes(create_package_with_resource(0x123, b"data2"))

        conflicts = find_conflicts([str(pkg1), str(pkg2)])

        assert len(conflicts) == 1
        assert conflicts[0].instance_id == 0x123


def test_merge_packages_creates_output():
    """Merge should create output package."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg1 = Path(tmpdir) / "a.package"
        pkg2 = Path(tmpdir) / "b.package"
        output = Path(tmpdir) / "merged.package"

        pkg1.write_bytes(create_package_with_resource(0x111, b"data1"))
        pkg2.write_bytes(create_package_with_resource(0x222, b"data2"))

        merge_packages([str(pkg1), str(pkg2)], str(output))

        assert output.exists()


def create_package_with_resource(instance_id: int, data: bytes) -> bytes:
    """Create a package with one resource."""
    from s4lt.core.writer import write_package

    resources = [{
        "type_id": 0x220557DA,
        "group_id": 0,
        "instance_id": instance_id,
        "data": data,
        "compress": False,
    }]

    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_path = Path(f.name)

    write_package(temp_path, resources, create_backup=False)
    result = temp_path.read_bytes()
    temp_path.unlink()
    return result
