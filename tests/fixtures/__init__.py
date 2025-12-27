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
