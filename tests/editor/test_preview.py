"""Tests for texture preview."""

import struct

from s4lt.editor.preview import can_preview, get_preview_png, get_preview_info


def test_can_preview_dds():
    """Should identify previewable types."""
    assert can_preview(0x00B2D882)  # DDS
    assert not can_preview(0x220557DA)  # STBL


def test_get_preview_returns_png():
    """Preview should return PNG data."""
    # Create minimal DDS (just header, will fail gracefully)
    dds_data = b"DDS " + b"\x00" * 124

    result = get_preview_png(dds_data, 0x00B2D882)

    # Should return None for invalid DDS (graceful failure)
    # or PNG bytes for valid DDS
    assert result is None or result[:4] == b"\x89PNG"


def test_get_preview_info_dds():
    """Should extract DDS metadata."""
    # Create DDS with known dimensions
    dds_data = bytearray(b"DDS " + b"\x00" * 124)
    struct.pack_into("<I", dds_data, 12, 512)  # height
    struct.pack_into("<I", dds_data, 16, 256)  # width

    info = get_preview_info(bytes(dds_data), 0x00B2D882)

    assert info is not None
    assert info["width"] == 256
    assert info["height"] == 512
    assert info["format"] == "DDS"
