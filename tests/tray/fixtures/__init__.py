"""Test fixtures for tray parsing."""

import struct
from pathlib import Path


def create_trayitem_v14(name: str = "Test Item", item_type: int = 1) -> bytes:
    """Create a minimal .trayitem file for testing.

    Based on observed trayitem structure:
    - Magic: varies by version
    - Version: uint32
    - Name: length-prefixed UTF-16 string
    - Type flag
    - Various metadata

    This is a simplified mock for testing.
    """
    data = bytearray()

    # Version (v14 is common in recent Sims 4)
    data.extend(struct.pack("<I", 14))

    # Name as length-prefixed UTF-16LE
    name_bytes = name.encode("utf-16-le")
    data.extend(struct.pack("<I", len(name_bytes) // 2))  # Char count
    data.extend(name_bytes)

    # Item type (1=household, 2=lot, 3=room)
    data.extend(struct.pack("<I", item_type))

    # Padding/unknown fields
    data.extend(b"\x00" * 64)

    return bytes(data)
