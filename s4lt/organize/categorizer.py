"""Mod categorization by resource type analysis."""

import sqlite3
from collections import Counter
from enum import Enum
from pathlib import Path
from typing import Optional


class ModCategory(Enum):
    """Categories for mod classification.

    Categories are mutually exclusive and represent the PRIMARY purpose:
    - SCRIPT: Contains Python/.ts4script code (like MCCC, Wicked Whims)
    - CAS: Create-a-Sim items (hair, clothes, makeup, skins, accessories)
    - BUILD_BUY: Objects, furniture, walls, floors for building
    - TUNING: XML tuning overrides (gameplay tweaks without scripts)
    - OTHER: Everything else (merged packs, unknown)
    """
    SCRIPT = "Script Mod"
    CAS = "CAS CC"
    BUILD_BUY = "Build/Buy CC"
    TUNING = "Tuning Mod"
    OTHER = "Other"


# Priority for tiebreaker (higher = wins ties)
# Script mods take highest priority - if it has scripts, it's a script mod
CATEGORY_PRIORITY: dict[ModCategory, int] = {
    ModCategory.SCRIPT: 100,      # Script mods always win
    ModCategory.CAS: 80,          # CAS CC
    ModCategory.BUILD_BUY: 70,    # Build/Buy CC
    ModCategory.TUNING: 50,       # Tuning mods
    ModCategory.OTHER: 0,         # Unknown/other
}


# Resource type IDs that indicate SCRIPT MODS
# If ANY of these are present, it's a script mod
SCRIPT_TYPE_IDS: set[int] = {
    0x073FAA07,  # TS4Script (.ts4script compiled Python)
    0x9C07855E,  # Python bytecode (.pyc/.pyo)
}


# Resource type ID → category mapping
TYPE_TO_CATEGORY: dict[int, ModCategory] = {
    # ===========================================
    # SCRIPT MODS - Python code / .ts4script
    # ===========================================
    0x073FAA07: ModCategory.SCRIPT,     # TS4Script (compiled Python in .ts4script)
    0x9C07855E: ModCategory.SCRIPT,     # Python bytecode (.pyc/.pyo)

    # ===========================================
    # CAS (Create-a-Sim) CC
    # Hair, clothing, accessories, makeup, skins
    # ===========================================
    0x034AEECB: ModCategory.CAS,      # CASPart (the main CAS item definition)
    0x0355E0A6: ModCategory.CAS,      # BoneDelta (bone adjustments)
    0x0354796A: ModCategory.CAS,      # Skintone
    0xB6C8B6A0: ModCategory.CAS,      # CASTexture (textures for CAS items)
    0x105205BA: ModCategory.CAS,      # SimPreset
    0x71BDB8A2: ModCategory.CAS,      # StyledLook
    0xEAA32ADD: ModCategory.CAS,      # CASPreset
    0xC5F6763E: ModCategory.CAS,      # CAS Part Modifier
    0xF7856BA9: ModCategory.CAS,      # BodyBlendData
    0x58F99AF9: ModCategory.CAS,      # SkinToneData
    0xB52F5055: ModCategory.CAS,      # HairColorPreset
    0x9D1AB874: ModCategory.CAS,      # DeformerMap (body morphs)
    0x0418FE2A: ModCategory.CAS,      # SimOutfit

    # ===========================================
    # BUILD/BUY CC
    # Furniture, objects, walls, floors, stairs
    # ===========================================
    0x319E4F1D: ModCategory.BUILD_BUY,  # ObjectCatalog
    0xC0DB5AE7: ModCategory.BUILD_BUY,  # ObjectDefinition
    0xB91E18DB: ModCategory.BUILD_BUY,  # ObjectCatalogSet
    0x07936CE0: ModCategory.BUILD_BUY,  # Block (building block)
    0xB4F762C9: ModCategory.BUILD_BUY,  # Floor
    0xFE33068E: ModCategory.BUILD_BUY,  # Wall
    0x1C1CF1F7: ModCategory.BUILD_BUY,  # Railing
    0xEBCBB16C: ModCategory.BUILD_BUY,  # Stairs
    0x0D338A3A: ModCategory.BUILD_BUY,  # Roof trim
    0x3DD914B4: ModCategory.BUILD_BUY,  # RoofPattern
    0x049CA4CD: ModCategory.BUILD_BUY,  # Fence
    0x3D56B7A0: ModCategory.BUILD_BUY,  # Foundation
    0xD5F0F921: ModCategory.BUILD_BUY,  # Pool
    0x9C925813: ModCategory.BUILD_BUY,  # PoolTrim
    0x1661233C: ModCategory.BUILD_BUY,  # Terrain paint

    # ===========================================
    # TUNING MODS
    # XML tweaks, gameplay changes without scripts
    # ===========================================
    0x0333406C: ModCategory.TUNING,     # Tuning XML
    0x025ED6F4: ModCategory.TUNING,     # SimData
    0x545AC67A: ModCategory.TUNING,     # CombinedTuning
    0x6017E896: ModCategory.TUNING,     # Object Tuning
    0xB61DE6B4: ModCategory.TUNING,     # Interaction Tuning
    0x8B18FF6E: ModCategory.TUNING,     # Buff Tuning
    0x5D6B4F84: ModCategory.TUNING,     # Trait Tuning
    0x339BC5BD: ModCategory.TUNING,     # Relationship Tuning
    0x02D5DF13: ModCategory.TUNING,     # Aspiration Tuning
    0x0C772E27: ModCategory.TUNING,     # Career Tuning
    0x48A5A22A: ModCategory.TUNING,     # Recipe Tuning
    0xE882D22F: ModCategory.TUNING,     # Situation Tuning
}

# ===========================================
# Resource types that are SHARED between categories
# (Don't use these alone to categorize - they're in many mods)
# ===========================================
SHARED_RESOURCE_TYPES: set[int] = {
    0x00B2D882,  # DDS texture (used by everything)
    0x00B2D882,  # DXT5 texture
    0x015A1849,  # Geometry (3D mesh - used by CAS and Build/Buy)
    0x01661233,  # Model (3D model)
    0x0166038C,  # Model LOD
    0x8EAF13DE,  # Rig (skeleton)
    0x01D0E75D,  # CLIP (animation)
    0x01D10F34,  # Animation state machine
    0x220557DA,  # StringTable (STBL - text)
    0x3C1AF1F2,  # Thumbnail
    0xD3044521,  # MaterialDefinition
}


def categorize_mod(conn: sqlite3.Connection, mod_id: int) -> ModCategory:
    """Determine category for a mod based on its resources.

    Algorithm:
    1. If mod contains ANY script type IDs → SCRIPT (always)
    2. Otherwise, count resources by category (excluding shared types)
    3. Pick category with highest count
    4. On tie, use priority to break

    Args:
        conn: Database connection
        mod_id: ID of the mod to categorize

    Returns:
        ModCategory for the mod
    """
    cursor = conn.execute(
        "SELECT type_id FROM resources WHERE mod_id = ?",
        (mod_id,)
    )
    type_ids = [row[0] for row in cursor.fetchall()]

    if not type_ids:
        return ModCategory.OTHER

    # RULE 1: If ANY script types are present, it's a script mod
    # This catches MCCC, Wicked Whims, and other script mods
    type_id_set = set(type_ids)
    if type_id_set & SCRIPT_TYPE_IDS:
        return ModCategory.SCRIPT

    # Count resources by category (excluding shared types)
    category_counts: Counter[ModCategory] = Counter()
    for type_id in type_ids:
        if type_id in SHARED_RESOURCE_TYPES:
            continue  # Don't count shared types
        category = TYPE_TO_CATEGORY.get(type_id, ModCategory.OTHER)
        category_counts[category] += 1

    if not category_counts:
        # Only shared resources - try to guess from what shared types are present
        # If it has meshes/textures, it's likely CC
        return ModCategory.OTHER

    # Remove OTHER from consideration if we have real categories
    real_categories = {k: v for k, v in category_counts.items() if k != ModCategory.OTHER}
    if real_categories:
        category_counts = Counter(real_categories)

    if not category_counts:
        return ModCategory.OTHER

    # Find max count
    max_count = max(category_counts.values())
    candidates = [cat for cat, count in category_counts.items() if count == max_count]

    if len(candidates) == 1:
        return candidates[0]

    # Tiebreaker: highest priority wins
    return max(candidates, key=lambda c: CATEGORY_PRIORITY[c])


def categorize_mod_by_path(path: Path) -> ModCategory:
    """Quick categorization by filename patterns (without opening the package).

    Used for fast initial categorization before full scan.
    """
    name_lower = path.name.lower()

    # .ts4script files are always script mods
    if name_lower.endswith('.ts4script'):
        return ModCategory.SCRIPT

    # Common script mod naming patterns
    script_patterns = ['_script', 'script_', 'mccc', 'mc_', 'ww_', 'basemental', 'nisa']
    for pattern in script_patterns:
        if pattern in name_lower:
            return ModCategory.SCRIPT

    # Can't determine from name alone
    return ModCategory.OTHER


def is_script_mod(conn: sqlite3.Connection, mod_id: int) -> bool:
    """Check if a mod contains any script resources.

    This is a fast check specifically for script detection.
    """
    placeholders = ','.join('?' * len(SCRIPT_TYPE_IDS))
    cursor = conn.execute(
        f"SELECT 1 FROM resources WHERE mod_id = ? AND type_id IN ({placeholders}) LIMIT 1",
        (mod_id, *SCRIPT_TYPE_IDS)
    )
    return cursor.fetchone() is not None
