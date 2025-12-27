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

    RefPack is an LZ77 variant used by EA games including Sims 4.

    Format:
    - 2-byte header (0x10 0xFB for compressed)
    - 3-byte big-endian uncompressed size
    - Command stream

    Commands:
    - 0x00-0x7F: Literal + short backref
    - 0x80-0xBF: Short backref (offset < 1024, len 3-10)
    - 0xC0-0xDF: Medium backref (offset < 16384, len 4-67)
    - 0xE0-0xFB: Literal run (1-28 bytes)
    - 0xFC-0xFF: Stop codes

    Args:
        data: Compressed data with RefPack header
        expected_size: Expected output size

    Returns:
        Decompressed data
    """
    if len(data) < 5:
        raise CompressionError("RefPack data too short for header")

    # Check header
    if data[0] != 0x10 or data[1] != 0xFB:
        raise CompressionError(f"Invalid RefPack header: {data[0]:02X} {data[1]:02X}")

    # Read uncompressed size (3 bytes, big-endian)
    uncompressed_size = (data[2] << 16) | (data[3] << 8) | data[4]

    if expected_size > 0 and uncompressed_size != expected_size:
        # Use expected_size as it's more reliable
        uncompressed_size = expected_size

    output = bytearray()
    pos = 5  # Start after header

    try:
        while pos < len(data) and len(output) < uncompressed_size:
            cmd = data[pos]
            pos += 1

            if cmd <= 0x7F:
                # 0x00-0x7F: Literal bytes + short backref
                # Bits: 0 L L O O O O O
                # L = literal count (0-3), O = offset low bits
                literal_count = (cmd >> 5) & 0x03

                # Copy literals
                for _ in range(literal_count):
                    if pos >= len(data):
                        raise CompressionError("Unexpected end in literal run")
                    output.append(data[pos])
                    pos += 1

                # Backref
                if pos >= len(data):
                    raise CompressionError("Unexpected end reading backref")
                byte2 = data[pos]
                pos += 1

                offset = ((cmd & 0x1F) << 3) | ((byte2 >> 5) & 0x07)
                length = (byte2 & 0x1F) + 3

                offset += 1  # Offset is 1-based
                _copy_backref(output, offset, length)

            elif cmd <= 0xBF:
                # 0x80-0xBF: Short backref
                # offset < 1024, length 3-10
                if pos >= len(data):
                    raise CompressionError("Unexpected end in short backref")
                byte2 = data[pos]
                pos += 1

                offset = ((cmd & 0x03) << 8) | byte2
                length = ((cmd >> 2) & 0x07) + 3

                offset += 1
                _copy_backref(output, offset, length)

            elif cmd <= 0xDF:
                # 0xC0-0xDF: Medium backref
                # offset < 16384, length 4-67
                if pos + 2 > len(data):
                    raise CompressionError("Unexpected end in medium backref")
                byte2 = data[pos]
                byte3 = data[pos + 1]
                pos += 2

                offset = ((cmd & 0x03) << 12) | (byte2 << 4) | ((byte3 >> 4) & 0x0F)
                length = ((cmd >> 2) & 0x0F) + 4

                offset += 1
                _copy_backref(output, offset, length)

            elif cmd <= 0xFB:
                # 0xE0-0xFB: Literal run (1-28 bytes)
                literal_count = (cmd - 0xDF)

                for _ in range(literal_count):
                    if pos >= len(data):
                        raise CompressionError("Unexpected end in literal run")
                    output.append(data[pos])
                    pos += 1

            else:
                # 0xFC-0xFF: Stop codes
                # 0xFC = stop, 0xFD-0xFF = stop + trailing literals
                trailing = cmd - 0xFC
                for _ in range(trailing):
                    if pos >= len(data):
                        break
                    output.append(data[pos])
                    pos += 1
                break

        result = bytes(output)

        if expected_size > 0 and len(result) != expected_size:
            raise CompressionError(
                f"RefPack size mismatch: got {len(result)}, expected {expected_size}"
            )

        return result

    except IndexError as e:
        raise CompressionError(f"RefPack decompression failed: {e}")


def _copy_backref(output: bytearray, offset: int, length: int) -> None:
    """Copy bytes from earlier in output (backref)."""
    if offset > len(output):
        raise CompressionError(f"Invalid backref offset {offset} (output size {len(output)})")

    start = len(output) - offset
    for i in range(length):
        # Must read one at a time - backref can overlap with destination
        output.append(output[start + i])


def compress(data: bytes, compression_type: int) -> bytes:
    """Compress data using the specified compression type.

    Args:
        data: Uncompressed data bytes
        compression_type: Compression type to use

    Returns:
        Compressed data with appropriate header

    Raises:
        CompressionError: If compression fails or type unsupported
    """
    if compression_type == COMPRESSION_NONE:
        return data

    if compression_type == COMPRESSION_ZLIB:
        return compress_zlib(data)

    raise CompressionError(f"Compression not supported for type: 0x{compression_type:04X}")


def compress_zlib(data: bytes) -> bytes:
    """Compress data using zlib/deflate.

    Returns data with 2-byte header matching Sims 4 format.

    Args:
        data: Uncompressed data

    Returns:
        Compressed data with header
    """
    # Compress with raw deflate (no zlib wrapper)
    compressed = zlib.compress(data, level=9)[2:-4]  # Strip zlib header/trailer

    # Add 2-byte header (compression marker)
    header = bytes([0x78, 0x9C])  # Standard zlib header for level 9
    return header + compressed
