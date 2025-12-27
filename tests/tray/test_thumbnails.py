"""Tests for thumbnail extraction."""

import tempfile
from pathlib import Path

import pytest

from s4lt.tray.thumbnails import extract_thumbnail, get_image_format
from s4lt.tray.exceptions import ThumbnailError


# Minimal valid PNG header (8 bytes magic + IHDR chunk)
MINIMAL_PNG = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
    0x00, 0x00, 0x00, 0x0D,  # IHDR length = 13
    0x49, 0x48, 0x44, 0x52,  # "IHDR"
    0x00, 0x00, 0x00, 0x01,  # width = 1
    0x00, 0x00, 0x00, 0x01,  # height = 1
    0x08, 0x02,              # bit depth = 8, color type = 2 (RGB)
    0x00, 0x00, 0x00,        # compression, filter, interlace
    0x90, 0x77, 0x53, 0xDE,  # CRC
    0x00, 0x00, 0x00, 0x00,  # IEND length = 0
    0x49, 0x45, 0x4E, 0x44,  # "IEND"
    0xAE, 0x42, 0x60, 0x82,  # CRC
])


def test_detect_png_format():
    """Should detect PNG format from magic bytes."""
    with tempfile.NamedTemporaryFile(suffix=".hhi", delete=False) as f:
        f.write(MINIMAL_PNG)
        path = Path(f.name)

    try:
        fmt = get_image_format(path)
        assert fmt == "png"
    finally:
        path.unlink()


def test_extract_thumbnail_png():
    """Should extract PNG thumbnail data."""
    with tempfile.NamedTemporaryFile(suffix=".sgi", delete=False) as f:
        f.write(MINIMAL_PNG)
        path = Path(f.name)

    try:
        data, fmt = extract_thumbnail(path)
        assert fmt == "png"
        assert data == MINIMAL_PNG
    finally:
        path.unlink()


def test_extract_thumbnail_with_header():
    """Should handle files with prefix header before image data."""
    # Some Sims 4 thumbnail files have metadata before the PNG
    header = b"\x00\x01\x02\x03" * 16  # 64 byte fake header

    with tempfile.NamedTemporaryFile(suffix=".bpi", delete=False) as f:
        f.write(header + MINIMAL_PNG)
        path = Path(f.name)

    try:
        data, fmt = extract_thumbnail(path)
        assert fmt == "png"
        # Should find and extract just the PNG portion
        assert data.startswith(b"\x89PNG")
    finally:
        path.unlink()


def test_invalid_thumbnail_raises():
    """Invalid image file should raise ThumbnailError."""
    with tempfile.NamedTemporaryFile(suffix=".hhi", delete=False) as f:
        f.write(b"not an image file at all")
        path = Path(f.name)

    try:
        with pytest.raises(ThumbnailError):
            extract_thumbnail(path)
    finally:
        path.unlink()
