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
