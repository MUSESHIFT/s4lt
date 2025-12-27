"""Tests for mod indexer."""

import struct
import tempfile
import hashlib
from pathlib import Path

from s4lt.mods.indexer import index_package, compute_hash, extract_tuning_name
from s4lt.db.schema import init_db, get_connection
from s4lt.db.operations import get_mod_by_path


def create_test_package(resources: list[tuple[int, bytes]] = None) -> bytes:
    """Create a minimal valid DBPF package."""
    if resources is None:
        resources = []

    resource_data = b""
    entries = []

    for type_id, data in resources:
        entries.append({
            "type_id": type_id,
            "group_id": 0,
            "instance_hi": 0,
            "instance_lo": len(entries),
            "offset": 0,
            "file_size": len(data),
            "mem_size": len(data),
            "compressed": 0x0000,
        })
        resource_data += data

    index_size = 4 + (32 * len(entries))
    resource_start = 96
    index_start = resource_start + len(resource_data)

    offset = resource_start
    for entry in entries:
        entry["offset"] = offset
        offset += entry["file_size"]

    header = bytearray(96)
    header[0:4] = b"DBPF"
    struct.pack_into("<I", header, 4, 2)
    struct.pack_into("<I", header, 8, 1)
    struct.pack_into("<I", header, 36, len(entries))
    struct.pack_into("<I", header, 44, index_size)
    struct.pack_into("<I", header, 64, index_start)

    index = bytearray()
    index.extend(struct.pack("<I", 0))

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


def test_compute_hash():
    """compute_hash should return SHA256."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test content")
        path = Path(f.name)

    try:
        result = compute_hash(path)
        expected = hashlib.sha256(b"test content").hexdigest()
        assert result == expected
    finally:
        path.unlink()


def test_extract_tuning_name_from_n_attribute():
    """extract_tuning_name should get n attribute."""
    xml = b'<?xml version="1.0"?>\n<I n="coolhair_CASPart" c="CASPart"></I>'
    result = extract_tuning_name(xml)
    assert result == "coolhair_CASPart"


def test_extract_tuning_name_returns_none_for_non_xml():
    """extract_tuning_name should return None for non-XML."""
    result = extract_tuning_name(b"not xml data")
    assert result is None


def test_index_package_adds_to_db():
    """index_package should add mod and resources to DB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        mods_path = Path(tmpdir) / "Mods"
        mods_path.mkdir()

        pkg_data = create_test_package([
            (0x0333406C, b'<?xml version="1.0"?>\n<I n="test_tuning"></I>'),
            (0x034AEECB, b"caspart data"),
        ])
        pkg_path = mods_path / "test.package"
        pkg_path.write_bytes(pkg_data)

        index_package(conn, mods_path, pkg_path)

        mod = get_mod_by_path(conn, "test.package")
        assert mod is not None
        assert mod["resource_count"] == 2

        cursor = conn.execute("SELECT * FROM resources WHERE mod_id = ?", (mod["id"],))
        resources = cursor.fetchall()
        assert len(resources) == 2
        conn.close()
