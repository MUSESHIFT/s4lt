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
    if len(data) < 17:
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
    # String data starts after 17-byte header
    # Header: magic(4) + version(2) + compressed(1) + num_entries(8) + reserved(2) = 17

    entries = []
    pos = 17

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
        try:
            string_id = int(id_part, 16)
        except ValueError:
            raise STBLError(f"Invalid hex ID: {id_part}")
        entries.append(STBLEntry(string_id=string_id, text=text_part))

    return entries
