"""CC tracking - TGI extraction and classification."""

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from s4lt.tray.item import TrayItem


@dataclass
class TGI:
    """Type/Group/Instance identifier."""
    type_id: int
    group_id: int
    instance_id: int

    def __hash__(self):
        return hash((self.type_id, self.group_id, self.instance_id))

    def __eq__(self, other):
        if not isinstance(other, TGI):
            return False
        return (self.type_id, self.group_id, self.instance_id) == \
               (other.type_id, other.group_id, other.instance_id)


@dataclass
class CCReference:
    """A CC reference with its source."""
    tgi: TGI
    source: str  # "ea", "mod", "missing"
    mod_path: Path | None = None
    mod_name: str | None = None


# Known resource types that indicate CC content
CC_RESOURCE_TYPES = {
    0x034AEECB,  # CAS Part
    0x319E4F1D,  # Object Definition
    0x00B2D882,  # DDS Texture
    0xC0DB5AE7,  # Thumbnail
    0x025ED6F4,  # STBL (strings)
    0x545AC67A,  # Geometry
}


def extract_tgis_from_binary(path: Path) -> list[TGI]:
    """Extract TGI patterns from a binary tray file.

    Scans the file for 16-byte TGI patterns.

    Args:
        path: Path to .householdbinary, .blueprint, etc.

    Returns:
        List of extracted TGIs
    """
    tgis = []

    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return []

    # Scan for TGI patterns
    # TGI = type(4 bytes) + group(4 bytes) + instance(8 bytes)
    offset = 0
    while offset + 16 <= len(data):
        type_id = struct.unpack_from("<I", data, offset)[0]
        group_id = struct.unpack_from("<I", data, offset + 4)[0]
        instance_id = struct.unpack_from("<Q", data, offset + 8)[0]

        # Filter: only include known CC resource types
        # and reasonable instance IDs (non-zero)
        if type_id in CC_RESOURCE_TYPES and instance_id > 0:
            tgis.append(TGI(type_id, group_id, instance_id))

        offset += 1  # Slide window by 1 byte

    # Deduplicate
    return list(set(tgis))


def extract_tgis_from_tray_item(item: TrayItem) -> list[TGI]:
    """Extract all TGIs from a tray item's binary files.

    Args:
        item: TrayItem to analyze

    Returns:
        List of unique TGIs found
    """
    all_tgis = []

    # Binary file extensions to scan
    binary_extensions = {".householdbinary", ".blueprint", ".room"}

    for file_path in item.files:
        if file_path.suffix.lower() in binary_extensions:
            tgis = extract_tgis_from_binary(file_path)
            all_tgis.extend(tgis)

    return list(set(all_tgis))
