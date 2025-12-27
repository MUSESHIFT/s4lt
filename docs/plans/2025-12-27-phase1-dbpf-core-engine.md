# Phase 1: DBPF Core Engine Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python library that can open any Sims 4 .package file, list its resources, and extract them (with decompression).

**Architecture:** Layered design with DBPF reader at bottom, index parser above, compression layer, then high-level Package API. Lazy loading - don't decompress until accessed.

**Tech Stack:** Python 3.11+, struct (binary parsing), zlib (decompression), pytest (testing)

---

## Task 1: Project Setup

**Files:**
- Create: `s4lt/core/__init__.py`
- Create: `s4lt/core/exceptions.py`
- Create: `tests/__init__.py`
- Create: `tests/core/__init__.py`
- Create: `pyproject.toml`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "s4lt"
version = "0.1.0"
description = "Sims 4 Linux Toolkit"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=7.0"]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
```

**Step 2: Create exception classes**

```python
# s4lt/core/exceptions.py
"""DBPF parsing exceptions."""


class DBPFError(Exception):
    """Base exception for DBPF parsing errors."""


class InvalidMagicError(DBPFError):
    """File does not have valid DBPF magic bytes."""


class UnsupportedVersionError(DBPFError):
    """DBPF version is not supported (requires 2.x)."""


class CorruptedIndexError(DBPFError):
    """Index table is corrupted or malformed."""


class CompressionError(DBPFError):
    """Failed to decompress resource data."""


class ResourceNotFoundError(DBPFError):
    """Requested resource does not exist in package."""
```

**Step 3: Create core __init__.py**

```python
# s4lt/core/__init__.py
"""S4LT Core - DBPF parsing library."""

from s4lt.core.exceptions import (
    DBPFError,
    InvalidMagicError,
    UnsupportedVersionError,
    CorruptedIndexError,
    CompressionError,
    ResourceNotFoundError,
)

__all__ = [
    "DBPFError",
    "InvalidMagicError",
    "UnsupportedVersionError",
    "CorruptedIndexError",
    "CompressionError",
    "ResourceNotFoundError",
]
```

**Step 4: Create test __init__ files**

```python
# tests/__init__.py
# tests/core/__init__.py
```

**Step 5: Install in dev mode and verify**

Run: `cd /root/s4lt && pip install -e ".[dev]"`
Expected: Successfully installed s4lt

Run: `python -c "from s4lt.core import DBPFError; print('OK')"`
Expected: `OK`

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: project setup with exceptions"
```

---

## Task 2: Resource Type Registry

**Files:**
- Create: `s4lt/core/types.py`
- Create: `tests/core/test_types.py`

**Step 1: Write the failing test**

```python
# tests/core/test_types.py
"""Tests for resource type registry."""

from s4lt.core.types import get_type_name, RESOURCE_TYPES


def test_known_type_returns_name():
    """Known type IDs should return human-readable names."""
    assert get_type_name(0x0333406C) == "Tuning"
    assert get_type_name(0x034AEECB) == "CASPart"
    assert get_type_name(0x220557DA) == "StringTable"


def test_unknown_type_returns_hex():
    """Unknown type IDs should return formatted hex string."""
    result = get_type_name(0x12345678)
    assert result == "Unknown_12345678"


def test_resource_types_dict_exists():
    """RESOURCE_TYPES should be a non-empty dict."""
    assert isinstance(RESOURCE_TYPES, dict)
    assert len(RESOURCE_TYPES) > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_types.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/core/types.py
"""Resource type ID registry for Sims 4 packages."""

# Known resource type IDs mapped to human-readable names
# Reference: https://github.com/Kuree/Sims4Tools/wiki
RESOURCE_TYPES: dict[int, str] = {
    # CAS (Create-a-Sim)
    0x034AEECB: "CASPart",
    0x0355E0A6: "BodyBlendData",

    # Tuning & Data
    0x0333406C: "Tuning",
    0x025ED6F4: "SimData",
    0x545AC67A: "CombinedTuning",

    # Text
    0x220557DA: "StringTable",

    # Images
    0x00B2D882: "DDS",
    0x3C1AF1F2: "PNG",
    0x2F7D0004: "DST",

    # 3D Assets
    0x015A1849: "Geometry",
    0x00AE6C67: "Bone",
    0x8EAF13DE: "RIG",

    # Catalog
    0xC0DB5AE7: "CatalogObject",
    0x319E4F1D: "ObjectDefinition",

    # Animation
    0x02D5DF13: "CLIP",

    # Audio
    0x01EEF63A: "AuditoryData",

    # Thumbnails
    0x3C2A8647: "Thumbnail",
    0x5B282D45: "ThumbnailAlt",
}


def get_type_name(type_id: int) -> str:
    """Get human-readable name for a resource type ID.

    Args:
        type_id: The 32-bit resource type identifier

    Returns:
        Human-readable name if known, otherwise "Unknown_XXXXXXXX"
    """
    return RESOURCE_TYPES.get(type_id, f"Unknown_{type_id:08X}")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_types.py -v`
Expected: 3 passed

**Step 5: Update core __init__.py**

```python
# s4lt/core/__init__.py
"""S4LT Core - DBPF parsing library."""

from s4lt.core.exceptions import (
    DBPFError,
    InvalidMagicError,
    UnsupportedVersionError,
    CorruptedIndexError,
    CompressionError,
    ResourceNotFoundError,
)
from s4lt.core.types import get_type_name, RESOURCE_TYPES

__all__ = [
    "DBPFError",
    "InvalidMagicError",
    "UnsupportedVersionError",
    "CorruptedIndexError",
    "CompressionError",
    "ResourceNotFoundError",
    "get_type_name",
    "RESOURCE_TYPES",
]
```

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: resource type ID registry"
```

---

## Task 3: Header Parsing

**Files:**
- Create: `s4lt/core/header.py`
- Create: `tests/core/test_header.py`
- Create: `tests/fixtures/` (for test files)

**Step 1: Create a minimal test package fixture**

```python
# tests/fixtures/__init__.py
"""Test fixtures for DBPF parsing."""
import struct
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent


def create_minimal_dbpf() -> bytes:
    """Create a minimal valid DBPF 2.1 header (96 bytes) with empty index."""
    header = bytearray(96)

    # Magic "DBPF"
    header[0:4] = b"DBPF"

    # Version 2.1
    struct.pack_into("<I", header, 4, 2)   # Major
    struct.pack_into("<I", header, 8, 1)   # Minor

    # Index entry count = 0
    struct.pack_into("<I", header, 36, 0)

    # Index position (right after header)
    struct.pack_into("<I", header, 64, 96)

    # Index size = 4 (just the flags field, no entries)
    struct.pack_into("<I", header, 44, 4)

    # Add minimal index (just flags = 0)
    index = struct.pack("<I", 0)

    return bytes(header) + index
```

**Step 2: Write the failing test**

```python
# tests/core/test_header.py
"""Tests for DBPF header parsing."""

import io
import struct
import pytest

from s4lt.core.header import DBPFHeader, parse_header
from s4lt.core.exceptions import InvalidMagicError, UnsupportedVersionError


def create_header(magic=b"DBPF", major=2, minor=1, entry_count=0,
                  index_pos=96, index_size=4) -> bytes:
    """Create a DBPF header for testing."""
    header = bytearray(96)
    header[0:4] = magic
    struct.pack_into("<I", header, 4, major)
    struct.pack_into("<I", header, 8, minor)
    struct.pack_into("<I", header, 36, entry_count)
    struct.pack_into("<I", header, 64, index_pos)
    struct.pack_into("<I", header, 44, index_size)
    return bytes(header)


def test_parse_valid_header():
    """Valid DBPF header should parse correctly."""
    data = create_header(entry_count=5, index_pos=100, index_size=200)
    header = parse_header(io.BytesIO(data))

    assert header.magic == b"DBPF"
    assert header.version_major == 2
    assert header.version_minor == 1
    assert header.entry_count == 5
    assert header.index_position == 100
    assert header.index_size == 200


def test_invalid_magic_raises():
    """Non-DBPF files should raise InvalidMagicError."""
    data = create_header(magic=b"NOPE")
    with pytest.raises(InvalidMagicError):
        parse_header(io.BytesIO(data))


def test_unsupported_version_raises():
    """Non-2.x versions should raise UnsupportedVersionError."""
    data = create_header(major=1, minor=0)
    with pytest.raises(UnsupportedVersionError):
        parse_header(io.BytesIO(data))


def test_header_version_tuple():
    """Header should provide version as tuple."""
    data = create_header(major=2, minor=1)
    header = parse_header(io.BytesIO(data))
    assert header.version == (2, 1)
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/core/test_header.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 4: Write the implementation**

```python
# s4lt/core/header.py
"""DBPF header parsing."""

import struct
from dataclasses import dataclass
from typing import BinaryIO

from s4lt.core.exceptions import InvalidMagicError, UnsupportedVersionError

# DBPF header is always 96 bytes
HEADER_SIZE = 96
MAGIC = b"DBPF"


@dataclass(frozen=True)
class DBPFHeader:
    """Parsed DBPF file header."""

    magic: bytes
    version_major: int
    version_minor: int
    entry_count: int
    index_position: int
    index_size: int

    @property
    def version(self) -> tuple[int, int]:
        """Version as (major, minor) tuple."""
        return (self.version_major, self.version_minor)


def parse_header(file: BinaryIO) -> DBPFHeader:
    """Parse DBPF header from file.

    Args:
        file: Binary file-like object positioned at start

    Returns:
        Parsed DBPFHeader

    Raises:
        InvalidMagicError: If file doesn't start with "DBPF"
        UnsupportedVersionError: If version is not 2.x
    """
    data = file.read(HEADER_SIZE)

    if len(data) < HEADER_SIZE:
        raise InvalidMagicError("File too small to be valid DBPF")

    magic = data[0:4]
    if magic != MAGIC:
        raise InvalidMagicError(f"Invalid magic bytes: {magic!r}, expected {MAGIC!r}")

    version_major = struct.unpack_from("<I", data, 4)[0]
    version_minor = struct.unpack_from("<I", data, 8)[0]

    if version_major != 2:
        raise UnsupportedVersionError(
            f"Unsupported DBPF version {version_major}.{version_minor}, "
            "only version 2.x is supported"
        )

    entry_count = struct.unpack_from("<I", data, 36)[0]
    index_size = struct.unpack_from("<I", data, 44)[0]
    index_position = struct.unpack_from("<I", data, 64)[0]

    return DBPFHeader(
        magic=magic,
        version_major=version_major,
        version_minor=version_minor,
        entry_count=entry_count,
        index_position=index_position,
        index_size=index_size,
    )
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/core/test_header.py -v`
Expected: 4 passed

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: DBPF header parsing"
```

---

## Task 4: Index Parsing

**Files:**
- Create: `s4lt/core/index.py`
- Create: `tests/core/test_index.py`

**Step 1: Write the failing test**

```python
# tests/core/test_index.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_index.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/core/index.py
"""DBPF index table parsing."""

import struct
from dataclasses import dataclass
from typing import BinaryIO

from s4lt.core.exceptions import CorruptedIndexError

# Compression type values
COMPRESSION_NONE = 0x0000
COMPRESSION_ZLIB = 0x5A42
COMPRESSION_REFPACK = 0xFFFF
COMPRESSION_REFPACK_ALT = 0xFFFE


@dataclass(frozen=True)
class IndexEntry:
    """A single resource entry in the DBPF index."""

    type_id: int
    group_id: int
    instance_id: int  # Combined instance_hi << 32 | instance_lo
    offset: int
    compressed_size: int
    uncompressed_size: int
    compression_type: int

    @property
    def is_compressed(self) -> bool:
        """True if resource data is compressed."""
        return self.compression_type != COMPRESSION_NONE


def parse_index(file: BinaryIO, entry_count: int) -> list[IndexEntry]:
    """Parse DBPF index table.

    Args:
        file: Binary file positioned at start of index
        entry_count: Number of entries to parse (from header)

    Returns:
        List of IndexEntry objects

    Raises:
        CorruptedIndexError: If index data is malformed
    """
    if entry_count == 0:
        return []

    try:
        # Read flags to determine which fields are constant
        flags_data = file.read(4)
        if len(flags_data) < 4:
            raise CorruptedIndexError("Index too short: missing flags")

        flags = struct.unpack("<I", flags_data)[0]

        # For Sims 4, flags are typically 0 (all fields per-entry)
        # But we should handle constant fields for compatibility
        constants = {}

        # Read constant values based on flags
        # Bit 0: Type, Bit 1: Group, Bit 2: InstanceHi, Bit 3: InstanceLo
        for bit, name in enumerate(["type_id", "group_id", "instance_hi", "instance_lo"]):
            if flags & (1 << bit):
                const_data = file.read(4)
                if len(const_data) < 4:
                    raise CorruptedIndexError(f"Index too short: missing constant {name}")
                constants[name] = struct.unpack("<I", const_data)[0]

        entries = []

        for i in range(entry_count):
            # Read per-entry fields (or use constants)
            type_id = constants.get("type_id") or _read_uint32(file)
            group_id = constants.get("group_id") or _read_uint32(file)
            instance_hi = constants.get("instance_hi") or _read_uint32(file)
            instance_lo = constants.get("instance_lo") or _read_uint32(file)

            offset = _read_uint32(file)

            file_size_raw = _read_uint32(file)
            # Bit 31 indicates extended compression info
            compressed_size = file_size_raw & 0x7FFFFFFF

            uncompressed_size = _read_uint32(file)

            # Compression type is 2 bytes + 2 bytes padding
            compression_data = file.read(4)
            if len(compression_data) < 4:
                raise CorruptedIndexError(f"Index too short at entry {i}")
            compression_type = struct.unpack("<H", compression_data[:2])[0]

            # Combine instance parts into single 64-bit ID
            instance_id = (instance_hi << 32) | instance_lo

            entries.append(IndexEntry(
                type_id=type_id,
                group_id=group_id,
                instance_id=instance_id,
                offset=offset,
                compressed_size=compressed_size,
                uncompressed_size=uncompressed_size,
                compression_type=compression_type,
            ))

        return entries

    except struct.error as e:
        raise CorruptedIndexError(f"Failed to parse index: {e}")


def _read_uint32(file: BinaryIO) -> int:
    """Read a little-endian uint32."""
    data = file.read(4)
    if len(data) < 4:
        raise CorruptedIndexError("Unexpected end of index data")
    return struct.unpack("<I", data)[0]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_index.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: DBPF index table parsing"
```

---

## Task 5: Compression - zlib

**Files:**
- Create: `s4lt/core/compression.py`
- Create: `tests/core/test_compression.py`

**Step 1: Write the failing test**

```python
# tests/core/test_compression.py
"""Tests for decompression routines."""

import zlib
import pytest

from s4lt.core.compression import decompress, decompress_zlib
from s4lt.core.exceptions import CompressionError
from s4lt.core.index import COMPRESSION_NONE, COMPRESSION_ZLIB, COMPRESSION_REFPACK


def test_decompress_none_returns_unchanged():
    """Uncompressed data should pass through unchanged."""
    data = b"Hello, Sims 4!"
    result = decompress(data, COMPRESSION_NONE)
    assert result == data


def test_decompress_zlib_works():
    """zlib compressed data should decompress correctly."""
    original = b"Hello, Sims 4! " * 100  # Repetitive for good compression

    # Create zlib compressed data with 2-byte header
    compressed_body = zlib.compress(original, level=9)
    # Sims 4 uses raw deflate, not zlib wrapper
    # So we need: 2-byte header + raw deflate
    raw_deflate = zlib.compress(original, level=9)[2:-4]  # Strip zlib header/trailer
    compressed = b"\x10\xFB" + raw_deflate  # Common Sims 4 header

    result = decompress_zlib(b"\x10\xFB" + raw_deflate, len(original))
    assert result == original


def test_decompress_zlib_via_dispatcher():
    """decompress() should route to zlib handler."""
    original = b"Test data for compression"
    raw_deflate = zlib.compress(original, level=9)[2:-4]
    compressed = b"\x10\xFB" + raw_deflate

    result = decompress(compressed, COMPRESSION_ZLIB, len(original))
    assert result == original


def test_decompress_invalid_zlib_raises():
    """Invalid zlib data should raise CompressionError."""
    with pytest.raises(CompressionError):
        decompress(b"\x10\xFB\x00\x00\x00", COMPRESSION_ZLIB, 100)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_compression.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/core/compression.py
"""Decompression routines for DBPF resources."""

import zlib
from s4lt.core.exceptions import CompressionError
from s4lt.core.index import (
    COMPRESSION_NONE,
    COMPRESSION_ZLIB,
    COMPRESSION_REFPACK,
    COMPRESSION_REFPACK_ALT,
)


def decompress(data: bytes, compression_type: int, expected_size: int = 0) -> bytes:
    """Decompress resource data based on compression type.

    Args:
        data: Compressed data bytes
        compression_type: Compression type from index entry
        expected_size: Expected uncompressed size (for validation)

    Returns:
        Decompressed data

    Raises:
        CompressionError: If decompression fails
    """
    if compression_type == COMPRESSION_NONE:
        return data

    if compression_type == COMPRESSION_ZLIB:
        return decompress_zlib(data, expected_size)

    if compression_type in (COMPRESSION_REFPACK, COMPRESSION_REFPACK_ALT):
        return decompress_refpack(data, expected_size)

    raise CompressionError(f"Unknown compression type: 0x{compression_type:04X}")


def decompress_zlib(data: bytes, expected_size: int = 0) -> bytes:
    """Decompress zlib/deflate compressed data.

    Sims 4 uses raw deflate with a 2-byte header.

    Args:
        data: Compressed data with 2-byte header
        expected_size: Expected output size

    Returns:
        Decompressed data
    """
    if len(data) < 2:
        raise CompressionError("zlib data too short")

    try:
        # Skip 2-byte header, decompress raw deflate
        result = zlib.decompress(data[2:], -zlib.MAX_WBITS)

        if expected_size > 0 and len(result) != expected_size:
            raise CompressionError(
                f"Size mismatch: got {len(result)}, expected {expected_size}"
            )

        return result

    except zlib.error as e:
        raise CompressionError(f"zlib decompression failed: {e}")


def decompress_refpack(data: bytes, expected_size: int = 0) -> bytes:
    """Decompress RefPack (EA proprietary) compressed data.

    RefPack is an LZ77 variant used by EA games.

    Args:
        data: Compressed data
        expected_size: Expected output size

    Returns:
        Decompressed data
    """
    # TODO: Implement RefPack decompression
    # For now, raise a clear error
    raise CompressionError(
        "RefPack decompression not yet implemented. "
        "This resource uses EA's proprietary compression."
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_compression.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: zlib decompression support"
```

---

## Task 6: RefPack Decompression

**Files:**
- Modify: `s4lt/core/compression.py`
- Create: `tests/core/test_refpack.py`

**Step 1: Write the failing test**

```python
# tests/core/test_refpack.py
"""Tests for RefPack decompression."""

import pytest

from s4lt.core.compression import decompress_refpack, decompress
from s4lt.core.exceptions import CompressionError
from s4lt.core.index import COMPRESSION_REFPACK


# RefPack test vectors - minimal valid compressed data
# These are based on the RefPack algorithm specification

def test_refpack_literal_only():
    """RefPack with only literal bytes (no backreferences)."""
    # RefPack format:
    # Header: 0x10 0xFB followed by 3-byte big-endian uncompressed size
    # Then commands

    # Simplest case: 4 literal bytes "TEST"
    # Command 0xE0-0xFB: 0xE0 + (n-1) where n is literal count (1-28)
    # 0xE3 = 0xE0 + 3 = 4 literal bytes
    # Then 0xFC-0xFF = stop codes. 0xFC = stop with 0 literals

    compressed = bytes([
        0x10, 0xFB,           # Magic header
        0x00, 0x00, 0x04,     # Uncompressed size = 4 (big-endian)
        0xE3,                 # 4 literal bytes follow
        ord('T'), ord('E'), ord('S'), ord('T'),
        0xFC,                 # Stop
    ])

    result = decompress_refpack(compressed, expected_size=4)
    assert result == b"TEST"


def test_refpack_with_backreference():
    """RefPack with a backreference copying previous data."""
    # Compress "ABCDABCD" - second ABCD refs first
    # Literal "ABCD" (4 bytes) then backref offset=4, length=4

    # For backref: 0x80-0xBF range
    # 0x80 | ((offset-1) >> 8) | ((length-3) << 2)
    # offset=4, length=4: 0x80 | 0 | ((4-3)<<2) = 0x80 | 0x04 = 0x84
    # Then low byte of (offset-1) = 3

    compressed = bytes([
        0x10, 0xFB,           # Magic
        0x00, 0x00, 0x08,     # Size = 8
        0xE3,                 # 4 literal bytes
        ord('A'), ord('B'), ord('C'), ord('D'),
        0x84, 0x03,           # Backref: offset=4, length=4
        0xFC,                 # Stop
    ])

    result = decompress_refpack(compressed, expected_size=8)
    assert result == b"ABCDABCD"


def test_refpack_via_dispatcher():
    """decompress() should route RefPack correctly."""
    compressed = bytes([
        0x10, 0xFB, 0x00, 0x00, 0x04,
        0xE3, ord('T'), ord('E'), ord('S'), ord('T'),
        0xFC,
    ])

    result = decompress(compressed, COMPRESSION_REFPACK, expected_size=4)
    assert result == b"TEST"


def test_refpack_invalid_data_raises():
    """Invalid RefPack data should raise CompressionError."""
    with pytest.raises(CompressionError):
        decompress_refpack(b"\x10\xFB\x00\x00\x10\xFF", expected_size=16)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_refpack.py -v`
Expected: FAIL (RefPack not implemented)

**Step 3: Implement RefPack decompression**

Replace the `decompress_refpack` function in `s4lt/core/compression.py`:

```python
def decompress_refpack(data: bytes, expected_size: int = 0) -> bytes:
    """Decompress RefPack (EA proprietary) compressed data.

    RefPack is an LZ77 variant used by EA games including Sims 4.

    Format:
    - 2-byte header (0x10 0xFB for compressed)
    - 3-byte big-endian uncompressed size
    - Command stream

    Commands:
    - 0x00-0x7F: Literal + short backref
    - 0x80-0xBF: Short backref (offset < 1024, len 3-10)
    - 0xC0-0xDF: Medium backref (offset < 16384, len 4-67)
    - 0xE0-0xFB: Literal run (1-28 bytes)
    - 0xFC-0xFF: Stop codes

    Args:
        data: Compressed data with RefPack header
        expected_size: Expected output size

    Returns:
        Decompressed data
    """
    if len(data) < 5:
        raise CompressionError("RefPack data too short for header")

    # Check header
    if data[0] != 0x10 or data[1] != 0xFB:
        raise CompressionError(f"Invalid RefPack header: {data[0]:02X} {data[1]:02X}")

    # Read uncompressed size (3 bytes, big-endian)
    uncompressed_size = (data[2] << 16) | (data[3] << 8) | data[4]

    if expected_size > 0 and uncompressed_size != expected_size:
        # Use expected_size as it's more reliable
        uncompressed_size = expected_size

    output = bytearray()
    pos = 5  # Start after header

    try:
        while pos < len(data) and len(output) < uncompressed_size:
            cmd = data[pos]
            pos += 1

            if cmd <= 0x7F:
                # 0x00-0x7F: Literal bytes + short backref
                # Bits: 0 L L O O O O O
                # L = literal count (0-3), O = offset low bits
                literal_count = (cmd >> 5) & 0x03

                # Copy literals
                for _ in range(literal_count):
                    if pos >= len(data):
                        raise CompressionError("Unexpected end in literal run")
                    output.append(data[pos])
                    pos += 1

                # Backref
                if pos >= len(data):
                    raise CompressionError("Unexpected end reading backref")
                byte2 = data[pos]
                pos += 1

                offset = ((cmd & 0x1F) << 3) | ((byte2 >> 5) & 0x07)
                length = (byte2 & 0x1F) + 3

                offset += 1  # Offset is 1-based
                _copy_backref(output, offset, length)

            elif cmd <= 0xBF:
                # 0x80-0xBF: Short backref
                # offset < 1024, length 3-10
                if pos >= len(data):
                    raise CompressionError("Unexpected end in short backref")
                byte2 = data[pos]
                pos += 1

                offset = ((cmd & 0x03) << 8) | byte2
                length = ((cmd >> 2) & 0x07) + 3

                offset += 1
                _copy_backref(output, offset, length)

            elif cmd <= 0xDF:
                # 0xC0-0xDF: Medium backref
                # offset < 16384, length 4-67
                if pos + 2 > len(data):
                    raise CompressionError("Unexpected end in medium backref")
                byte2 = data[pos]
                byte3 = data[pos + 1]
                pos += 2

                offset = ((cmd & 0x03) << 12) | (byte2 << 4) | ((byte3 >> 4) & 0x0F)
                length = ((cmd >> 2) & 0x0F) + 4

                offset += 1
                _copy_backref(output, offset, length)

            elif cmd <= 0xFB:
                # 0xE0-0xFB: Literal run (1-28 bytes)
                literal_count = (cmd - 0xDF)

                for _ in range(literal_count):
                    if pos >= len(data):
                        raise CompressionError("Unexpected end in literal run")
                    output.append(data[pos])
                    pos += 1

            else:
                # 0xFC-0xFF: Stop codes
                # 0xFC = stop, 0xFD-0xFF = stop + trailing literals
                trailing = cmd - 0xFC
                for _ in range(trailing):
                    if pos >= len(data):
                        break
                    output.append(data[pos])
                    pos += 1
                break

        result = bytes(output)

        if expected_size > 0 and len(result) != expected_size:
            raise CompressionError(
                f"RefPack size mismatch: got {len(result)}, expected {expected_size}"
            )

        return result

    except IndexError as e:
        raise CompressionError(f"RefPack decompression failed: {e}")


def _copy_backref(output: bytearray, offset: int, length: int) -> None:
    """Copy bytes from earlier in output (backref)."""
    if offset > len(output):
        raise CompressionError(f"Invalid backref offset {offset} (output size {len(output)})")

    start = len(output) - offset
    for i in range(length):
        # Must read one at a time - backref can overlap with destination
        output.append(output[start + i])
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_refpack.py -v`
Expected: 4 passed

**Step 5: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests pass

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: RefPack decompression support"
```

---

## Task 7: Resource Class

**Files:**
- Create: `s4lt/core/resource.py`
- Create: `tests/core/test_resource.py`

**Step 1: Write the failing test**

```python
# tests/core/test_resource.py
"""Tests for Resource class."""

import io
import pytest

from s4lt.core.resource import Resource
from s4lt.core.index import IndexEntry, COMPRESSION_NONE, COMPRESSION_ZLIB
from s4lt.core.types import get_type_name


def test_resource_properties():
    """Resource should expose index entry properties."""
    entry = IndexEntry(
        type_id=0x0333406C,
        group_id=0x00000000,
        instance_id=0x123456789ABCDEF0,
        offset=1000,
        compressed_size=500,
        uncompressed_size=1000,
        compression_type=COMPRESSION_ZLIB,
    )

    # Mock file
    file = io.BytesIO(b"\x00" * 2000)

    resource = Resource(entry, file)

    assert resource.type_id == 0x0333406C
    assert resource.type_name == "Tuning"
    assert resource.group_id == 0x00000000
    assert resource.instance_id == 0x123456789ABCDEF0
    assert resource.is_compressed == True
    assert resource.compressed_size == 500
    assert resource.uncompressed_size == 1000


def test_resource_extract_uncompressed():
    """Extracting uncompressed resource returns raw data."""
    raw_data = b"Hello, this is raw tuning data!"

    # Create file with data at offset 100
    file_data = b"\x00" * 100 + raw_data
    file = io.BytesIO(file_data)

    entry = IndexEntry(
        type_id=0x0333406C,
        group_id=0,
        instance_id=0,
        offset=100,
        compressed_size=len(raw_data),
        uncompressed_size=len(raw_data),
        compression_type=COMPRESSION_NONE,
    )

    resource = Resource(entry, file)
    result = resource.extract()

    assert result == raw_data


def test_resource_str():
    """Resource should have readable string representation."""
    entry = IndexEntry(
        type_id=0x0333406C,
        group_id=0x00000001,
        instance_id=0xABCDEF0123456789,
        offset=100,
        compressed_size=50,
        uncompressed_size=100,
        compression_type=COMPRESSION_ZLIB,
    )

    file = io.BytesIO(b"\x00" * 200)
    resource = Resource(entry, file)

    s = str(resource)
    assert "Tuning" in s
    assert "ABCDEF0123456789" in s.upper()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_resource.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/core/resource.py
"""Resource class for lazy extraction from DBPF packages."""

from typing import BinaryIO

from s4lt.core.index import IndexEntry
from s4lt.core.types import get_type_name
from s4lt.core.compression import decompress


class Resource:
    """A single resource in a DBPF package.

    Resources are lazily extracted - data is only read and
    decompressed when extract() is called.
    """

    def __init__(self, entry: IndexEntry, file: BinaryIO):
        """Create a Resource.

        Args:
            entry: Index entry with resource metadata
            file: Open file handle to read data from
        """
        self._entry = entry
        self._file = file
        self._cached_data: bytes | None = None

    @property
    def type_id(self) -> int:
        """Resource type ID."""
        return self._entry.type_id

    @property
    def type_name(self) -> str:
        """Human-readable type name."""
        return get_type_name(self._entry.type_id)

    @property
    def group_id(self) -> int:
        """Resource group ID."""
        return self._entry.group_id

    @property
    def instance_id(self) -> int:
        """Resource instance ID (64-bit)."""
        return self._entry.instance_id

    @property
    def is_compressed(self) -> bool:
        """True if resource data is compressed."""
        return self._entry.is_compressed

    @property
    def compressed_size(self) -> int:
        """Size of data on disk (compressed)."""
        return self._entry.compressed_size

    @property
    def uncompressed_size(self) -> int:
        """Size of data when decompressed."""
        return self._entry.uncompressed_size

    @property
    def compression_type(self) -> int:
        """Compression type code."""
        return self._entry.compression_type

    @property
    def offset(self) -> int:
        """File offset where data begins."""
        return self._entry.offset

    def extract(self) -> bytes:
        """Extract and decompress resource data.

        Returns:
            Decompressed resource data

        Note:
            Result is cached after first extraction.
        """
        if self._cached_data is not None:
            return self._cached_data

        # Seek to resource offset and read compressed data
        self._file.seek(self._entry.offset)
        compressed_data = self._file.read(self._entry.compressed_size)

        # Decompress
        self._cached_data = decompress(
            compressed_data,
            self._entry.compression_type,
            self._entry.uncompressed_size,
        )

        return self._cached_data

    def __str__(self) -> str:
        """Human-readable representation."""
        compressed = " (compressed)" if self.is_compressed else ""
        return (
            f"<Resource {self.type_name} "
            f"G:{self.group_id:08X} "
            f"I:{self.instance_id:016X} "
            f"{self.uncompressed_size} bytes{compressed}>"
        )

    def __repr__(self) -> str:
        return self.__str__()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_resource.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: Resource class with lazy extraction"
```

---

## Task 8: Package Class (Main API)

**Files:**
- Create: `s4lt/core/package.py`
- Create: `tests/core/test_package.py`

**Step 1: Write the failing test**

```python
# tests/core/test_package.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_package.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write the implementation**

```python
# s4lt/core/package.py
"""Package class - main API for reading DBPF packages."""

from pathlib import Path
from typing import BinaryIO, Iterator

from s4lt.core.header import parse_header, DBPFHeader
from s4lt.core.index import parse_index, IndexEntry
from s4lt.core.resource import Resource


class Package:
    """A Sims 4 .package file.

    Usage:
        with Package.open("mod.package") as pkg:
            for resource in pkg.resources:
                print(resource)
                data = resource.extract()
    """

    def __init__(self, file: BinaryIO, header: DBPFHeader, resources: list[Resource]):
        """Create a Package. Use Package.open() instead."""
        self._file = file
        self._header = header
        self._resources = resources

    @classmethod
    def open(cls, path: str | Path) -> "Package":
        """Open a DBPF package file.

        Args:
            path: Path to .package file

        Returns:
            Package instance

        Raises:
            InvalidMagicError: If file is not a valid DBPF
            UnsupportedVersionError: If DBPF version is not 2.x
            FileNotFoundError: If file doesn't exist
        """
        path = Path(path)
        file = open(path, "rb")

        try:
            # Parse header
            header = parse_header(file)

            # Seek to index and parse
            file.seek(header.index_position)
            entries = parse_index(file, header.entry_count)

            # Create Resource objects
            resources = [Resource(entry, file) for entry in entries]

            return cls(file, header, resources)

        except Exception:
            file.close()
            raise

    @property
    def version(self) -> tuple[int, int]:
        """DBPF version as (major, minor)."""
        return self._header.version

    @property
    def resources(self) -> list[Resource]:
        """List of all resources in the package."""
        return self._resources

    def find_by_type(self, type_id: int) -> list[Resource]:
        """Find all resources with a specific type ID.

        Args:
            type_id: The type ID to search for

        Returns:
            List of matching resources
        """
        return [r for r in self._resources if r.type_id == type_id]

    def find_by_instance(self, instance_id: int) -> Resource | None:
        """Find a resource by instance ID.

        Args:
            instance_id: The 64-bit instance ID

        Returns:
            Matching resource or None
        """
        for r in self._resources:
            if r.instance_id == instance_id:
                return r
        return None

    def close(self) -> None:
        """Close the underlying file handle."""
        if self._file:
            self._file.close()
            self._file = None

    def __enter__(self) -> "Package":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __iter__(self) -> Iterator[Resource]:
        return iter(self._resources)

    def __len__(self) -> int:
        return len(self._resources)

    def __str__(self) -> str:
        return f"<Package v{self.version[0]}.{self.version[1]} with {len(self)} resources>"

    def __repr__(self) -> str:
        return self.__str__()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_package.py -v`
Expected: 6 passed

**Step 5: Update core __init__.py with full exports**

```python
# s4lt/core/__init__.py
"""S4LT Core - DBPF parsing library."""

from s4lt.core.exceptions import (
    DBPFError,
    InvalidMagicError,
    UnsupportedVersionError,
    CorruptedIndexError,
    CompressionError,
    ResourceNotFoundError,
)
from s4lt.core.types import get_type_name, RESOURCE_TYPES
from s4lt.core.package import Package
from s4lt.core.resource import Resource
from s4lt.core.index import IndexEntry

__all__ = [
    # Exceptions
    "DBPFError",
    "InvalidMagicError",
    "UnsupportedVersionError",
    "CorruptedIndexError",
    "CompressionError",
    "ResourceNotFoundError",
    # Types
    "get_type_name",
    "RESOURCE_TYPES",
    # Main API
    "Package",
    "Resource",
    "IndexEntry",
]
```

**Step 6: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests pass

**Step 7: Commit**

```bash
git add -A
git commit -m "feat: Package class - complete DBPF reading API"
```

---

## Task 9: CLI Test Script

**Files:**
- Create: `s4lt/cli/__init__.py`
- Create: `s4lt/cli/package_info.py`

**Step 1: Create the CLI script**

```python
# s4lt/cli/__init__.py
"""S4LT Command Line Interface."""
```

```python
# s4lt/cli/package_info.py
#!/usr/bin/env python3
"""Simple CLI to test package reading.

Usage:
    python -m s4lt.cli.package_info <path_to_package>
"""

import sys
from pathlib import Path
from collections import Counter

from s4lt.core import Package, DBPFError


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m s4lt.cli.package_info <package_path>")
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"Error: File not found: {path}")
        sys.exit(1)

    try:
        with Package.open(path) as pkg:
            print(f"Package: {path.name}")
            print(f"Version: {pkg.version[0]}.{pkg.version[1]}")
            print(f"Resources: {len(pkg)}")
            print()

            # Count by type
            type_counts = Counter(r.type_name for r in pkg.resources)

            print("Resource Types:")
            for type_name, count in type_counts.most_common():
                print(f"  {type_name}: {count}")
            print()

            # List first 10 resources
            print("First 10 Resources:")
            for i, resource in enumerate(pkg.resources[:10]):
                print(f"  [{i}] {resource}")

            if len(pkg.resources) > 10:
                print(f"  ... and {len(pkg.resources) - 10} more")

            # Try extracting first resource
            if pkg.resources:
                print()
                print("Testing extraction of first resource...")
                r = pkg.resources[0]
                try:
                    data = r.extract()
                    print(f"  Extracted {len(data)} bytes")
                    if r.type_name == "Tuning" and data[:5] == b"<?xml":
                        print(f"  Preview: {data[:100].decode('utf-8', errors='replace')}...")
                except Exception as e:
                    print(f"  Extraction failed: {e}")

    except DBPFError as e:
        print(f"Error reading package: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 2: Test with a placeholder**

Run: `python -m s4lt.cli.package_info --help 2>&1 || echo "Script runs"`
Expected: Shows usage message

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: CLI package_info script for testing"
```

---

## Task 10: Integration Test with Real Package

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_real_package.py`

**Step 1: Create integration test (skipped if no test file)**

```python
# tests/integration/__init__.py
"""Integration tests requiring real Sims 4 files."""
```

```python
# tests/integration/test_real_package.py
"""Integration tests with real .package files.

These tests are skipped if TEST_PACKAGE_PATH env var is not set.
Set it to a path to a real Sims 4 .package file to run these tests.

Example:
    TEST_PACKAGE_PATH=/path/to/mod.package pytest tests/integration/ -v
"""

import os
import pytest
from pathlib import Path

from s4lt.core import Package


# Skip all tests if no test package available
TEST_PACKAGE_PATH = os.environ.get("TEST_PACKAGE_PATH")

pytestmark = pytest.mark.skipif(
    not TEST_PACKAGE_PATH or not Path(TEST_PACKAGE_PATH).exists(),
    reason="TEST_PACKAGE_PATH not set or file doesn't exist"
)


def test_open_real_package():
    """Should open a real .package file."""
    with Package.open(TEST_PACKAGE_PATH) as pkg:
        assert pkg.version[0] == 2
        assert len(pkg.resources) > 0


def test_list_resources():
    """Should list all resources."""
    with Package.open(TEST_PACKAGE_PATH) as pkg:
        for resource in pkg.resources:
            assert resource.type_id > 0
            assert resource.instance_id >= 0


def test_extract_resources():
    """Should extract all resources without error."""
    with Package.open(TEST_PACKAGE_PATH) as pkg:
        for resource in pkg.resources[:10]:  # Test first 10
            data = resource.extract()
            assert len(data) == resource.uncompressed_size
```

**Step 2: Commit**

```bash
git add -A
git commit -m "feat: integration test framework for real packages"
```

---

## Task 11: Final Cleanup and Documentation

**Step 1: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 2: Create top-level __init__.py**

```python
# s4lt/__init__.py
"""S4LT: Sims 4 Linux Toolkit.

A native Linux toolkit for Sims 4 mod management.
"""

from s4lt.core import Package, Resource, DBPFError

__version__ = "0.1.0"

__all__ = [
    "Package",
    "Resource",
    "DBPFError",
    "__version__",
]
```

**Step 3: Update README with usage**

Add to README.md:

```markdown
## Phase 1 Complete: DBPF Core Engine

The core DBPF parser is now functional:

```python
from s4lt import Package

# Open and inspect a package
with Package.open("path/to/mod.package") as pkg:
    print(f"Version: {pkg.version}")
    print(f"Resources: {len(pkg)}")

    for resource in pkg.resources:
        print(f"  {resource.type_name}: {resource.instance_id:016X}")

    # Extract a resource
    data = pkg.resources[0].extract()
```

### CLI Testing

```bash
python -m s4lt.cli.package_info path/to/mod.package
```
```

**Step 4: Final commit**

```bash
git add -A
git commit -m "docs: complete Phase 1 - DBPF core engine ready"
```

---

## Summary

**Files Created:**
- `pyproject.toml` - Project configuration
- `s4lt/__init__.py` - Package entry point
- `s4lt/core/__init__.py` - Core module exports
- `s4lt/core/exceptions.py` - Error classes
- `s4lt/core/types.py` - Resource type registry
- `s4lt/core/header.py` - Header parsing
- `s4lt/core/index.py` - Index parsing
- `s4lt/core/compression.py` - Decompression (zlib + RefPack)
- `s4lt/core/resource.py` - Resource class
- `s4lt/core/package.py` - Main Package API
- `s4lt/cli/__init__.py` - CLI module
- `s4lt/cli/package_info.py` - Test CLI script
- `tests/` - Complete test suite

**Capabilities:**
- Open any Sims 4 .package file
- Parse DBPF 2.x header and index
- Decompress zlib and RefPack resources
- Extract individual resources
- List and filter by type
- Context manager support
- Clean error handling

**Next Phase:** Mod Scanner (uses this engine to crawl Mods folder)
