"""Tests for package split functionality."""

import tempfile
from pathlib import Path

from s4lt.editor.split import split_by_type
from s4lt.core.writer import write_package


def test_split_by_type():
    """Split should create packages per resource type."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = Path(tmpdir) / "mixed.package"
        output_dir = Path(tmpdir) / "split"
        output_dir.mkdir()

        # Create package with multiple types
        resources = [
            {"type_id": 0x220557DA, "group_id": 0, "instance_id": 0x111, "data": b"stbl1", "compress": False},
            {"type_id": 0x220557DA, "group_id": 0, "instance_id": 0x222, "data": b"stbl2", "compress": False},
            {"type_id": 0x0333406C, "group_id": 0, "instance_id": 0x333, "data": b"<xml/>", "compress": False},
        ]
        write_package(pkg_path, resources, create_backup=False)

        result = split_by_type(str(pkg_path), str(output_dir))

        assert len(result) == 2  # Two different types
        assert (output_dir / "mixed_StringTable.package").exists()
        assert (output_dir / "mixed_Tuning.package").exists()
