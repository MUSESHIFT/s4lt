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
