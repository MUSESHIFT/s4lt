"""Mod sorting and organization."""

import re
from pathlib import Path


def normalize_creator(name: str) -> str:
    """Normalize creator name for consistent grouping.

    Args:
        name: Raw creator name

    Returns:
        Normalized name (title case)
    """
    return name.title()


def extract_creator(filename: str) -> str:
    """Extract creator name from mod filename.

    Parses common naming conventions:
    - SimsyCreator_CASHair.package -> Simsycreator
    - TS4-Bobby-Dress.package -> Bobby
    - Creator-ModName.package -> Creator

    Args:
        filename: Mod filename

    Returns:
        Creator name or "_Uncategorized"
    """
    patterns = [
        r"^TS4[-_]([A-Za-z0-9]+)[-_]",  # TS4-Bobby-Dress, TS4_Bobby_Dress
        r"^([A-Za-z0-9]+)_",             # SimsyCreator_Hair
        r"^([A-Za-z0-9]+)-",             # Creator-ModName
    ]

    for pattern in patterns:
        match = re.match(pattern, filename)
        if match:
            return normalize_creator(match.group(1))

    return "_Uncategorized"
