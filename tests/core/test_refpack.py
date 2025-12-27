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
