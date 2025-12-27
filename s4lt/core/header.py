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
