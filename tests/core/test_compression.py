"""Tests for decompression routines."""

import zlib
import pytest

from s4lt.core.compression import decompress, decompress_zlib
from s4lt.core.exceptions import CompressionError
from s4lt.core.index import COMPRESSION_NONE, COMPRESSION_ZLIB, COMPRESSION_REFPACK


def test_decompress_none_returns_unchanged():
    """Uncompressed data should pass through unchanged."""
    data = b"Hello, Sims 4!"
    result = decompress(data, COMPRESSION_NONE)
    assert result == data


def test_decompress_zlib_works():
    """zlib compressed data should decompress correctly."""
    original = b"Hello, Sims 4! " * 100  # Repetitive for good compression

    # Create zlib compressed data with 2-byte header
    # Sims 4 uses raw deflate, not zlib wrapper
    # So we need: 2-byte header + raw deflate
    raw_deflate = zlib.compress(original, level=9)[2:-4]  # Strip zlib header/trailer
    compressed = b"\x10\xFB" + raw_deflate  # Common Sims 4 header

    result = decompress_zlib(b"\x10\xFB" + raw_deflate, len(original))
    assert result == original


def test_decompress_zlib_via_dispatcher():
    """decompress() should route to zlib handler."""
    original = b"Test data for compression"
    raw_deflate = zlib.compress(original, level=9)[2:-4]
    compressed = b"\x10\xFB" + raw_deflate

    result = decompress(compressed, COMPRESSION_ZLIB, len(original))
    assert result == original


def test_decompress_invalid_zlib_raises():
    """Invalid zlib data should raise CompressionError."""
    with pytest.raises(CompressionError):
        decompress(b"\x10\xFB\x00\x00\x00", COMPRESSION_ZLIB, 100)
