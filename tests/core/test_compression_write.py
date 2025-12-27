"""Tests for compression (write support)."""

from s4lt.core.compression import compress, decompress
from s4lt.core.index import COMPRESSION_ZLIB


def test_compress_zlib_roundtrip():
    """Compress then decompress should return original data."""
    original = b"Hello World! " * 100
    compressed = compress(original, COMPRESSION_ZLIB)
    decompressed = decompress(compressed, COMPRESSION_ZLIB, len(original))
    assert decompressed == original


def test_compress_zlib_smaller():
    """Compressed data should be smaller than original."""
    original = b"AAAAAAAAAA" * 1000
    compressed = compress(original, COMPRESSION_ZLIB)
    assert len(compressed) < len(original)
