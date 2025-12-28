"""Texture preview support."""

import io
from PIL import Image


# Previewable resource types
TYPE_DDS = 0x00B2D882
TYPE_DST = 0x2F7D0004
TYPE_PNG = 0x2F7D0006  # Not standard, but sometimes used


PREVIEWABLE_TYPES = {TYPE_DDS, TYPE_DST, TYPE_PNG}


def can_preview(type_id: int) -> bool:
    """Check if a resource type can be previewed.

    Args:
        type_id: Resource type ID

    Returns:
        True if previewable
    """
    return type_id in PREVIEWABLE_TYPES


def get_preview_png(data: bytes, type_id: int) -> bytes | None:
    """Generate PNG preview for a resource.

    Args:
        data: Raw resource data
        type_id: Resource type ID

    Returns:
        PNG bytes or None if preview failed
    """
    try:
        if type_id == TYPE_DDS:
            return _decode_dds(data)
        elif type_id == TYPE_DST:
            return _decode_dst(data)
        elif type_id == TYPE_PNG:
            return data  # Already PNG
        return None
    except Exception:
        return None


def _decode_dds(data: bytes) -> bytes | None:
    """Decode DDS texture to PNG.

    DDS format:
    - 4 bytes: "DDS "
    - 124 bytes: DDS_HEADER
    - Variable: Pixel data

    This is a simplified decoder for common DDS formats.
    """
    if len(data) < 128 or data[:4] != b"DDS ":
        return None

    try:
        # Try using Pillow's DDS support
        img = Image.open(io.BytesIO(data))
        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()
    except Exception:
        return None


def _decode_dst(data: bytes) -> bytes | None:
    """Decode Sims 4 DST texture to PNG.

    DST is a proprietary format. Basic implementation:
    - Try treating as DDS variant
    - Fall back to raw pixel interpretation
    """
    # DST often starts with a header similar to DDS
    # Try DDS decode first
    if len(data) > 128:
        result = _decode_dds(data)
        if result:
            return result

    # DST-specific decode would go here
    # For now, return None (not implemented)
    return None


def get_preview_info(data: bytes, type_id: int) -> dict | None:
    """Get preview metadata without full decode.

    Args:
        data: Raw resource data
        type_id: Resource type ID

    Returns:
        Dict with width, height, format info, or None
    """
    if type_id == TYPE_DDS and len(data) >= 128 and data[:4] == b"DDS ":
        # Parse DDS header
        import struct
        height = struct.unpack_from("<I", data, 12)[0]
        width = struct.unpack_from("<I", data, 16)[0]
        return {
            "width": width,
            "height": height,
            "format": "DDS",
        }

    return None
