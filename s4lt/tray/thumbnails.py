"""Thumbnail extraction from tray image files.

Sims 4 tray items use several image file types:
- .hhi - Household images
- .sgi - Individual Sim images
- .bpi - Lot/blueprint images

These files typically contain PNG data, sometimes with a
proprietary header that must be skipped.
"""

from pathlib import Path

from s4lt.tray.exceptions import ThumbnailError


# Magic bytes for image formats
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JFIF_MAGIC = b"\xff\xd8\xff"


def get_image_format(path: Path) -> str | None:
    """Detect image format from file.

    Args:
        path: Path to image file

    Returns:
        Format string ("png", "jpeg") or None if unknown
    """
    try:
        with open(path, "rb") as f:
            data = f.read(1024)  # Read enough to find magic

            # Check for PNG anywhere in first 1KB
            png_offset = data.find(PNG_MAGIC)
            if png_offset >= 0:
                return "png"

            # Check for JPEG
            jfif_offset = data.find(JFIF_MAGIC)
            if jfif_offset >= 0:
                return "jpeg"

            return None

    except OSError:
        return None


def extract_thumbnail(path: Path) -> tuple[bytes, str]:
    """Extract thumbnail image data from tray image file.

    Handles files that may have proprietary headers before
    the actual image data.

    Args:
        path: Path to .hhi, .sgi, or .bpi file

    Returns:
        Tuple of (image_data, format_string)

    Raises:
        ThumbnailError: If no valid image found
    """
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        raise ThumbnailError(f"Could not read file: {e}")

    # Try to find PNG data
    png_offset = data.find(PNG_MAGIC)
    if png_offset >= 0:
        return data[png_offset:], "png"

    # Try to find JPEG data
    jfif_offset = data.find(JFIF_MAGIC)
    if jfif_offset >= 0:
        return data[jfif_offset:], "jpeg"

    raise ThumbnailError(f"No valid image found in {path.name}")


def save_thumbnail(path: Path, output_path: Path) -> str:
    """Extract and save thumbnail to output file.

    Args:
        path: Path to source tray image file
        output_path: Path to save extracted image

    Returns:
        Format of saved image ("png" or "jpeg")

    Raises:
        ThumbnailError: If extraction fails
    """
    data, fmt = extract_thumbnail(path)

    # Ensure correct extension
    if fmt == "png" and output_path.suffix.lower() != ".png":
        output_path = output_path.with_suffix(".png")
    elif fmt == "jpeg" and output_path.suffix.lower() not in (".jpg", ".jpeg"):
        output_path = output_path.with_suffix(".jpg")

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(data)
        return fmt
    except OSError as e:
        raise ThumbnailError(f"Could not save thumbnail: {e}")
