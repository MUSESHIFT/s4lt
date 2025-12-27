"""Resource type ID registry for Sims 4 packages."""

# Known resource type IDs mapped to human-readable names
# Reference: https://simswiki.info/wiki.php?title=Sims_4:PackedFileTypes
# Reference: https://github.com/Kuree/Sims4Tools/wiki/Sims-4---Packed-File-Types
RESOURCE_TYPES: dict[int, str] = {
    # CAS (Create-a-Sim)
    0x034AEECB: "CASPart",
    0x0355E0A6: "BoneDelta",
    0x0354796A: "Skintone",
    0x015A1849: "Geometry",
    0x067CAA11: "BlendGeometry",
    0xAC16FBEC: "RegionMap",
    0x9D1AB874: "Sculpt",
    0x105205BA: "SimPreset",
    0x71BDB8A2: "StyledLook",
    0x27C01D95: "Walkstyle",
    0xEAA32ADD: "CASPreset",
    0xA7815676: "ColorList",
    0x9D7E7558: "PeltBrush",
    0x26AF8338: "PeltLayer",
    0xC4DFAE6D: "PetCoatPattern",

    # CAS Textures & Images
    0xB6C8B6A0: "CASTexture",
    0x00B2D882: "DDS",
    0x3453CF95: "RLE2Image",
    0xBA856C78: "RLESImage",
    0x2BC04EDF: "LRLEImage",
    0x2F7D0004: "DST",

    # Thumbnails
    0x3C1AF1F2: "CASPartThumbnail",
    0x3C2A8647: "ObjectThumbnail",
    0x5B282D45: "BodyPartThumbnail",
    0xCD9DE247: "SimThumbnail",
    0x9C925813: "SimPresetThumbnail",
    0x8E71065D: "PetBreedThumbnail",
    0xB67673A2: "PetFaceThumbnail",
    0x0D338A3A: "LotPreviewThumbnail",
    0xBD491726: "PlexThumbnail",
    0xAB19BCBA: "PlexUnitMaskThumbnail",
    0xA1FF2FC4: "WorldmapLotThumbnail",
    0x3BD45407: "HouseholdThumbnail",
    0x16CA6BC4: "ThumbnailExtra1",
    0xB0118C15: "ThumbnailExtra2",
    0xB93A9915: "ThumbnailCache",

    # Tuning & Data
    0x0333406C: "Tuning",
    0x025ED6F4: "SimData",
    0x545AC67A: "CombinedTuning",
    0x62E94D38: "CombinedBinaryTuning",
    0xB61DE6B4: "ObjectTuning",
    0xE231B3D8: "ObjectModifiers",

    # Text & Localization
    0x220557DA: "StringTable",

    # 3D Models & Meshes
    0x01661233: "Model",
    0x01D10F34: "ModelLOD",
    0x8EAF13DE: "Rig",
    0x00AE6C67: "Bone",
    0xD3044521: "Slot",
    0xD382BF57: "Footprint",
    0x4F726BBE: "ObjectFootprint",
    0x01D0E75D: "MaterialDefinition",
    0x02019972: "MaterialSet",
    0x81CA1A10: "CutoutInfoTable",
    0x07576A17: "ModelCutout",
    0xDB43E069: "DeformerMap",

    # Animation
    0x6B20C4F3: "CLIP",
    0x02D5DF13: "AnimationStateMachine",
    0xBC4A5044: "ClipHeader",
    0x033260E3: "TrackMask",
    0x1C99B344: "AnimBoundaryCondition",
    0xE2249422: "AnimConstraintCache",
    0x053A3E7B: "LocomotionBuilder",
    0x9AFE47F5: "LocomotionConfig",
    0x2D277213: "SyncPointSchema",

    # Audio
    0x01EEF63A: "AudioEffects",
    0x01A527DB: "AudioVocals",
    0xD2DC5BAD: "Ambience",
    0xFD04E3BE: "AudioConfig",
    0xC202C770: "MusicData",
    0x4115F9D5: "SoundMixProperties",
    0xA576C2E7: "SoundModifierMapping",
    0x1B25A024: "SoundProperties",
    0x73CB32C2: "VoiceEffect",
    0xC582D2FB: "VoicePlugin",
    0x376840D7: "AVI",

    # Catalog Objects
    0xC0DB5AE7: "ObjectDefinition",
    0x319E4F1D: "ObjectCatalog",
    0xB91E18DB: "ObjectCatalogSet",
    0xA0451CBD: "ModularPieceCatalog",
    0x9917EACD: "ModularPiece",

    # Build Mode
    0x07936CE0: "Block",
    0x1D6DF1CF: "Column",
    0x13CF0ED2: "DecoTrim",
    0x0418FE2A: "Fence",
    0xB4F762C9: "Floor",
    0x84C23219: "FloorTrim",
    0x2FAE983E: "Foundation",
    0xE7ADA79D: "FountainTrim",
    0xA057811C: "Frieze",
    0x9151E6BC: "HalfWall",
    0x5003333C: "Pond",
    0xA5DFFCF3: "PoolTrim",
    0x1C1CF1F7: "Railing",
    0x91EDBD3E: "RoofStyle",
    0xF1EDBD86: "RoofPattern",
    0xB0311D0F: "RoofTrim",
    0x3F0C529A: "Room",
    0x370EFD6E: "RoomDefinition",
    0x9A20CD1C: "Spandrel",
    0xEBCBB16C: "Stairs",
    0x1427C109: "TerrainPaint",
    0x76BCF80C: "TerrainTool",
    0xD5F0F921: "Trim",
    0xFE33068E: "Wall",
    0xA8F7B517: "WindowSet",

    # World
    0xAEE860E4: "ColorBlendedTerrain",
    0x45061106: "LotFootprintReference",
    0xFA25B7DE: "MaxisWorldPipeline2",
    0x9063660E: "RoadDefinition",
    0x71A449C9: "SkyBoxTextureData",
    0x3D8632D0: "TerrainBlendMap",
    0x9063660D: "TerrainData",
    0x2AD195F2: "TerrainHeightMap",
    0x033B2B66: "TerrainKDTree",
    0xAE39399F: "TerrainMesh",
    0x90624C1B: "TerrainSizeInfo",
    0xA4BA8645: "WaterMaskList",
    0x892C4B8A: "WorldCameraInfo",
    0xFB0DD002: "WorldCameraMesh",
    0x96B0BD17: "WorldColorTimelineMap",
    0xD04FA861: "WorldConditionalData",
    0x810A102D: "WorldData",
    0xF0633989: "WorldFileHeader",
    0x18F3C673: "WorldLightsInfo",
    0x12952634: "WorldLotArchitecture",
    0x91568FD8: "WorldLotObjects",
    0x3BF8FD86: "WorldLotParameterInfo",
    0x20D81496: "WorldManifestReference",
    0xFCB1A1E4: "WorldObjectData",
    0x0A227BCF: "WorldOffLotMeshReference",
    0xE0ED7129: "WorldSpawnerInfo",
    0x19301120: "WorldTimelineColor",
    0x5BE29703: "WorldVisualEffectsInfo",
    0x153D2219: "WorldWaterManifest",

    # World Related
    0xFD57A8D7: "ColorTimelineData",
    0x729F6C4F: "HouseholdDescription",
    0x01942E2C: "LotDescription",
    0x0119B36D: "QueryableWorldMask",
    0x4E71B4E6: "QueryableWorldMaskManifest",
    0xD65DAFF9: "RegionDescription",
    0x48C28979: "Spawner",
    0x1709627D: "WaterManifest",
    0x656322B7: "WorldCameraMeshReference",
    0xA680EA4B: "WorldDescription",
    0x4F726BBE: "WorldLandingStrip",
    0x78C8BCE4: "WorldManifest",
    0x1CC04273: "WorldMap",
    0xB734E44F: "WorldOffLotMesh",
    0x6F40796A: "WorldRoadPolys",

    # Lots & Households
    0x3924DE26: "Blueprint",
    0xD33C281E: "BlueprintImage",
    0x2A8A5E22: "TrayItem",
    0xB3C438F0: "HouseholdTemplate",
    0x56278554: "HouseholdFile",

    # UI
    0x669499DC: "Credits",
    0x26978421: "Cursor",
    0x25796DCA: "OpenTypeFont",
    0x62ECC59A: "ScaleFormGFX",
    0x276CA4B9: "TrueTypeFont",
    0xBDD82221: "UIControlEventMap",
    0x99D98089: "UIEventModeMapping",

    # Tuning Types (specific gameplay tuning)
    # Note: Most gameplay content (aspirations, careers, rewards, snippets, etc.)
    # uses the generic Tuning type (0x0333406C) differentiated by instance ID
    0x6017E896: "Buff",
    0xCB5FDDC7: "Trait",
    0xE882D22F: "Interaction",
    0x0C772E27: "Loot",
    0xE86B1EEF: "DirectoryIndex",  # Compression directory for DBPF

    # Effects
    0x1B192049: "VisualEffects",
    0x1B19204A: "VisualEffectsInstanceMap",
    0xEA5118B0: "VisualEffectsMerged",

    # Misc
    0x03B4C61D: "Light",
    0x122FC66A: "LotTypeEventMap",
    0x6DFF1A66: "MTXCatalog",
    0xAC03A936: "GenericMTX",
    0x3A1E944E: "Path",
    0x8B18FF6E: "SimHotspotControl",
    0xC5F6763E: "SimModifier",
    0x06AC244F: "TimelineEvents",
    0x47FDDFBC: "WaterMask",
    0x010FAF71: "AgeGenderMap",
    0x9F5CFF10: "Style",
    0x0166038C: "NameMap",
}


def get_type_name(type_id: int) -> str:
    """Get human-readable name for a resource type ID.

    Args:
        type_id: The 32-bit resource type identifier

    Returns:
        Human-readable name if known, otherwise "Unknown_XXXXXXXX"
    """
    return RESOURCE_TYPES.get(type_id, f"Unknown_{type_id:08X}")
