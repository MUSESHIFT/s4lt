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
