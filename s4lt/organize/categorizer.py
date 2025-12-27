"""Mod categorization by resource type analysis."""

import sqlite3
from collections import Counter
from enum import Enum


class ModCategory(Enum):
    """Categories for mod classification."""
    CAS = "CAS"
    BUILD_BUY = "BuildBuy"
    SCRIPT = "Script"
    TUNING = "Tuning"
    OVERRIDE = "Override"
    GAMEPLAY = "Gameplay"
    UNKNOWN = "Unknown"


# Priority for tiebreaker (higher = wins ties)
CATEGORY_PRIORITY: dict[ModCategory, int] = {
    ModCategory.SCRIPT: 100,
    ModCategory.CAS: 80,
    ModCategory.BUILD_BUY: 70,
    ModCategory.OVERRIDE: 60,
    ModCategory.GAMEPLAY: 50,
    ModCategory.TUNING: 40,
    ModCategory.UNKNOWN: 0,
}


# Resource type ID → category mapping
TYPE_TO_CATEGORY: dict[int, ModCategory] = {
    # CAS (Create-a-Sim)
    0x034AEECB: ModCategory.CAS,      # CASPart
    0x0355E0A6: ModCategory.CAS,      # BoneDelta
    0x0354796A: ModCategory.CAS,      # Skintone
    0xB6C8B6A0: ModCategory.CAS,      # CASTexture
    0x105205BA: ModCategory.CAS,      # SimPreset
    0x71BDB8A2: ModCategory.CAS,      # StyledLook
    0xEAA32ADD: ModCategory.CAS,      # CASPreset

    # Build/Buy
    0x319E4F1D: ModCategory.BUILD_BUY,  # ObjectCatalog
    0xC0DB5AE7: ModCategory.BUILD_BUY,  # ObjectDefinition
    0xB91E18DB: ModCategory.BUILD_BUY,  # ObjectCatalogSet
    0x07936CE0: ModCategory.BUILD_BUY,  # Block
    0xB4F762C9: ModCategory.BUILD_BUY,  # Floor
    0xFE33068E: ModCategory.BUILD_BUY,  # Wall
    0x1C1CF1F7: ModCategory.BUILD_BUY,  # Railing
    0xEBCBB16C: ModCategory.BUILD_BUY,  # Stairs

    # Script mods
    0x9C07855E: ModCategory.SCRIPT,     # Python bytecode

    # Tuning
    0x0333406C: ModCategory.TUNING,     # Tuning XML
    0x025ED6F4: ModCategory.TUNING,     # SimData
    0x545AC67A: ModCategory.TUNING,     # CombinedTuning
}


def categorize_mod(conn: sqlite3.Connection, mod_id: int) -> ModCategory:
    """Determine category for a mod based on its resources.

    Algorithm:
    1. Count resources by category
    2. Pick category with highest count
    3. On tie, use priority to break

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
        return ModCategory.UNKNOWN

    # Count resources by category
    category_counts: Counter[ModCategory] = Counter()
    for type_id in type_ids:
        category = TYPE_TO_CATEGORY.get(type_id, ModCategory.UNKNOWN)
        category_counts[category] += 1

    if not category_counts:
        return ModCategory.UNKNOWN

    # Find max count
    max_count = max(category_counts.values())
    candidates = [cat for cat, count in category_counts.items() if count == max_count]

    if len(candidates) == 1:
        return candidates[0]

    # Tiebreaker: highest priority wins
    return max(candidates, key=lambda c: CATEGORY_PRIORITY[c])
