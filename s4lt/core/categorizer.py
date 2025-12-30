"""Package categorization based on resource types."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from s4lt.core.package import Package
from s4lt.core.types import RESOURCE_TYPES

logger = logging.getLogger(__name__)

# CAS (Create-A-Sim) resource types
CAS_TYPES = {
    0x034AEECB,  # CASPart - hair, clothes, accessories
    0x0354796A,  # Skintone
    0x9D1AB874,  # Sculpt - face/body sculpts
    0x105205BA,  # SimPreset
    0x71BDB8A2,  # StyledLook
    0xEAA32ADD,  # CASPreset
    0xC5F6763E,  # SimModifier - body sliders
    0x0355E0A6,  # BoneDelta
    0x015A1849,  # Geometry (CAS geometry)
    0x067CAA11,  # BlendGeometry
    0xAC16FBEC,  # RegionMap
    0xA7815676,  # ColorList
    0x9D7E7558,  # PeltBrush
    0x26AF8338,  # PeltLayer
    0xC4DFAE6D,  # PetCoatPattern
}

# Build/Buy resource types
BUILDBUY_TYPES = {
    0xC0DB5AE7,  # ObjectDefinition
    0x319E4F1D,  # ObjectCatalog
    0xB91E18DB,  # ObjectCatalogSet
    0xA0451CBD,  # ModularPieceCatalog
    0x9917EACD,  # ModularPiece
    # Build mode
    0x07936CE0,  # Block
    0x1D6DF1CF,  # Column
    0x13CF0ED2,  # DecoTrim
    0x0418FE2A,  # Fence
    0xB4F762C9,  # Floor
    0x84C23219,  # FloorTrim
    0x2FAE983E,  # Foundation
    0xE7ADA79D,  # FountainTrim
    0xA057811C,  # Frieze
    0x9151E6BC,  # HalfWall
    0x5003333C,  # Pond
    0xA5DFFCF3,  # PoolTrim
    0x1C1CF1F7,  # Railing
    0x91EDBD3E,  # RoofStyle
    0xF1EDBD86,  # RoofPattern
    0xB0311D0F,  # RoofTrim
    0x9A20CD1C,  # Spandrel
    0xEBCBB16C,  # Stairs
    0x1427C109,  # TerrainPaint
    0x76BCF80C,  # TerrainTool
    0xD5F0F921,  # Trim
    0xFE33068E,  # Wall
    0xA8F7B517,  # WindowSet
}

# Tuning/gameplay resource types
TUNING_TYPES = {
    0x0333406C,  # Tuning (generic)
    0x025ED6F4,  # SimData
    0x545AC67A,  # CombinedTuning
    0x62ECC59A,  # CombinedBinaryTuning
    0xB61DE6B4,  # ObjectTuning
    0xE231B3D8,  # ObjectModifiers
    0x6017E896,  # Buff
    0xCB5FDDC7,  # Trait
    0xE882D22F,  # Interaction
    0x0C772E27,  # Loot
}

# Thumbnail resource types (for extraction)
THUMBNAIL_TYPES = {
    0x3C1AF1F2,  # CASPartThumbnail (PNG)
    0x3C2A8647,  # ObjectThumbnail (PNG)
    0x5B282D45,  # BodyPartThumbnail
    0xCD9DE247,  # SimThumbnail
    0x9C925813,  # SimPresetThumbnail
    0x8E71065D,  # PetBreedThumbnail
    0xB67673A2,  # PetFaceThumbnail
}

# Image/texture types
IMAGE_TYPES = {
    0x00B2D882,  # DDS
    0x3453CF95,  # RLE2Image
    0xBA856C78,  # RLESImage
    0x2BC04EDF,  # LRLEImage
    0xB6C8B6A0,  # CASTexture
}


@dataclass
class PackageCategory:
    """Categorization result for a package."""

    category: str  # "cas", "buildbuy", "tuning", "script", "mixed", "other"
    subcategory: str  # More specific category
    resource_counts: dict[str, int]  # Count by type name
    instance_ids: list[int]  # All instance IDs (for conflict detection)
    has_thumbnail: bool
    total_resources: int

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "category": self.category,
            "subcategory": self.subcategory,
            "resource_counts": self.resource_counts,
            "instance_ids": self.instance_ids,
            "has_thumbnail": self.has_thumbnail,
            "total_resources": self.total_resources,
        }


def categorize_package(package_path: Path) -> Optional[PackageCategory]:
    """Analyze a package and determine its category.

    Args:
        package_path: Path to the .package file

    Returns:
        PackageCategory with analysis results, or None if parsing failed
    """
    # Handle .ts4script files
    if package_path.suffix.lower() == ".ts4script":
        return PackageCategory(
            category="script",
            subcategory="script_mod",
            resource_counts={"Script": 1},
            instance_ids=[],
            has_thumbnail=False,
            total_resources=1,
        )

    try:
        with Package.open(package_path) as pkg:
            # Count resources by type
            type_counts: dict[int, int] = {}
            instance_ids: list[int] = []
            has_thumbnail = False

            for resource in pkg.resources:
                type_id = resource.type_id
                type_counts[type_id] = type_counts.get(type_id, 0) + 1
                instance_ids.append(resource.instance_id)

                if type_id in THUMBNAIL_TYPES:
                    has_thumbnail = True

            # Convert type IDs to names for readable output
            resource_counts = {}
            for type_id, count in type_counts.items():
                name = RESOURCE_TYPES.get(type_id, f"Unknown_{type_id:08X}")
                resource_counts[name] = count

            # Determine primary category
            cas_count = sum(type_counts.get(t, 0) for t in CAS_TYPES)
            buildbuy_count = sum(type_counts.get(t, 0) for t in BUILDBUY_TYPES)
            tuning_count = sum(type_counts.get(t, 0) for t in TUNING_TYPES)

            # Determine category based on dominant type
            if cas_count > 0 and cas_count >= buildbuy_count and cas_count >= tuning_count:
                category = "cas"
                subcategory = _determine_cas_subcategory(type_counts)
            elif buildbuy_count > 0 and buildbuy_count >= tuning_count:
                category = "buildbuy"
                subcategory = _determine_buildbuy_subcategory(type_counts)
            elif tuning_count > 0:
                category = "tuning"
                subcategory = _determine_tuning_subcategory(type_counts)
            elif cas_count > 0 or buildbuy_count > 0:
                category = "mixed"
                subcategory = "mixed_content"
            else:
                category = "other"
                subcategory = "unknown"

            return PackageCategory(
                category=category,
                subcategory=subcategory,
                resource_counts=resource_counts,
                instance_ids=instance_ids,
                has_thumbnail=has_thumbnail,
                total_resources=len(pkg.resources),
            )

    except Exception as e:
        logger.warning(f"Failed to categorize {package_path}: {e}")
        return None


def _determine_cas_subcategory(type_counts: dict[int, int]) -> str:
    """Determine CAS subcategory based on resource types."""
    # Check for specific CAS types
    if type_counts.get(0x034AEECB, 0) > 0:  # CASPart
        return "cas_part"  # Could be hair, clothes, accessories
    if type_counts.get(0x0354796A, 0) > 0:  # Skintone
        return "skintone"
    if type_counts.get(0x9D1AB874, 0) > 0:  # Sculpt
        return "sculpt"
    if type_counts.get(0x105205BA, 0) > 0:  # SimPreset
        return "preset"
    if type_counts.get(0xC5F6763E, 0) > 0:  # SimModifier
        return "slider"
    if type_counts.get(0xC4DFAE6D, 0) > 0:  # PetCoatPattern
        return "pet_coat"
    return "cas_other"


def _determine_buildbuy_subcategory(type_counts: dict[int, int]) -> str:
    """Determine Build/Buy subcategory based on resource types."""
    # Check for build mode types
    if type_counts.get(0xFE33068E, 0) > 0:  # Wall
        return "wall"
    if type_counts.get(0xB4F762C9, 0) > 0:  # Floor
        return "floor"
    if type_counts.get(0x91EDBD3E, 0) > 0 or type_counts.get(0xF1EDBD86, 0) > 0:  # RoofStyle/Pattern
        return "roof"
    if type_counts.get(0x0418FE2A, 0) > 0:  # Fence
        return "fence"
    if type_counts.get(0xEBCBB16C, 0) > 0:  # Stairs
        return "stairs"
    if type_counts.get(0xA8F7B517, 0) > 0:  # WindowSet
        return "window"

    # Check for object types
    if type_counts.get(0xC0DB5AE7, 0) > 0 or type_counts.get(0x319E4F1D, 0) > 0:
        return "object"

    return "buildbuy_other"


def _determine_tuning_subcategory(type_counts: dict[int, int]) -> str:
    """Determine tuning subcategory based on resource types."""
    if type_counts.get(0x6017E896, 0) > 0:  # Buff
        return "buff"
    if type_counts.get(0xCB5FDDC7, 0) > 0:  # Trait
        return "trait"
    if type_counts.get(0xE882D22F, 0) > 0:  # Interaction
        return "interaction"
    if type_counts.get(0x0C772E27, 0) > 0:  # Loot
        return "loot"
    return "tuning_other"


def get_category_display_name(category: str) -> str:
    """Get display name for a category."""
    names = {
        "cas": "CAS CC",
        "buildbuy": "Build/Buy",
        "tuning": "Tuning Mod",
        "script": "Script Mod",
        "mixed": "Mixed Content",
        "other": "Other",
    }
    return names.get(category, category.title())


def get_subcategory_display_name(subcategory: str) -> str:
    """Get display name for a subcategory."""
    names = {
        "cas_part": "CAS Part",
        "skintone": "Skintone",
        "sculpt": "Sculpt",
        "preset": "Preset",
        "slider": "Slider",
        "pet_coat": "Pet Coat",
        "cas_other": "Other CAS",
        "wall": "Wall",
        "floor": "Floor",
        "roof": "Roof",
        "fence": "Fence",
        "stairs": "Stairs",
        "window": "Window",
        "object": "Object",
        "buildbuy_other": "Other Build/Buy",
        "buff": "Buff",
        "trait": "Trait",
        "interaction": "Interaction",
        "loot": "Loot",
        "tuning_other": "Other Tuning",
        "script_mod": "Script Mod",
        "mixed_content": "Mixed",
        "unknown": "Unknown",
    }
    return names.get(subcategory, subcategory.replace("_", " ").title())
