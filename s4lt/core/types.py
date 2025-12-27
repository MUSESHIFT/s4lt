"""Resource type ID registry for Sims 4 packages."""

# Known resource type IDs mapped to human-readable names
# Reference: https://github.com/Kuree/Sims4Tools/wiki
RESOURCE_TYPES: dict[int, str] = {
    # CAS (Create-a-Sim)
    0x034AEECB: "CASPart",
    0x0355E0A6: "BodyBlendData",

    # Tuning & Data
    0x0333406C: "Tuning",
    0x025ED6F4: "SimData",
    0x545AC67A: "CombinedTuning",

    # Text
    0x220557DA: "StringTable",

    # Images
    0x00B2D882: "DDS",
    0x3C1AF1F2: "PNG",
    0x2F7D0004: "DST",

    # 3D Assets
    0x015A1849: "Geometry",
    0x00AE6C67: "Bone",
    0x8EAF13DE: "RIG",

    # Catalog
    0xC0DB5AE7: "CatalogObject",
    0x319E4F1D: "ObjectDefinition",

    # Animation
    0x02D5DF13: "CLIP",

    # Audio
    0x01EEF63A: "AuditoryData",

    # Thumbnails
    0x3C2A8647: "Thumbnail",
    0x5B282D45: "ThumbnailAlt",
}


def get_type_name(type_id: int) -> str:
    """Get human-readable name for a resource type ID.

    Args:
        type_id: The 32-bit resource type identifier

    Returns:
        Human-readable name if known, otherwise "Unknown_XXXXXXXX"
    """
    return RESOURCE_TYPES.get(type_id, f"Unknown_{type_id:08X}")
