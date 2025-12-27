"""Tests for DBPF index table parsing."""

import io
import struct
import pytest

from s4lt.core.index import IndexEntry, parse_index
from s4lt.core.exceptions import CorruptedIndexError


def create_index(entries: list[dict], flags: int = 0) -> bytes:
    """Create a DBPF index for testing.

    Args:
        entries: List of dicts with type_id, group_id, instance_hi, instance_lo,
                 offset, file_size, mem_size, compressed
        flags: Index flags (which fields are constant)
    """
    data = bytearray()

    # Index header: flags
    data.extend(struct.pack("<I", flags))

    # If no flags, all fields are per-entry
    for entry in entries:
        data.extend(struct.pack("<I", entry.get("type_id", 0)))
        data.extend(struct.pack("<I", entry.get("group_id", 0)))
        data.extend(struct.pack("<I", entry.get("instance_hi", 0)))
        data.extend(struct.pack("<I", entry.get("instance_lo", 0)))
        data.extend(struct.pack("<I", entry.get("offset", 0)))
        # File size with compression flag in bit 31
        file_size = entry.get("file_size", 0)
        if entry.get("extended", False):
            file_size |= 0x80000000
        data.extend(struct.pack("<I", file_size))
        data.extend(struct.pack("<I", entry.get("mem_size", 0)))
        data.extend(struct.pack("<H", entry.get("compressed", 0)))
        data.extend(struct.pack("<H", 0))  # Padding

    return bytes(data)


def test_parse_empty_index():
    """Empty index should return empty list."""
    data = create_index([])
    entries = parse_index(io.BytesIO(data), entry_count=0)
    assert entries == []


def test_parse_single_entry():
    """Single entry should parse correctly."""
    data = create_index([{
        "type_id": 0x0333406C,
        "group_id": 0x00000000,
        "instance_hi": 0x12345678,
        "instance_lo": 0x9ABCDEF0,
        "offset": 1000,
        "file_size": 500,
        "mem_size": 1000,
        "compressed": 0x5A42,
    }])

    entries = parse_index(io.BytesIO(data), entry_count=1)

    assert len(entries) == 1
    e = entries[0]
    assert e.type_id == 0x0333406C
    assert e.group_id == 0x00000000
    assert e.instance_id == 0x123456789ABCDEF0
    assert e.offset == 1000
    assert e.compressed_size == 500
    assert e.uncompressed_size == 1000
    assert e.compression_type == 0x5A42
    assert e.is_compressed == True


def test_parse_uncompressed_entry():
    """Uncompressed entry should have is_compressed=False."""
    data = create_index([{
        "type_id": 0x3C1AF1F2,
        "offset": 500,
        "file_size": 200,
        "mem_size": 200,
        "compressed": 0x0000,
    }])

    entries = parse_index(io.BytesIO(data), entry_count=1)

    assert entries[0].is_compressed == False
    assert entries[0].compression_type == 0x0000


def test_parse_multiple_entries():
    """Multiple entries should all parse."""
    data = create_index([
        {"type_id": 0x0333406C, "offset": 100, "file_size": 50, "mem_size": 100, "compressed": 0x5A42},
        {"type_id": 0x034AEECB, "offset": 200, "file_size": 75, "mem_size": 150, "compressed": 0xFFFF},
        {"type_id": 0x220557DA, "offset": 300, "file_size": 25, "mem_size": 25, "compressed": 0x0000},
    ])

    entries = parse_index(io.BytesIO(data), entry_count=3)

    assert len(entries) == 3
    assert entries[0].type_id == 0x0333406C
    assert entries[1].type_id == 0x034AEECB
    assert entries[2].type_id == 0x220557DA
