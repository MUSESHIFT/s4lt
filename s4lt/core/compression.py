"""Decompression routines for DBPF resources."""

import zlib
from s4lt.core.exceptions import CompressionError
from s4lt.core.index import (
    COMPRESSION_NONE,
    COMPRESSION_ZLIB,
    COMPRESSION_REFPACK,
    COMPRESSION_REFPACK_ALT,
)


def decompress(data: bytes, compression_type: int, expected_size: int = 0) -> bytes:
    """Decompress resource data based on compression type.

    Args:
        data: Compressed data bytes
        compression_type: Compression type from index entry
        expected_size: Expected uncompressed size (for validation)

    Returns:
        Decompressed data

    Raises:
        CompressionError: If decompression fails
    """
    if compression_type == COMPRESSION_NONE:
        return data

    if compression_type == COMPRESSION_ZLIB:
        return decompress_zlib(data, expected_size)

    if compression_type in (COMPRESSION_REFPACK, COMPRESSION_REFPACK_ALT):
        return decompress_refpack(data, expected_size)

    raise CompressionError(f"Unknown compression type: 0x{compression_type:04X}")


def decompress_zlib(data: bytes, expected_size: int = 0) -> bytes:
    """Decompress zlib/deflate compressed data.

    Sims 4 uses raw deflate with a 2-byte header.

    Args:
        data: Compressed data with 2-byte header
        expected_size: Expected output size

    Returns:
        Decompressed data
    """
    if len(data) < 2:
        raise CompressionError("zlib data too short")

    try:
        # Skip 2-byte header, decompress raw deflate
        result = zlib.decompress(data[2:], -zlib.MAX_WBITS)

        if expected_size > 0 and len(result) != expected_size:
            raise CompressionError(
                f"Size mismatch: got {len(result)}, expected {expected_size}"
            )

        return result

    except zlib.error as e:
        raise CompressionError(f"zlib decompression failed: {e}")


def decompress_refpack(data: bytes, expected_size: int = 0) -> bytes:
    """Decompress RefPack (EA proprietary) compressed data.

    RefPack is an LZ77 variant used by EA games.

    Args:
        data: Compressed data
        expected_size: Expected output size

    Returns:
        Decompressed data
    """
    # TODO: Implement RefPack decompression
    # For now, raise a clear error
    raise CompressionError(
        "RefPack decompression not yet implemented. "
        "This resource uses EA's proprietary compression."
    )
