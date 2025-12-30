"""Thumbnail extraction from Sims 4 packages."""

import hashlib
import logging
from pathlib import Path
from typing import Optional

from s4lt.core.package import Package
from s4lt.core.categorizer import THUMBNAIL_TYPES, IMAGE_TYPES

logger = logging.getLogger(__name__)

# Cache directory for extracted thumbnails
CACHE_DIR = Path.home() / ".local" / "share" / "s4lt" / "cache" / "thumbnails"


def get_cache_dir() -> Path:
    """Get and ensure thumbnail cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def get_cache_path(package_path: Path) -> Path:
    """Get cache path for a package's thumbnail.

    Uses hash of the full path to create unique cache filename.
    """
    path_hash = hashlib.md5(str(package_path.absolute()).encode()).hexdigest()[:16]
    return get_cache_dir() / f"{path_hash}.png"


def extract_thumbnail(package_path: Path, use_cache: bool = True) -> Optional[bytes]:
    """Extract thumbnail PNG from a .package file.

    Args:
        package_path: Path to the .package file
        use_cache: Whether to use/update the cache

    Returns:
        PNG image bytes, or None if no thumbnail found
    """
    # Check cache first
    if use_cache:
        cache_path = get_cache_path(package_path)
        if cache_path.exists():
            # Check if cache is still valid (package hasn't changed)
            if cache_path.stat().st_mtime >= package_path.stat().st_mtime:
                try:
                    return cache_path.read_bytes()
                except Exception as e:
                    logger.warning(f"Failed to read cached thumbnail: {e}")

    # Extract from package
    thumbnail_data = _extract_thumbnail_from_package(package_path)

    # Cache the result
    if thumbnail_data and use_cache:
        try:
            cache_path = get_cache_path(package_path)
            cache_path.write_bytes(thumbnail_data)
        except Exception as e:
            logger.warning(f"Failed to cache thumbnail: {e}")

    return thumbnail_data


def _extract_thumbnail_from_package(package_path: Path) -> Optional[bytes]:
    """Extract thumbnail from package file."""
    try:
        with Package.open(package_path) as pkg:
            # First try PNG thumbnails (preferred)
            for resource in pkg.resources:
                if resource.type_id in THUMBNAIL_TYPES:
                    data = resource.extract()
                    if data and _is_valid_png(data):
                        return data

            # Try DDS textures as fallback (would need conversion)
            for resource in pkg.resources:
                if resource.type_id == 0x00B2D882:  # DDS
                    data = resource.extract()
                    if data:
                        # Try to convert DDS to PNG
                        png_data = _dds_to_png(data)
                        if png_data:
                            return png_data

    except Exception as e:
        logger.debug(f"Failed to extract thumbnail from {package_path}: {e}")

    return None


def _is_valid_png(data: bytes) -> bool:
    """Check if data is a valid PNG file."""
    return data[:8] == b'\x89PNG\r\n\x1a\n'


def _dds_to_png(dds_data: bytes) -> Optional[bytes]:
    """Convert DDS texture to PNG.

    This is a placeholder - full DDS conversion would need PIL/Pillow
    with DDS support or a specialized library.
    """
    try:
        # Check DDS magic
        if dds_data[:4] != b'DDS ':
            return None

        # Try using PIL if available
        try:
            from PIL import Image
            import io

            # PIL can read some DDS formats
            img = Image.open(io.BytesIO(dds_data))
            output = io.BytesIO()
            img.save(output, format='PNG')
            return output.getvalue()
        except Exception:
            # PIL couldn't handle this DDS format
            pass

    except Exception as e:
        logger.debug(f"DDS conversion failed: {e}")

    return None


def clear_cache() -> int:
    """Clear the thumbnail cache.

    Returns:
        Number of files deleted
    """
    cache_dir = get_cache_dir()
    count = 0
    for cache_file in cache_dir.glob("*.png"):
        try:
            cache_file.unlink()
            count += 1
        except Exception as e:
            logger.warning(f"Failed to delete cache file {cache_file}: {e}")
    return count


def get_cache_stats() -> dict:
    """Get cache statistics."""
    cache_dir = get_cache_dir()
    files = list(cache_dir.glob("*.png"))
    total_size = sum(f.stat().st_size for f in files)

    return {
        "count": len(files),
        "size_bytes": total_size,
        "size_mb": round(total_size / (1024 * 1024), 2),
        "path": str(cache_dir),
    }


def get_placeholder_thumbnail() -> bytes:
    """Return a placeholder thumbnail for packages without one.

    Returns a small gray PNG placeholder.
    """
    # 1x1 gray PNG (minimal valid PNG)
    # In a real implementation, we'd return a nicer placeholder
    return (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
        b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
        b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )
