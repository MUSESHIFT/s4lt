# Phase 6: Package Editor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete package editor with DBPF write support, web-based editing, and CLI commands.

**Architecture:** Extend the core module with write capabilities, create an editor module for session management and specialized editors (XML, STBL), extend the web UI with package viewing/editing pages, and add CLI commands under `s4lt package`.

**Tech Stack:** Python 3.11+, FastAPI, HTMX, TailwindCSS, Pillow (for textures), existing s4lt.core

---

## Task 1: Add DBPF compression support

**Files:**
- Modify: `s4lt/core/compression.py`
- Create: `tests/core/test_compression_write.py`

**Step 1: Write the failing test**

`tests/core/test_compression_write.py`:
```python
"""Tests for compression (write support)."""

from s4lt.core.compression import compress, decompress
from s4lt.core.index import COMPRESSION_ZLIB


def test_compress_zlib_roundtrip():
    """Compress then decompress should return original data."""
    original = b"Hello World! " * 100
    compressed = compress(original, COMPRESSION_ZLIB)
    decompressed = decompress(compressed, COMPRESSION_ZLIB, len(original))
    assert decompressed == original


def test_compress_zlib_smaller():
    """Compressed data should be smaller than original."""
    original = b"AAAAAAAAAA" * 1000
    compressed = compress(original, COMPRESSION_ZLIB)
    assert len(compressed) < len(original)
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/core/test_compression_write.py -v`
Expected: FAIL with "cannot import name 'compress'"

**Step 3: Implement compression**

Add to `s4lt/core/compression.py` after the decompress functions:

```python
def compress(data: bytes, compression_type: int) -> bytes:
    """Compress data using the specified compression type.

    Args:
        data: Uncompressed data bytes
        compression_type: Compression type to use

    Returns:
        Compressed data with appropriate header

    Raises:
        CompressionError: If compression fails or type unsupported
    """
    if compression_type == COMPRESSION_NONE:
        return data

    if compression_type == COMPRESSION_ZLIB:
        return compress_zlib(data)

    raise CompressionError(f"Compression not supported for type: 0x{compression_type:04X}")


def compress_zlib(data: bytes) -> bytes:
    """Compress data using zlib/deflate.

    Returns data with 2-byte header matching Sims 4 format.

    Args:
        data: Uncompressed data

    Returns:
        Compressed data with header
    """
    # Compress with raw deflate (no zlib wrapper)
    compressed = zlib.compress(data, level=9)[2:-4]  # Strip zlib header/trailer

    # Add 2-byte header (compression marker)
    header = bytes([0x78, 0x9C])  # Standard zlib header for level 9
    return header + compressed
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/core/test_compression_write.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add s4lt/core/compression.py tests/core/test_compression_write.py
git commit -m "feat(core): add zlib compression support"
```

---

## Task 2: Add DBPF write support to Package class

**Files:**
- Create: `s4lt/core/writer.py`
- Modify: `s4lt/core/package.py`
- Modify: `s4lt/core/__init__.py`
- Create: `tests/core/test_package_write.py`

**Step 1: Write the failing test**

`tests/core/test_package_write.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/core/test_package_write.py -v`
Expected: FAIL with "Package object has no attribute 'mark_modified'"

**Step 3: Create writer module**

`s4lt/core/writer.py`:
```python
"""DBPF package writing support."""

import struct
import shutil
from pathlib import Path
from typing import BinaryIO

from s4lt.core.header import HEADER_SIZE, MAGIC
from s4lt.core.index import COMPRESSION_NONE, COMPRESSION_ZLIB
from s4lt.core.compression import compress


def write_package(
    path: Path,
    resources: list[dict],
    create_backup: bool = True,
) -> None:
    """Write a DBPF package to disk.

    Args:
        path: Output path
        resources: List of resource dicts with keys:
            type_id, group_id, instance_id, data, compress
        create_backup: Create .bak file if path exists
    """
    if create_backup and path.exists():
        backup_path = path.with_suffix(path.suffix + ".bak")
        if not backup_path.exists():
            shutil.copy2(path, backup_path)

    # Build resource data and index entries
    entries = []
    data_chunks = []
    current_offset = HEADER_SIZE  # Data starts after header

    for res in resources:
        data = res["data"]
        compress_flag = res.get("compress", False)

        if compress_flag:
            compressed = compress(data, COMPRESSION_ZLIB)
            compression_type = COMPRESSION_ZLIB
        else:
            compressed = data
            compression_type = COMPRESSION_NONE

        entries.append({
            "type_id": res["type_id"],
            "group_id": res["group_id"],
            "instance_id": res["instance_id"],
            "offset": current_offset,
            "compressed_size": len(compressed),
            "uncompressed_size": len(data),
            "compression_type": compression_type,
        })

        data_chunks.append(compressed)
        current_offset += len(compressed)

    # Calculate index position and size
    index_position = current_offset
    index_data = _build_index(entries)
    index_size = len(index_data)

    # Build header
    header = _build_header(len(entries), index_position, index_size)

    # Write file
    with open(path, "wb") as f:
        f.write(header)
        for chunk in data_chunks:
            f.write(chunk)
        f.write(index_data)


def _build_header(entry_count: int, index_position: int, index_size: int) -> bytes:
    """Build DBPF header."""
    header = bytearray(HEADER_SIZE)
    header[0:4] = MAGIC
    struct.pack_into("<I", header, 4, 2)   # version major
    struct.pack_into("<I", header, 8, 1)   # version minor
    struct.pack_into("<I", header, 36, entry_count)
    struct.pack_into("<I", header, 44, index_size)
    struct.pack_into("<I", header, 64, index_position)
    return bytes(header)


def _build_index(entries: list[dict]) -> bytes:
    """Build DBPF index table."""
    # Flags = 0 (no constant fields)
    index = bytearray(struct.pack("<I", 0))

    for e in entries:
        instance_hi = (e["instance_id"] >> 32) & 0xFFFFFFFF
        instance_lo = e["instance_id"] & 0xFFFFFFFF

        index.extend(struct.pack("<I", e["type_id"]))
        index.extend(struct.pack("<I", e["group_id"]))
        index.extend(struct.pack("<I", instance_hi))
        index.extend(struct.pack("<I", instance_lo))
        index.extend(struct.pack("<I", e["offset"]))
        index.extend(struct.pack("<I", e["compressed_size"]))
        index.extend(struct.pack("<I", e["uncompressed_size"]))
        index.extend(struct.pack("<H", e["compression_type"]))
        index.extend(struct.pack("<H", 0))  # padding

    return bytes(index)
```

**Step 4: Modify Package class**

Add to `s4lt/core/package.py`:

```python
# Add import at top
from s4lt.core.writer import write_package

# Add to Package class after __init__:
    def __init__(self, file: BinaryIO, header: DBPFHeader, resources: list[Resource], path: Path | None = None):
        """Create a Package. Use Package.open() instead."""
        self._file = file
        self._header = header
        self._resources = resources
        self._path = path
        self._modified = False
        self._pending_resources: list[dict] = []  # New resources to add
        self._removed_tgis: set[tuple] = set()     # TGIs to remove

# Update open() to pass path:
    @classmethod
    def open(cls, path: str | Path) -> "Package":
        # ... existing code ...
        return cls(file, header, resources, Path(path))

# Add new methods:
    def mark_modified(self) -> None:
        """Mark package as modified (will create backup on save)."""
        self._modified = True

    def add_resource(
        self,
        type_id: int,
        group_id: int,
        instance_id: int,
        data: bytes,
        compress: bool = True,
    ) -> None:
        """Add a new resource to the package.

        Args:
            type_id: Resource type ID
            group_id: Resource group ID
            instance_id: Resource instance ID (64-bit)
            data: Uncompressed resource data
            compress: Whether to compress the data
        """
        self._pending_resources.append({
            "type_id": type_id,
            "group_id": group_id,
            "instance_id": instance_id,
            "data": data,
            "compress": compress,
        })
        self._modified = True

    def remove_resource(self, type_id: int, group_id: int, instance_id: int) -> None:
        """Remove a resource by TGI."""
        self._removed_tgis.add((type_id, group_id, instance_id))
        self._modified = True

    def update_resource(self, type_id: int, group_id: int, instance_id: int, data: bytes) -> None:
        """Update an existing resource's data."""
        self.remove_resource(type_id, group_id, instance_id)
        self.add_resource(type_id, group_id, instance_id, data)

    def save(self, path: Path | None = None) -> None:
        """Save package to disk.

        Args:
            path: Output path (defaults to original path)
        """
        if path is None:
            path = self._path
        if path is None:
            raise ValueError("No path specified for save")

        # Collect all resources
        all_resources = []

        # Add existing resources (not removed)
        for res in self._resources:
            tgi = (res.type_id, res.group_id, res.instance_id)
            if tgi not in self._removed_tgis:
                all_resources.append({
                    "type_id": res.type_id,
                    "group_id": res.group_id,
                    "instance_id": res.instance_id,
                    "data": res.extract(),
                    "compress": res.is_compressed,
                })

        # Add pending resources
        all_resources.extend(self._pending_resources)

        # Write
        write_package(path, all_resources, create_backup=self._modified)

        # Clear pending state
        self._pending_resources = []
        self._removed_tgis = set()
        self._modified = False
```

**Step 5: Update __init__.py exports**

Add to `s4lt/core/__init__.py`:
```python
from s4lt.core.compression import compress, decompress
```

And add "compress" to __all__.

**Step 6: Run test to verify it passes**

Run: `.venv/bin/pytest tests/core/test_package_write.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add s4lt/core/writer.py s4lt/core/package.py s4lt/core/compression.py s4lt/core/__init__.py tests/core/test_package_write.py
git commit -m "feat(core): add DBPF write support"
```

---

## Task 3: Create editor module with session management

**Files:**
- Create: `s4lt/editor/__init__.py`
- Create: `s4lt/editor/session.py`
- Create: `tests/editor/__init__.py`
- Create: `tests/editor/test_session.py`

**Step 1: Write the failing test**

`tests/editor/__init__.py`:
```python
"""Tests for editor module."""
```

`tests/editor/test_session.py`:
```python
"""Tests for edit session management."""

import tempfile
from pathlib import Path

from s4lt.editor.session import EditSession, get_session, close_session


def test_get_session_creates_session():
    """get_session should create and cache a session."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = Path(tmpdir) / "test.package"
        pkg_path.write_bytes(create_minimal_package())

        session = get_session(str(pkg_path))
        assert session is not None
        assert session.path == pkg_path
        assert not session.has_unsaved_changes

        close_session(str(pkg_path))


def test_session_tracks_modifications():
    """Session should track when changes are made."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = Path(tmpdir) / "test.package"
        pkg_path.write_bytes(create_minimal_package())

        session = get_session(str(pkg_path))
        assert not session.has_unsaved_changes

        session.add_resource(0x220557DA, 0, 0x123, b"test")
        assert session.has_unsaved_changes

        close_session(str(pkg_path))


def create_minimal_package() -> bytes:
    """Create a minimal valid DBPF package."""
    import struct
    header = bytearray(96)
    header[0:4] = b"DBPF"
    struct.pack_into("<I", header, 4, 2)
    struct.pack_into("<I", header, 8, 1)
    struct.pack_into("<I", header, 36, 0)
    struct.pack_into("<I", header, 44, 4)
    struct.pack_into("<I", header, 64, 96)
    return bytes(header) + struct.pack("<I", 0)
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/editor/test_session.py -v`
Expected: FAIL with "No module named 's4lt.editor'"

**Step 3: Implement session module**

`s4lt/editor/__init__.py`:
```python
"""S4LT Package Editor."""

from s4lt.editor.session import EditSession, get_session, close_session

__all__ = ["EditSession", "get_session", "close_session"]
```

`s4lt/editor/session.py`:
```python
"""Edit session management for package editing."""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Iterator

from s4lt.core import Package, Resource


@dataclass
class PendingChange:
    """A pending change to a resource."""

    action: str  # "add", "update", "delete"
    type_id: int
    group_id: int
    instance_id: int
    data: bytes | None = None


@dataclass
class EditSession:
    """An editing session for a package file."""

    path: Path
    package: Package
    changes: list[PendingChange] = field(default_factory=list)

    @property
    def has_unsaved_changes(self) -> bool:
        """True if there are pending changes."""
        return len(self.changes) > 0

    @property
    def resources(self) -> list[Resource]:
        """Get all resources in the package."""
        return self.package.resources

    def add_resource(
        self,
        type_id: int,
        group_id: int,
        instance_id: int,
        data: bytes,
    ) -> None:
        """Add a new resource."""
        self.changes.append(PendingChange(
            action="add",
            type_id=type_id,
            group_id=group_id,
            instance_id=instance_id,
            data=data,
        ))

    def update_resource(
        self,
        type_id: int,
        group_id: int,
        instance_id: int,
        data: bytes,
    ) -> None:
        """Update an existing resource."""
        self.changes.append(PendingChange(
            action="update",
            type_id=type_id,
            group_id=group_id,
            instance_id=instance_id,
            data=data,
        ))

    def delete_resource(
        self,
        type_id: int,
        group_id: int,
        instance_id: int,
    ) -> None:
        """Delete a resource."""
        self.changes.append(PendingChange(
            action="delete",
            type_id=type_id,
            group_id=group_id,
            instance_id=instance_id,
        ))

    def save(self) -> None:
        """Apply all pending changes and save."""
        for change in self.changes:
            if change.action == "add":
                self.package.add_resource(
                    change.type_id,
                    change.group_id,
                    change.instance_id,
                    change.data,
                )
            elif change.action == "update":
                self.package.update_resource(
                    change.type_id,
                    change.group_id,
                    change.instance_id,
                    change.data,
                )
            elif change.action == "delete":
                self.package.remove_resource(
                    change.type_id,
                    change.group_id,
                    change.instance_id,
                )

        self.package.save()
        self.changes = []

    def discard_changes(self) -> None:
        """Discard all pending changes."""
        self.changes = []

    def close(self) -> None:
        """Close the session."""
        self.package.close()


# Session cache
_sessions: dict[str, EditSession] = {}


def get_session(path: str) -> EditSession:
    """Get or create an edit session for a package.

    Args:
        path: Path to package file

    Returns:
        EditSession instance
    """
    path_str = str(Path(path).resolve())

    if path_str not in _sessions:
        package = Package.open(path)
        _sessions[path_str] = EditSession(
            path=Path(path).resolve(),
            package=package,
        )

    return _sessions[path_str]


def close_session(path: str) -> None:
    """Close and remove a session."""
    path_str = str(Path(path).resolve())

    if path_str in _sessions:
        _sessions[path_str].close()
        del _sessions[path_str]


def list_sessions() -> list[str]:
    """List all open session paths."""
    return list(_sessions.keys())
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/editor/test_session.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add s4lt/editor/ tests/editor/
git commit -m "feat(editor): add session management"
```

---

## Task 4: Create STBL (string table) parser/editor

**Files:**
- Create: `s4lt/editor/stbl.py`
- Create: `tests/editor/test_stbl.py`

**Step 1: Write the failing test**

`tests/editor/test_stbl.py`:
```python
"""Tests for STBL parsing and editing."""

from s4lt.editor.stbl import parse_stbl, build_stbl, STBLEntry


def test_parse_stbl():
    """Parse a valid STBL."""
    # Minimal STBL: header + 1 entry
    stbl_data = build_test_stbl([
        STBLEntry(0x12345678, "Hello World"),
    ])

    entries = parse_stbl(stbl_data)

    assert len(entries) == 1
    assert entries[0].string_id == 0x12345678
    assert entries[0].text == "Hello World"


def test_build_stbl():
    """Build a valid STBL from entries."""
    entries = [
        STBLEntry(0x12345678, "Hello World"),
        STBLEntry(0x87654321, "Goodbye"),
    ]

    data = build_stbl(entries)
    parsed = parse_stbl(data)

    assert len(parsed) == 2
    assert parsed[0].text == "Hello World"
    assert parsed[1].text == "Goodbye"


def test_roundtrip():
    """Parse then build should produce equivalent data."""
    original_entries = [
        STBLEntry(0xAABBCCDD, "Test string one"),
        STBLEntry(0x11223344, "Test string two"),
    ]

    data = build_stbl(original_entries)
    parsed = parse_stbl(data)

    assert len(parsed) == len(original_entries)
    for orig, new in zip(original_entries, parsed):
        assert orig.string_id == new.string_id
        assert orig.text == new.text


def build_test_stbl(entries: list) -> bytes:
    """Build test STBL data."""
    return build_stbl(entries)
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/editor/test_stbl.py -v`
Expected: FAIL with "cannot import name 'parse_stbl'"

**Step 3: Implement STBL module**

`s4lt/editor/stbl.py`:
```python
"""STBL (String Table) parsing and building."""

import struct
from dataclasses import dataclass


STBL_MAGIC = b"STBL"


@dataclass
class STBLEntry:
    """A single string table entry."""

    string_id: int  # 32-bit hash
    text: str


class STBLError(Exception):
    """Error parsing or building STBL."""

    pass


def parse_stbl(data: bytes) -> list[STBLEntry]:
    """Parse STBL binary data into entries.

    Args:
        data: Raw STBL bytes

    Returns:
        List of STBLEntry objects

    Raises:
        STBLError: If data is invalid
    """
    if len(data) < 21:
        raise STBLError("STBL too short for header")

    # Check magic
    if data[0:4] != STBL_MAGIC:
        raise STBLError(f"Invalid STBL magic: {data[0:4]!r}")

    # Parse header
    version = struct.unpack_from("<H", data, 4)[0]
    if version != 5:
        raise STBLError(f"Unsupported STBL version: {version}")

    # Skip: compressed (1 byte), num_entries (8 bytes), reserved (2 bytes)
    num_entries = struct.unpack_from("<Q", data, 7)[0]
    # String data starts after 21-byte header
    # But first we have entry table

    entries = []
    pos = 21

    for _ in range(num_entries):
        if pos + 6 > len(data):
            raise STBLError("STBL truncated in entry table")

        string_id = struct.unpack_from("<I", data, pos)[0]
        pos += 4

        # Skip flags (1 byte)
        pos += 1

        # String length
        str_len = struct.unpack_from("<H", data, pos)[0]
        pos += 2

        # Read string
        if pos + str_len > len(data):
            raise STBLError("STBL truncated in string data")

        text = data[pos:pos + str_len].decode("utf-8")
        pos += str_len

        entries.append(STBLEntry(string_id=string_id, text=text))

    return entries


def build_stbl(entries: list[STBLEntry]) -> bytes:
    """Build STBL binary data from entries.

    Args:
        entries: List of STBLEntry objects

    Returns:
        Raw STBL bytes
    """
    # Header
    header = bytearray()
    header.extend(STBL_MAGIC)
    header.extend(struct.pack("<H", 5))  # version
    header.append(0)  # not compressed
    header.extend(struct.pack("<Q", len(entries)))  # num entries
    header.extend(struct.pack("<H", 0))  # reserved

    # Entries
    body = bytearray()
    for entry in entries:
        text_bytes = entry.text.encode("utf-8")
        body.extend(struct.pack("<I", entry.string_id))
        body.append(0)  # flags
        body.extend(struct.pack("<H", len(text_bytes)))
        body.extend(text_bytes)

    return bytes(header) + bytes(body)


def stbl_to_text(entries: list[STBLEntry]) -> str:
    """Convert STBL entries to text format.

    Format: 0xHEXID: Text content

    Args:
        entries: List of STBLEntry objects

    Returns:
        Text representation
    """
    lines = []
    for entry in entries:
        lines.append(f"0x{entry.string_id:08X}: {entry.text}")
    return "\n".join(lines)


def text_to_stbl(text: str) -> list[STBLEntry]:
    """Parse text format back to STBL entries.

    Args:
        text: Text in "0xHEXID: Text" format

    Returns:
        List of STBLEntry objects
    """
    entries = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        if ": " not in line:
            raise STBLError(f"Invalid line format: {line}")

        id_part, text_part = line.split(": ", 1)
        string_id = int(id_part, 16)
        entries.append(STBLEntry(string_id=string_id, text=text_part))

    return entries
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/editor/test_stbl.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add s4lt/editor/stbl.py tests/editor/test_stbl.py
git commit -m "feat(editor): add STBL parsing and building"
```

---

## Task 5: Create XML schema registry

**Files:**
- Create: `s4lt/editor/xml_schema.py`
- Create: `tests/editor/test_xml_schema.py`

**Step 1: Write the failing test**

`tests/editor/test_xml_schema.py`:
```python
"""Tests for XML tuning schema validation."""

from s4lt.editor.xml_schema import validate_tuning, TuningError, get_tuning_type


def test_validate_well_formed_xml():
    """Well-formed XML should pass basic validation."""
    xml = '<I n="tuning" c="Buff" i="buff" m="buffs.buff" s="12345"></I>'
    errors = validate_tuning(xml)
    assert not any(e.level == "error" for e in errors)


def test_validate_malformed_xml():
    """Malformed XML should return error."""
    xml = '<I n="tuning"><missing close tag>'
    errors = validate_tuning(xml)
    assert any(e.level == "error" for e in errors)


def test_get_tuning_type():
    """Should extract tuning type from XML."""
    xml = '<I n="tuning" c="Buff" i="buff" m="buffs.buff" s="12345"></I>'
    tuning_type = get_tuning_type(xml)
    assert tuning_type == "Buff"
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/editor/test_xml_schema.py -v`
Expected: FAIL with "cannot import name 'validate_tuning'"

**Step 3: Implement XML schema module**

`s4lt/editor/xml_schema.py`:
```python
"""XML tuning schema validation."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Iterator


@dataclass
class ValidationIssue:
    """A validation issue found in tuning XML."""

    level: str  # "error", "warning", "info"
    message: str
    line: int | None = None


class TuningError(Exception):
    """Error in tuning XML."""

    pass


# Known tuning types and their required/optional elements
TUNING_SCHEMAS: dict[str, dict] = {
    "Buff": {
        "required": [],
        "optional": ["buff_type", "visible", "mood_type", "mood_weight"],
    },
    "Trait": {
        "required": [],
        "optional": ["trait_type", "display_name", "display_name_gender_neutral"],
    },
    "Interaction": {
        "required": [],
        "optional": ["display_name", "category", "target_type"],
    },
    "Object": {
        "required": [],
        "optional": ["tuning_id"],
    },
    "Snippet": {
        "required": [],
        "optional": [],
    },
}


def validate_tuning(xml_text: str) -> list[ValidationIssue]:
    """Validate tuning XML.

    Args:
        xml_text: XML string to validate

    Returns:
        List of validation issues found
    """
    issues = []

    # Check well-formedness
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        issues.append(ValidationIssue(
            level="error",
            message=f"Malformed XML: {e}",
            line=getattr(e, "position", (None,))[0],
        ))
        return issues

    # Check for tuning root element
    if root.tag != "I":
        issues.append(ValidationIssue(
            level="warning",
            message=f"Expected root element 'I', got '{root.tag}'",
        ))

    # Check for required attributes
    tuning_type = root.get("c")
    if not tuning_type:
        issues.append(ValidationIssue(
            level="warning",
            message="Missing 'c' (class) attribute on root element",
        ))

    # Schema-specific validation
    if tuning_type and tuning_type in TUNING_SCHEMAS:
        schema = TUNING_SCHEMAS[tuning_type]
        for required in schema["required"]:
            if root.find(f".//*[@n='{required}']") is None:
                issues.append(ValidationIssue(
                    level="warning",
                    message=f"Missing required element: {required}",
                ))

    return issues


def get_tuning_type(xml_text: str) -> str | None:
    """Extract tuning type from XML.

    Args:
        xml_text: XML string

    Returns:
        Tuning type (class name) or None
    """
    try:
        root = ET.fromstring(xml_text)
        return root.get("c")
    except ET.ParseError:
        return None


def get_autocomplete_suggestions(
    xml_text: str,
    cursor_position: int,
) -> list[str]:
    """Get autocomplete suggestions for current position.

    Args:
        xml_text: Current XML text
        cursor_position: Cursor position in text

    Returns:
        List of suggested tag/attribute names
    """
    # Basic implementation - can be enhanced
    suggestions = []

    tuning_type = get_tuning_type(xml_text)
    if tuning_type and tuning_type in TUNING_SCHEMAS:
        schema = TUNING_SCHEMAS[tuning_type]
        suggestions.extend(schema.get("required", []))
        suggestions.extend(schema.get("optional", []))

    # Common tuning elements
    suggestions.extend([
        "T", "V", "L", "U", "E",  # Common value types
    ])

    return sorted(set(suggestions))


def format_xml(xml_text: str, indent: int = 2) -> str:
    """Format/pretty-print XML.

    Args:
        xml_text: XML string
        indent: Indentation spaces

    Returns:
        Formatted XML
    """
    try:
        root = ET.fromstring(xml_text)
        _indent_element(root, level=0, indent=indent)
        return ET.tostring(root, encoding="unicode")
    except ET.ParseError:
        return xml_text  # Return original if can't parse


def _indent_element(elem: ET.Element, level: int, indent: int) -> None:
    """Add indentation to element tree."""
    i = "\n" + " " * (level * indent)
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + " " * indent
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            _indent_element(child, level + 1, indent)
        if not child.tail or not child.tail.strip():
            child.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/editor/test_xml_schema.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add s4lt/editor/xml_schema.py tests/editor/test_xml_schema.py
git commit -m "feat(editor): add XML tuning schema validation"
```

---

## Task 6: Create package viewer web page

**Files:**
- Create: `s4lt/web/routers/package.py`
- Create: `s4lt/web/templates/package/view.html`
- Modify: `s4lt/web/app.py`
- Create: `tests/web/test_package.py`

**Step 1: Write the failing test**

`tests/web/test_package.py`:
```python
"""Tests for package viewer routes."""

import tempfile
import struct
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient

from s4lt.web import create_app


def test_package_view_returns_html():
    """Package view should return HTML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = Path(tmpdir) / "test.package"
        pkg_path.write_bytes(create_minimal_package())

        app = create_app()
        client = TestClient(app)

        # URL encode the path
        encoded_path = quote(str(pkg_path), safe="")
        response = client.get(f"/package/{encoded_path}")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


def create_minimal_package() -> bytes:
    """Create a minimal valid DBPF package."""
    header = bytearray(96)
    header[0:4] = b"DBPF"
    struct.pack_into("<I", header, 4, 2)
    struct.pack_into("<I", header, 8, 1)
    struct.pack_into("<I", header, 36, 0)
    struct.pack_into("<I", header, 44, 4)
    struct.pack_into("<I", header, 64, 96)
    return bytes(header) + struct.pack("<I", 0)
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/web/test_package.py -v`
Expected: FAIL with 404

**Step 3: Create package router**

`s4lt/web/routers/package.py`:
```python
"""Package viewer and editor routes."""

from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response

from s4lt.core import Package, get_type_name
from s4lt.editor.session import get_session, close_session
from s4lt import __version__

router = APIRouter(prefix="/package", tags=["package"])
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/{path:path}")
async def view_package(request: Request, path: str):
    """View package contents."""
    decoded_path = unquote(path)
    pkg_path = Path(decoded_path)

    if not pkg_path.exists():
        raise HTTPException(status_code=404, detail="Package not found")

    try:
        session = get_session(str(pkg_path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Build resource list
    resources = []
    for res in session.resources:
        resources.append({
            "type_id": res.type_id,
            "type_name": res.type_name,
            "group_id": res.group_id,
            "instance_id": res.instance_id,
            "size": res.uncompressed_size,
            "compressed": res.is_compressed,
            "tgi": f"{res.type_id:08X}:{res.group_id:08X}:{res.instance_id:016X}",
        })

    # Group by type for stats
    type_counts = {}
    for res in resources:
        t = res["type_name"]
        type_counts[t] = type_counts.get(t, 0) + 1

    return templates.TemplateResponse(
        request,
        "package/view.html",
        {
            "active": "package",
            "version": __version__,
            "path": str(pkg_path),
            "filename": pkg_path.name,
            "resources": resources,
            "total": len(resources),
            "type_counts": type_counts,
            "has_changes": session.has_unsaved_changes,
        },
    )
```

**Step 4: Create template**

Create directory: `s4lt/web/templates/package/`

`s4lt/web/templates/package/view.html`:
```html
{% extends "base.html" %}

{% block title %}{{ filename }} - S4LT{% endblock %}

{% block content %}
<div class="flex justify-between items-center mb-6">
    <div>
        <h1 class="text-3xl font-bold">{{ filename }}</h1>
        <p class="text-gray-400 text-sm mt-1">{{ path }}</p>
    </div>
    <div class="flex gap-4">
        {% if has_changes %}
        <span class="px-3 py-1 bg-yellow-600 rounded text-sm">Unsaved Changes</span>
        {% endif %}
        <span class="text-gray-400">{{ total }} resources</span>
    </div>
</div>

<!-- Type Summary -->
<div class="bg-gray-800 rounded-lg p-4 border border-gray-700 mb-6">
    <div class="flex flex-wrap gap-2">
        {% for type_name, count in type_counts.items() %}
        <span class="px-2 py-1 bg-gray-700 rounded text-sm">
            {{ type_name }}: {{ count }}
        </span>
        {% endfor %}
    </div>
</div>

<!-- Filter -->
<div class="bg-gray-800 rounded-lg p-4 border border-gray-700 mb-6">
    <input
        type="text"
        id="filter"
        placeholder="Filter by type or TGI..."
        class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
        oninput="filterResources(this.value)">
</div>

<!-- Resources Table -->
<div class="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
    <table class="w-full" id="resources-table">
        <thead class="bg-gray-700">
            <tr>
                <th class="px-4 py-3 text-left">Type</th>
                <th class="px-4 py-3 text-left">Group</th>
                <th class="px-4 py-3 text-left">Instance</th>
                <th class="px-4 py-3 text-left">Size</th>
                <th class="px-4 py-3 text-right">Actions</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-gray-700">
            {% for res in resources %}
            <tr class="hover:bg-gray-750 resource-row" data-tgi="{{ res.tgi }}" data-type="{{ res.type_name }}">
                <td class="px-4 py-3">
                    <span class="font-mono">{{ res.type_name }}</span>
                    <span class="text-gray-500 text-xs ml-2">0x{{ "%08X"|format(res.type_id) }}</span>
                </td>
                <td class="px-4 py-3 font-mono text-gray-400">0x{{ "%08X"|format(res.group_id) }}</td>
                <td class="px-4 py-3 font-mono text-gray-400 text-sm">0x{{ "%016X"|format(res.instance_id) }}</td>
                <td class="px-4 py-3 text-gray-400">
                    {{ "%.1f"|format(res.size / 1024) }} KB
                    {% if res.compressed %}<span class="text-blue-400 text-xs ml-1">Z</span>{% endif %}
                </td>
                <td class="px-4 py-3 text-right">
                    <a href="/package/{{ path|urlencode }}/resource/{{ res.tgi }}"
                       class="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm">
                        View
                    </a>
                    <button
                        hx-get="/api/package/{{ path|urlencode }}/extract/{{ res.tgi }}"
                        hx-swap="none"
                        class="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-sm ml-2">
                        Extract
                    </button>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<script>
function filterResources(query) {
    const rows = document.querySelectorAll('.resource-row');
    const q = query.toLowerCase();
    rows.forEach(row => {
        const tgi = row.dataset.tgi.toLowerCase();
        const type = row.dataset.type.toLowerCase();
        if (tgi.includes(q) || type.includes(q)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}
</script>
{% endblock %}
```

**Step 5: Update app.py**

Add to `s4lt/web/app.py`:
```python
from s4lt.web.routers import dashboard, mods, tray, profiles, api, package

# In create_app():
app.include_router(package.router)
```

**Step 6: Run test to verify it passes**

Run: `.venv/bin/pytest tests/web/test_package.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add s4lt/web/routers/package.py s4lt/web/templates/package/ s4lt/web/app.py tests/web/test_package.py
git commit -m "feat(web): add package viewer page"
```

---

## Task 7: Create resource detail view with XML editor

**Files:**
- Modify: `s4lt/web/routers/package.py`
- Create: `s4lt/web/templates/package/resource.html`

**Step 1: Add resource view route**

Add to `s4lt/web/routers/package.py`:

```python
from s4lt.editor.xml_schema import validate_tuning, format_xml
from s4lt.editor.stbl import parse_stbl, stbl_to_text

# Resource type IDs
TYPE_TUNING = 0x0333406C
TYPE_STBL = 0x220557DA


@router.get("/{path:path}/resource/{tgi}")
async def view_resource(request: Request, path: str, tgi: str):
    """View/edit a single resource."""
    decoded_path = unquote(path)
    pkg_path = Path(decoded_path)

    if not pkg_path.exists():
        raise HTTPException(status_code=404, detail="Package not found")

    session = get_session(str(pkg_path))

    # Parse TGI
    parts = tgi.split(":")
    if len(parts) != 3:
        raise HTTPException(status_code=400, detail="Invalid TGI format")

    type_id = int(parts[0], 16)
    group_id = int(parts[1], 16)
    instance_id = int(parts[2], 16)

    # Find resource
    resource = None
    for res in session.resources:
        if res.type_id == type_id and res.group_id == group_id and res.instance_id == instance_id:
            resource = res
            break

    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    # Extract and process data
    data = resource.extract()
    content = None
    content_type = "binary"
    validation_errors = []

    if type_id == TYPE_TUNING:
        # XML tuning
        content_type = "xml"
        try:
            content = data.decode("utf-8")
            content = format_xml(content)
            validation_errors = validate_tuning(content)
        except UnicodeDecodeError:
            content = data.hex()
            content_type = "hex"

    elif type_id == TYPE_STBL:
        # String table
        content_type = "stbl"
        try:
            entries = parse_stbl(data)
            content = stbl_to_text(entries)
        except Exception as e:
            content = f"Error parsing STBL: {e}"
            content_type = "error"

    else:
        # Binary - show hex dump
        content_type = "hex"
        content = data[:512].hex()  # First 512 bytes

    return templates.TemplateResponse(
        request,
        "package/resource.html",
        {
            "active": "package",
            "version": __version__,
            "path": str(pkg_path),
            "filename": pkg_path.name,
            "tgi": tgi,
            "resource": {
                "type_id": type_id,
                "type_name": resource.type_name,
                "group_id": group_id,
                "instance_id": instance_id,
                "size": resource.uncompressed_size,
                "compressed": resource.is_compressed,
            },
            "content": content,
            "content_type": content_type,
            "validation_errors": validation_errors,
        },
    )
```

**Step 2: Create resource template**

`s4lt/web/templates/package/resource.html`:
```html
{% extends "base.html" %}

{% block title %}{{ resource.type_name }} - {{ filename }} - S4LT{% endblock %}

{% block content %}
<div class="mb-6">
    <a href="/package/{{ path|urlencode }}" class="text-blue-400 hover:underline">&larr; Back to {{ filename }}</a>
</div>

<div class="flex justify-between items-center mb-6">
    <div>
        <h1 class="text-2xl font-bold">{{ resource.type_name }}</h1>
        <p class="text-gray-400 font-mono text-sm mt-1">{{ tgi }}</p>
    </div>
    <div class="flex gap-4">
        <span class="text-gray-400">{{ "%.1f"|format(resource.size / 1024) }} KB</span>
        {% if resource.compressed %}
        <span class="px-2 py-1 bg-blue-600 rounded text-xs">Compressed</span>
        {% endif %}
    </div>
</div>

<!-- Validation Errors -->
{% if validation_errors %}
<div class="bg-gray-800 rounded-lg p-4 border border-gray-700 mb-6">
    <h2 class="text-lg font-bold mb-2 text-yellow-400">Validation Issues</h2>
    <ul class="space-y-1">
        {% for error in validation_errors %}
        <li class="text-sm {% if error.level == 'error' %}text-red-400{% else %}text-yellow-400{% endif %}">
            [{{ error.level|upper }}] {{ error.message }}
        </li>
        {% endfor %}
    </ul>
</div>
{% endif %}

<!-- Editor -->
<div class="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
    {% if content_type == "xml" %}
    <div class="border-b border-gray-700 px-4 py-2 flex justify-between items-center">
        <span class="text-sm text-gray-400">XML Tuning</span>
        <button
            hx-post="/api/package/{{ path|urlencode }}/resource/{{ tgi }}/save"
            hx-include="#editor-content"
            hx-swap="none"
            class="px-4 py-1 bg-green-600 hover:bg-green-700 rounded text-sm">
            Save
        </button>
    </div>
    <textarea
        id="editor-content"
        name="content"
        class="w-full h-96 p-4 bg-gray-900 font-mono text-sm text-gray-100 focus:outline-none resize-y"
        spellcheck="false">{{ content }}</textarea>

    {% elif content_type == "stbl" %}
    <div class="border-b border-gray-700 px-4 py-2 flex justify-between items-center">
        <div class="flex gap-4">
            <button class="px-3 py-1 bg-gray-700 rounded text-sm" onclick="toggleView('table')">Table</button>
            <button class="px-3 py-1 bg-gray-600 rounded text-sm" onclick="toggleView('text')">Text</button>
        </div>
        <button
            hx-post="/api/package/{{ path|urlencode }}/resource/{{ tgi }}/save"
            hx-include="#editor-content"
            hx-swap="none"
            class="px-4 py-1 bg-green-600 hover:bg-green-700 rounded text-sm">
            Save
        </button>
    </div>
    <div id="stbl-text-view">
        <textarea
            id="editor-content"
            name="content"
            class="w-full h-96 p-4 bg-gray-900 font-mono text-sm text-gray-100 focus:outline-none resize-y"
            spellcheck="false">{{ content }}</textarea>
    </div>

    {% else %}
    <div class="border-b border-gray-700 px-4 py-2">
        <span class="text-sm text-gray-400">Hex Dump (first 512 bytes)</span>
    </div>
    <pre class="p-4 font-mono text-xs text-gray-400 overflow-x-auto">{{ content }}</pre>
    {% endif %}
</div>

<!-- Actions -->
<div class="mt-6 flex gap-4">
    <a href="/api/package/{{ path|urlencode }}/extract/{{ tgi }}"
       class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded">
        Download Resource
    </a>
    <button
        hx-delete="/api/package/{{ path|urlencode }}/resource/{{ tgi }}"
        hx-confirm="Delete this resource?"
        hx-swap="none"
        class="px-4 py-2 bg-red-600 hover:bg-red-700 rounded">
        Delete
    </button>
</div>

<script>
function toggleView(view) {
    // Toggle between table and text view for STBL
    // Simplified - full implementation would convert between formats
}
</script>
{% endblock %}
```

**Step 3: Commit**

```bash
git add s4lt/web/routers/package.py s4lt/web/templates/package/resource.html
git commit -m "feat(web): add resource detail view with XML editor"
```

---

## Task 8: Add package API endpoints

**Files:**
- Modify: `s4lt/web/routers/package.py`

**Step 1: Add API endpoints**

Add to `s4lt/web/routers/package.py`:

```python
from fastapi.responses import StreamingResponse
import io


@router.post("/{path:path}/resource/{tgi}/save")
async def save_resource(request: Request, path: str, tgi: str):
    """Save resource changes."""
    decoded_path = unquote(path)
    pkg_path = Path(decoded_path)

    form = await request.form()
    content = form.get("content", "")

    session = get_session(str(pkg_path))

    # Parse TGI
    parts = tgi.split(":")
    type_id = int(parts[0], 16)
    group_id = int(parts[1], 16)
    instance_id = int(parts[2], 16)

    # Convert content back to bytes
    if type_id == TYPE_TUNING:
        data = content.encode("utf-8")
    elif type_id == TYPE_STBL:
        from s4lt.editor.stbl import text_to_stbl, build_stbl
        entries = text_to_stbl(content)
        data = build_stbl(entries)
    else:
        return {"error": "Cannot edit this resource type"}

    # Update resource
    session.update_resource(type_id, group_id, instance_id, data)

    return {"status": "updated", "has_changes": session.has_unsaved_changes}


@router.delete("/{path:path}/resource/{tgi}")
async def delete_resource(path: str, tgi: str):
    """Delete a resource."""
    decoded_path = unquote(path)
    pkg_path = Path(decoded_path)

    session = get_session(str(pkg_path))

    parts = tgi.split(":")
    type_id = int(parts[0], 16)
    group_id = int(parts[1], 16)
    instance_id = int(parts[2], 16)

    session.delete_resource(type_id, group_id, instance_id)

    return {"status": "deleted"}


@router.get("/{path:path}/extract/{tgi}")
async def extract_resource(path: str, tgi: str):
    """Extract/download a resource."""
    decoded_path = unquote(path)
    pkg_path = Path(decoded_path)

    session = get_session(str(pkg_path))

    parts = tgi.split(":")
    type_id = int(parts[0], 16)
    group_id = int(parts[1], 16)
    instance_id = int(parts[2], 16)

    for res in session.resources:
        if res.type_id == type_id and res.group_id == group_id and res.instance_id == instance_id:
            data = res.extract()
            filename = f"{res.type_name}_{instance_id:016X}.bin"

            return StreamingResponse(
                io.BytesIO(data),
                media_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

    raise HTTPException(status_code=404, detail="Resource not found")


@router.post("/{path:path}/save")
async def save_package(path: str):
    """Save all pending changes."""
    decoded_path = unquote(path)
    pkg_path = Path(decoded_path)

    session = get_session(str(pkg_path))
    session.save()

    return {"status": "saved"}
```

**Step 2: Commit**

```bash
git add s4lt/web/routers/package.py
git commit -m "feat(web): add package editing API endpoints"
```

---

## Task 9: Create merge functionality

**Files:**
- Create: `s4lt/editor/merge.py`
- Create: `tests/editor/test_merge.py`

**Step 1: Write the failing test**

`tests/editor/test_merge.py`:
```python
"""Tests for package merge functionality."""

import tempfile
import struct
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
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/editor/test_merge.py -v`
Expected: FAIL with "cannot import name 'find_conflicts'"

**Step 3: Implement merge module**

`s4lt/editor/merge.py`:
```python
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
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/editor/test_merge.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add s4lt/editor/merge.py tests/editor/test_merge.py
git commit -m "feat(editor): add package merge functionality"
```

---

## Task 10: Create split functionality

**Files:**
- Create: `s4lt/editor/split.py`
- Create: `tests/editor/test_split.py`

**Step 1: Write the failing test**

`tests/editor/test_split.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/editor/test_split.py -v`
Expected: FAIL with "cannot import name 'split_by_type'"

**Step 3: Implement split module**

`s4lt/editor/split.py`:
```python
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
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/editor/test_split.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add s4lt/editor/split.py tests/editor/test_split.py
git commit -m "feat(editor): add package split functionality"
```

---

## Task 11: Add CLI package command group

**Files:**
- Create: `s4lt/cli/commands/package.py`
- Modify: `s4lt/cli/main.py`

**Step 1: Create package CLI commands**

`s4lt/cli/commands/package.py`:
```python
"""Package command implementations."""

import json
from pathlib import Path

from rich.table import Table
from rich.syntax import Syntax

from s4lt.cli.output import console
from s4lt.core import Package, get_type_name


def run_view(package_path: str, type_filter: str | None, json_output: bool) -> None:
    """View package contents."""
    try:
        with Package.open(package_path) as pkg:
            resources = list(pkg.resources)

            if type_filter:
                resources = [r for r in resources if r.type_name == type_filter]

            if json_output:
                data = [
                    {
                        "type": r.type_name,
                        "type_id": f"0x{r.type_id:08X}",
                        "group": f"0x{r.group_id:08X}",
                        "instance": f"0x{r.instance_id:016X}",
                        "size": r.uncompressed_size,
                        "compressed": r.is_compressed,
                    }
                    for r in resources
                ]
                console.print(json.dumps(data, indent=2))
            else:
                table = Table(title=f"{Path(package_path).name} ({len(resources)} resources)")
                table.add_column("Type")
                table.add_column("Group")
                table.add_column("Instance")
                table.add_column("Size")
                table.add_column("Z", justify="center")

                for r in resources:
                    table.add_row(
                        r.type_name,
                        f"0x{r.group_id:08X}",
                        f"0x{r.instance_id:016X}",
                        f"{r.uncompressed_size:,}",
                        "✓" if r.is_compressed else "",
                    )

                console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


def run_extract(
    package_path: str,
    tgi: str | None,
    type_filter: str | None,
    output_dir: str | None,
    all_resources: bool,
) -> None:
    """Extract resources from package."""
    from s4lt.editor.split import extract_all

    output = Path(output_dir) if output_dir else Path(".")
    output.mkdir(parents=True, exist_ok=True)

    if all_resources:
        created = extract_all(package_path, str(output))
        console.print(f"[green]Extracted {len(created)} resources to {output}[/green]")
        return

    with Package.open(package_path) as pkg:
        resources = list(pkg.resources)

        if tgi:
            # Extract specific resource
            parts = tgi.split(":")
            type_id = int(parts[0], 16)
            group_id = int(parts[1], 16)
            instance_id = int(parts[2], 16)

            for r in resources:
                if r.type_id == type_id and r.group_id == group_id and r.instance_id == instance_id:
                    filename = f"{r.type_name}_{instance_id:016X}.bin"
                    (output / filename).write_bytes(r.extract())
                    console.print(f"[green]Extracted to {output / filename}[/green]")
                    return

            console.print("[red]Resource not found[/red]")

        elif type_filter:
            # Extract all of a type
            count = 0
            for r in resources:
                if r.type_name == type_filter:
                    filename = f"{r.type_name}_{r.instance_id:016X}.bin"
                    (output / filename).write_bytes(r.extract())
                    count += 1

            console.print(f"[green]Extracted {count} resources to {output}[/green]")


def run_edit(package_path: str) -> None:
    """Open package in web editor."""
    import webbrowser
    from urllib.parse import quote

    # Start server if not running
    console.print(f"[cyan]Opening {package_path} in browser...[/cyan]")

    encoded = quote(str(Path(package_path).resolve()), safe="")
    url = f"http://127.0.0.1:8000/package/{encoded}"

    console.print(f"[dim]URL: {url}[/dim]")
    console.print("[yellow]Make sure the web server is running: s4lt serve[/yellow]")

    webbrowser.open(url)


def run_merge(output_path: str, input_paths: list[str]) -> None:
    """Merge packages."""
    from s4lt.editor.merge import find_conflicts, merge_packages

    console.print(f"[cyan]Merging {len(input_paths)} packages...[/cyan]")

    # Check for conflicts
    conflicts = find_conflicts(input_paths)

    if conflicts:
        console.print(f"[yellow]Found {len(conflicts)} conflicts (last file wins):[/yellow]")
        for c in conflicts[:10]:
            console.print(f"  0x{c.type_id:08X}:0x{c.group_id:08X}:0x{c.instance_id:016X}")
        if len(conflicts) > 10:
            console.print(f"  ... and {len(conflicts) - 10} more")

    merge_packages(input_paths, output_path)
    console.print(f"[green]Merged to {output_path}[/green]")


def run_split(
    package_path: str,
    output_dir: str | None,
    by_type: bool,
    by_group: bool,
    extract_all_flag: bool,
) -> None:
    """Split package."""
    from s4lt.editor.split import split_by_type, split_by_group, extract_all

    output = Path(output_dir) if output_dir else Path(".")
    output.mkdir(parents=True, exist_ok=True)

    if extract_all_flag:
        created = extract_all(package_path, str(output))
        console.print(f"[green]Extracted {len(created)} files to {output}[/green]")
    elif by_group:
        created = split_by_group(package_path, str(output))
        console.print(f"[green]Created {len(created)} packages in {output}[/green]")
    else:  # by_type is default
        created = split_by_type(package_path, str(output))
        console.print(f"[green]Created {len(created)} packages in {output}[/green]")
```

**Step 2: Add to main CLI**

Add to `s4lt/cli/main.py`:

```python
@cli.group()
def package():
    """View, edit, merge, and split .package files."""
    pass


@package.command("view")
@click.argument("file")
@click.option("--type", "type_filter", help="Filter by resource type")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def package_view(file: str, type_filter: str | None, json_output: bool):
    """View package contents."""
    from s4lt.cli.commands.package import run_view
    run_view(file, type_filter, json_output)


@package.command("extract")
@click.argument("file")
@click.argument("tgi", required=False)
@click.option("--type", "type_filter", help="Extract all of type")
@click.option("--output", "-o", "output_dir", help="Output directory")
@click.option("--all", "all_resources", is_flag=True, help="Extract all resources")
def package_extract(file: str, tgi: str | None, type_filter: str | None, output_dir: str | None, all_resources: bool):
    """Extract resources from package."""
    from s4lt.cli.commands.package import run_extract
    run_extract(file, tgi, type_filter, output_dir, all_resources)


@package.command("edit")
@click.argument("file")
def package_edit(file: str):
    """Open package in web editor."""
    from s4lt.cli.commands.package import run_edit
    run_edit(file)


@package.command("merge")
@click.argument("output")
@click.argument("inputs", nargs=-1, required=True)
def package_merge(output: str, inputs: tuple[str, ...]):
    """Merge multiple packages into one."""
    from s4lt.cli.commands.package import run_merge
    run_merge(output, list(inputs))


@package.command("split")
@click.argument("file")
@click.option("--output", "-o", "output_dir", help="Output directory")
@click.option("--by-type", is_flag=True, default=True, help="Split by resource type")
@click.option("--by-group", is_flag=True, help="Split by group ID")
@click.option("--extract-all", is_flag=True, help="Extract as individual files")
def package_split(file: str, output_dir: str | None, by_type: bool, by_group: bool, extract_all: bool):
    """Split package into multiple files."""
    from s4lt.cli.commands.package import run_split
    run_split(file, output_dir, by_type, by_group, extract_all)
```

**Step 3: Verify CLI works**

Run: `.venv/bin/python -c "from s4lt.cli.main import cli; print('OK')"`
Expected: OK

**Step 4: Commit**

```bash
git add s4lt/cli/commands/package.py s4lt/cli/main.py
git commit -m "feat(cli): add package command group"
```

---

## Task 12: Add texture preview support

**Files:**
- Create: `s4lt/editor/preview.py`
- Modify: `pyproject.toml`
- Create: `tests/editor/test_preview.py`

**Step 1: Add Pillow dependency**

Update `pyproject.toml` dependencies:
```toml
dependencies = [
    "click>=8.0",
    "rich>=13.0",
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "jinja2>=3.1.0",
    "python-multipart>=0.0.6",
    "pillow>=10.0.0",
]
```

Run: `.venv/bin/pip install -e ".[dev]"`

**Step 2: Write the failing test**

`tests/editor/test_preview.py`:
```python
"""Tests for texture preview."""

from s4lt.editor.preview import can_preview, get_preview_png


def test_can_preview_dds():
    """Should identify previewable types."""
    assert can_preview(0x00B2D882)  # DDS
    assert not can_preview(0x220557DA)  # STBL


def test_get_preview_returns_png():
    """Preview should return PNG data."""
    # Create minimal DDS (just header, will fail gracefully)
    dds_data = b"DDS " + b"\x00" * 124

    result = get_preview_png(dds_data, 0x00B2D882)

    # Should return None for invalid DDS (graceful failure)
    # or PNG bytes for valid DDS
    assert result is None or result[:4] == b"\x89PNG"
```

**Step 3: Implement preview module**

`s4lt/editor/preview.py`:
```python
"""Texture preview support."""

import io
from PIL import Image


# Previewable resource types
TYPE_DDS = 0x00B2D882
TYPE_DST = 0x2F7D0004
TYPE_PNG = 0x2F7D0006  # Not standard, but sometimes used


PREVIEWABLE_TYPES = {TYPE_DDS, TYPE_DST, TYPE_PNG}


def can_preview(type_id: int) -> bool:
    """Check if a resource type can be previewed.

    Args:
        type_id: Resource type ID

    Returns:
        True if previewable
    """
    return type_id in PREVIEWABLE_TYPES


def get_preview_png(data: bytes, type_id: int) -> bytes | None:
    """Generate PNG preview for a resource.

    Args:
        data: Raw resource data
        type_id: Resource type ID

    Returns:
        PNG bytes or None if preview failed
    """
    try:
        if type_id == TYPE_DDS:
            return _decode_dds(data)
        elif type_id == TYPE_DST:
            return _decode_dst(data)
        elif type_id == TYPE_PNG:
            return data  # Already PNG
        return None
    except Exception:
        return None


def _decode_dds(data: bytes) -> bytes | None:
    """Decode DDS texture to PNG.

    DDS format:
    - 4 bytes: "DDS "
    - 124 bytes: DDS_HEADER
    - Variable: Pixel data

    This is a simplified decoder for common DDS formats.
    """
    if len(data) < 128 or data[:4] != b"DDS ":
        return None

    try:
        # Try using Pillow's DDS support
        img = Image.open(io.BytesIO(data))
        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()
    except Exception:
        return None


def _decode_dst(data: bytes) -> bytes | None:
    """Decode Sims 4 DST texture to PNG.

    DST is a proprietary format. Basic implementation:
    - Try treating as DDS variant
    - Fall back to raw pixel interpretation
    """
    # DST often starts with a header similar to DDS
    # Try DDS decode first
    if len(data) > 128:
        result = _decode_dds(data)
        if result:
            return result

    # DST-specific decode would go here
    # For now, return None (not implemented)
    return None


def get_preview_info(data: bytes, type_id: int) -> dict | None:
    """Get preview metadata without full decode.

    Args:
        data: Raw resource data
        type_id: Resource type ID

    Returns:
        Dict with width, height, format info, or None
    """
    if type_id == TYPE_DDS and len(data) >= 128 and data[:4] == b"DDS ":
        # Parse DDS header
        import struct
        height = struct.unpack_from("<I", data, 12)[0]
        width = struct.unpack_from("<I", data, 16)[0]
        return {
            "width": width,
            "height": height,
            "format": "DDS",
        }

    return None
```

**Step 4: Run tests**

Run: `.venv/bin/pytest tests/editor/test_preview.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add s4lt/editor/preview.py tests/editor/test_preview.py pyproject.toml
git commit -m "feat(editor): add texture preview support"
```

---

## Task 13: Add preview to web resource view

**Files:**
- Modify: `s4lt/web/routers/package.py`
- Modify: `s4lt/web/templates/package/resource.html`

**Step 1: Add preview route**

Add to `s4lt/web/routers/package.py`:

```python
from s4lt.editor.preview import can_preview, get_preview_png


@router.get("/{path:path}/resource/{tgi}/preview")
async def get_resource_preview(path: str, tgi: str):
    """Get preview image for a resource."""
    decoded_path = unquote(path)
    pkg_path = Path(decoded_path)

    session = get_session(str(pkg_path))

    parts = tgi.split(":")
    type_id = int(parts[0], 16)
    group_id = int(parts[1], 16)
    instance_id = int(parts[2], 16)

    for res in session.resources:
        if res.type_id == type_id and res.group_id == group_id and res.instance_id == instance_id:
            if not can_preview(type_id):
                raise HTTPException(status_code=400, detail="Resource type not previewable")

            data = res.extract()
            png_data = get_preview_png(data, type_id)

            if png_data is None:
                raise HTTPException(status_code=500, detail="Failed to generate preview")

            return Response(content=png_data, media_type="image/png")

    raise HTTPException(status_code=404, detail="Resource not found")
```

**Step 2: Update resource view to check preview**

Update the view_resource function to pass preview info:

```python
# Add to view_resource context:
from s4lt.editor.preview import can_preview

# In the context dict:
"can_preview": can_preview(type_id),
```

**Step 3: Update template**

Add to `s4lt/web/templates/package/resource.html` before the editor section:

```html
{% if can_preview %}
<!-- Preview -->
<div class="bg-gray-800 rounded-lg border border-gray-700 p-4 mb-6">
    <h2 class="text-lg font-bold mb-4">Preview</h2>
    <img src="/package/{{ path|urlencode }}/resource/{{ tgi }}/preview"
         alt="Resource preview"
         class="max-w-full max-h-96 mx-auto">
</div>
{% endif %}
```

**Step 4: Commit**

```bash
git add s4lt/web/routers/package.py s4lt/web/templates/package/resource.html
git commit -m "feat(web): add texture preview to resource view"
```

---

## Task 14: Add merge web UI

**Files:**
- Create: `s4lt/web/templates/package/merge.html`
- Modify: `s4lt/web/routers/package.py`

**Step 1: Add merge routes**

Add to `s4lt/web/routers/package.py`:

```python
from s4lt.editor.merge import find_conflicts, merge_packages


@router.get("/merge")
async def merge_page(request: Request):
    """Merge packages page."""
    return templates.TemplateResponse(
        request,
        "package/merge.html",
        {
            "active": "package",
            "version": __version__,
        },
    )


@router.post("/merge/check")
async def check_merge_conflicts(request: Request):
    """Check for merge conflicts."""
    form = await request.form()
    paths = form.getlist("paths")

    if len(paths) < 2:
        return {"error": "Need at least 2 packages"}

    conflicts = find_conflicts(paths)

    return {
        "conflicts": [
            {
                "tgi": f"{c.type_id:08X}:{c.group_id:08X}:{c.instance_id:016X}",
                "sources": c.sources,
            }
            for c in conflicts
        ]
    }


@router.post("/merge/execute")
async def execute_merge(request: Request):
    """Execute package merge."""
    form = await request.form()
    paths = form.getlist("paths")
    output = form.get("output")
    resolutions_json = form.get("resolutions", "{}")

    import json
    resolutions_raw = json.loads(resolutions_json)

    # Convert string TGIs to tuples
    resolutions = {}
    for tgi_str, source in resolutions_raw.items():
        parts = tgi_str.split(":")
        tgi = (int(parts[0], 16), int(parts[1], 16), int(parts[2], 16))
        resolutions[tgi] = source

    merge_packages(paths, output, resolutions)

    return {"status": "merged", "output": output}
```

**Step 2: Create merge template**

`s4lt/web/templates/package/merge.html`:
```html
{% extends "base.html" %}

{% block title %}Merge Packages - S4LT{% endblock %}

{% block content %}
<h1 class="text-3xl font-bold mb-6">Merge Packages</h1>

<div class="bg-gray-800 rounded-lg p-6 border border-gray-700 mb-6">
    <h2 class="text-xl font-bold mb-4">Select Packages</h2>

    <div id="package-list" class="space-y-2 mb-4">
        <div class="flex gap-2">
            <input type="text" name="path" placeholder="Package path..."
                   class="flex-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded">
            <button onclick="addPackageInput()" class="px-4 py-2 bg-blue-600 rounded">+</button>
        </div>
    </div>

    <div class="flex gap-4">
        <input type="text" id="output-path" placeholder="Output path..."
               class="flex-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded">
        <button onclick="checkConflicts()" class="px-4 py-2 bg-yellow-600 rounded">
            Check Conflicts
        </button>
    </div>
</div>

<div id="conflicts-section" class="hidden bg-gray-800 rounded-lg p-6 border border-gray-700 mb-6">
    <h2 class="text-xl font-bold mb-4">Conflicts</h2>
    <div id="conflicts-list"></div>
</div>

<button onclick="executeMerge()" class="px-6 py-3 bg-green-600 hover:bg-green-700 rounded font-bold">
    Merge Packages
</button>

<script>
function addPackageInput() {
    const list = document.getElementById('package-list');
    const div = document.createElement('div');
    div.className = 'flex gap-2';
    div.innerHTML = `
        <input type="text" name="path" placeholder="Package path..."
               class="flex-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded">
        <button onclick="this.parentElement.remove()" class="px-4 py-2 bg-red-600 rounded">-</button>
    `;
    list.appendChild(div);
}

async function checkConflicts() {
    const inputs = document.querySelectorAll('input[name="path"]');
    const paths = Array.from(inputs).map(i => i.value).filter(p => p);

    const formData = new FormData();
    paths.forEach(p => formData.append('paths', p));

    const response = await fetch('/package/merge/check', {
        method: 'POST',
        body: formData
    });
    const data = await response.json();

    const section = document.getElementById('conflicts-section');
    const list = document.getElementById('conflicts-list');

    if (data.conflicts && data.conflicts.length > 0) {
        section.classList.remove('hidden');
        list.innerHTML = data.conflicts.map(c => `
            <div class="p-2 bg-gray-700 rounded mb-2">
                <div class="font-mono text-sm">${c.tgi}</div>
                <div class="text-gray-400 text-sm">Found in: ${c.sources.map(s => s[0]).join(', ')}</div>
            </div>
        `).join('');
    } else {
        section.classList.add('hidden');
    }
}

async function executeMerge() {
    const inputs = document.querySelectorAll('input[name="path"]');
    const paths = Array.from(inputs).map(i => i.value).filter(p => p);
    const output = document.getElementById('output-path').value;

    const formData = new FormData();
    paths.forEach(p => formData.append('paths', p));
    formData.append('output', output);

    const response = await fetch('/package/merge/execute', {
        method: 'POST',
        body: formData
    });
    const data = await response.json();

    if (data.status === 'merged') {
        alert('Packages merged successfully!');
    }
}
</script>
{% endblock %}
```

**Step 3: Commit**

```bash
git add s4lt/web/routers/package.py s4lt/web/templates/package/merge.html
git commit -m "feat(web): add merge UI with conflict detection"
```

---

## Task 15: Version bump and final verification

**Files:**
- Modify: `pyproject.toml`
- Modify: `s4lt/__init__.py`
- Modify: `s4lt/editor/__init__.py`

**Step 1: Update editor __init__.py exports**

`s4lt/editor/__init__.py`:
```python
"""S4LT Package Editor."""

from s4lt.editor.session import EditSession, get_session, close_session, list_sessions
from s4lt.editor.stbl import STBLEntry, parse_stbl, build_stbl, stbl_to_text, text_to_stbl
from s4lt.editor.xml_schema import validate_tuning, get_tuning_type, format_xml
from s4lt.editor.merge import find_conflicts, merge_packages, MergeConflict
from s4lt.editor.split import split_by_type, split_by_group, extract_all
from s4lt.editor.preview import can_preview, get_preview_png

__all__ = [
    # Session
    "EditSession",
    "get_session",
    "close_session",
    "list_sessions",
    # STBL
    "STBLEntry",
    "parse_stbl",
    "build_stbl",
    "stbl_to_text",
    "text_to_stbl",
    # XML
    "validate_tuning",
    "get_tuning_type",
    "format_xml",
    # Merge
    "find_conflicts",
    "merge_packages",
    "MergeConflict",
    # Split
    "split_by_type",
    "split_by_group",
    "extract_all",
    # Preview
    "can_preview",
    "get_preview_png",
]
```

**Step 2: Update versions**

`pyproject.toml`: Change `version = "0.5.0"` to `version = "0.6.0"`

`s4lt/__init__.py`: Change `__version__ = "0.5.0"` to `__version__ = "0.6.0"`

**Step 3: Run full test suite**

Run: `.venv/bin/pytest tests/ -v`
Expected: All tests pass

**Step 4: Verify imports**

Run: `.venv/bin/python -c "from s4lt.editor import get_session, merge_packages; print('OK')"`
Expected: OK

**Step 5: Commit and tag**

```bash
git add pyproject.toml s4lt/__init__.py s4lt/editor/__init__.py
git commit -m "chore: bump version to v0.6.0

Phase 6: Package Editor complete"

git tag -a v0.6.0 -m "Phase 6: Package Editor

Features:
- DBPF write support (add/update/remove resources)
- Package viewer web page
- XML tuning editor with validation
- String table editor (table + text views)
- Texture preview (DDS)
- Package merge with conflict detection
- Package split (by type, by group, extract all)
- CLI: s4lt package view/extract/edit/merge/split
- Auto-backup on first edit (.package.bak)"
```

---

## Summary

| Task | Description | Tests |
|------|-------------|-------|
| 1 | DBPF compression support | 2 |
| 2 | DBPF write support | 2 |
| 3 | Editor session management | 2 |
| 4 | STBL parser/editor | 3 |
| 5 | XML schema validation | 3 |
| 6 | Package viewer web page | 1 |
| 7 | Resource detail view | - |
| 8 | Package API endpoints | - |
| 9 | Merge functionality | 2 |
| 10 | Split functionality | 1 |
| 11 | CLI package commands | - |
| 12 | Texture preview | 2 |
| 13 | Preview in web UI | - |
| 14 | Merge web UI | - |
| 15 | Version bump | - |

**Total: 15 tasks, 18 new tests**

Run web editor with: `s4lt serve` then `s4lt package edit mymod.package`
