"""Tests for Package class - the main API."""

import io
import struct
import tempfile
import pytest
from pathlib import Path

from s4lt.core.package import Package
from s4lt.core.exceptions import InvalidMagicError


def create_test_package(resources: list[tuple[int, bytes]] = None) -> bytes:
    """Create a minimal valid DBPF package for testing.

    Args:
        resources: List of (type_id, data) tuples
    """
    if resources is None:
        resources = []

    # Build resources data
    resource_data = b""
    entries = []
    current_offset = 96 + 4  # Header + index flags (we'll adjust)

    for type_id, data in resources:
        entries.append({
            "type_id": type_id,
            "group_id": 0,
            "instance_hi": 0,
            "instance_lo": len(entries),
            "offset": 0,  # Will be set later
            "file_size": len(data),
            "mem_size": len(data),
            "compressed": 0x0000,
        })
        resource_data += data

    # Calculate index size (4 bytes flags + 32 bytes per entry)
    index_size = 4 + (32 * len(entries))

    # Resources come after header, before index
    resource_start = 96
    index_start = resource_start + len(resource_data)

    # Update offsets
    offset = resource_start
    for i, entry in enumerate(entries):
        entry["offset"] = offset
        offset += entry["file_size"]

    # Build header
    header = bytearray(96)
    header[0:4] = b"DBPF"
    struct.pack_into("<I", header, 4, 2)   # Major version
    struct.pack_into("<I", header, 8, 1)   # Minor version
    struct.pack_into("<I", header, 36, len(entries))  # Entry count
    struct.pack_into("<I", header, 44, index_size)    # Index size
    struct.pack_into("<I", header, 64, index_start)   # Index position

    # Build index
    index = bytearray()
    index.extend(struct.pack("<I", 0))  # Flags = 0 (all per-entry)

    for entry in entries:
        index.extend(struct.pack("<I", entry["type_id"]))
        index.extend(struct.pack("<I", entry["group_id"]))
        index.extend(struct.pack("<I", entry["instance_hi"]))
        index.extend(struct.pack("<I", entry["instance_lo"]))
        index.extend(struct.pack("<I", entry["offset"]))
        index.extend(struct.pack("<I", entry["file_size"]))
        index.extend(struct.pack("<I", entry["mem_size"]))
        index.extend(struct.pack("<HH", entry["compressed"], 0))

    return bytes(header) + resource_data + bytes(index)


def test_open_valid_package():
    """Opening a valid package should work."""
    data = create_test_package([
        (0x0333406C, b"<tuning>test</tuning>"),
    ])

    with tempfile.NamedTemporaryFile(suffix=".package", delete=False) as f:
        f.write(data)
        path = f.name

    try:
        pkg = Package.open(path)
        assert pkg.version == (2, 1)
        assert len(pkg.resources) == 1
        pkg.close()
    finally:
        Path(path).unlink()


def test_context_manager():
    """Package should work as context manager."""
    data = create_test_package([])

    with tempfile.NamedTemporaryFile(suffix=".package", delete=False) as f:
        f.write(data)
        path = f.name

    try:
        with Package.open(path) as pkg:
            assert pkg.version == (2, 1)
    finally:
        Path(path).unlink()


def test_resource_extraction():
    """Should be able to extract resource data."""
    content = b"<tuning>Hello Sims!</tuning>"
    data = create_test_package([
        (0x0333406C, content),
    ])

    with tempfile.NamedTemporaryFile(suffix=".package", delete=False) as f:
        f.write(data)
        path = f.name

    try:
        with Package.open(path) as pkg:
            resource = pkg.resources[0]
            extracted = resource.extract()
            assert extracted == content
    finally:
        Path(path).unlink()


def test_find_by_type():
    """find_by_type should filter resources."""
    data = create_test_package([
        (0x0333406C, b"tuning1"),
        (0x034AEECB, b"caspart"),
        (0x0333406C, b"tuning2"),
    ])

    with tempfile.NamedTemporaryFile(suffix=".package", delete=False) as f:
        f.write(data)
        path = f.name

    try:
        with Package.open(path) as pkg:
            tuning = pkg.find_by_type(0x0333406C)
            assert len(tuning) == 2

            cas = pkg.find_by_type(0x034AEECB)
            assert len(cas) == 1
    finally:
        Path(path).unlink()


def test_invalid_file_raises():
    """Opening a non-DBPF file should raise."""
    with tempfile.NamedTemporaryFile(suffix=".package", delete=False) as f:
        f.write(b"This is not a DBPF file!")
        path = f.name

    try:
        with pytest.raises(InvalidMagicError):
            Package.open(path)
    finally:
        Path(path).unlink()


def test_iteration():
    """Should be able to iterate over resources."""
    data = create_test_package([
        (0x0333406C, b"one"),
        (0x0333406C, b"two"),
        (0x0333406C, b"three"),
    ])

    with tempfile.NamedTemporaryFile(suffix=".package", delete=False) as f:
        f.write(data)
        path = f.name

    try:
        with Package.open(path) as pkg:
            count = 0
            for resource in pkg:
                count += 1
            assert count == 3
    finally:
        Path(path).unlink()
