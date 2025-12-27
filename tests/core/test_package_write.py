"""Tests for Package write support."""

import tempfile
from pathlib import Path

from s4lt.core import Package


def test_package_save_creates_backup():
    """First save should create .bak file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a minimal package
        pkg_path = Path(tmpdir) / "test.package"
        pkg_path.write_bytes(create_minimal_package())

        with Package.open(pkg_path) as pkg:
            pkg.mark_modified()
            pkg.save()

        assert (Path(tmpdir) / "test.package.bak").exists()


def test_package_add_resource():
    """Can add a new resource to package."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = Path(tmpdir) / "test.package"
        pkg_path.write_bytes(create_minimal_package())

        with Package.open(pkg_path) as pkg:
            original_count = len(pkg)
            pkg.add_resource(
                type_id=0x220557DA,  # StringTable
                group_id=0,
                instance_id=0x12345678,
                data=b"test data",
            )
            assert len(pkg) == original_count + 1
            pkg.save()

        # Verify saved correctly
        with Package.open(pkg_path) as pkg:
            assert len(pkg) == original_count + 1


def create_minimal_package() -> bytes:
    """Create a minimal valid DBPF package."""
    import struct

    # Header (96 bytes)
    header = bytearray(96)
    header[0:4] = b"DBPF"
    struct.pack_into("<I", header, 4, 2)   # version major
    struct.pack_into("<I", header, 8, 1)   # version minor
    struct.pack_into("<I", header, 36, 0)  # entry count
    struct.pack_into("<I", header, 44, 4)  # index size (just flags)
    struct.pack_into("<I", header, 64, 96) # index position

    # Index (just flags = 0)
    index = struct.pack("<I", 0)

    return bytes(header) + index
