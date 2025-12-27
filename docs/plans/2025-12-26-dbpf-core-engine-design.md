# S4LT Phase 1: DBPF Core Engine Design

**Date:** 2025-12-26
**Status:** Approved

---

## Overview

Build the foundational DBPF 2.1 parser that all other S4LT modules depend on. This enables reading any Sims 4 .package file, listing contents, and extracting resources.

---

## Architecture

```
┌─────────────────────────────────────┐
│  High-Level API                     │
│  Package.open() → resources → data  │
├─────────────────────────────────────┤
│  Resource Type Handlers             │
│  Tuning, Texture, STBL, Thumbnail   │
├─────────────────────────────────────┤
│  Compression Layer                  │
│  RefPack, zlib, raw passthrough     │
├─────────────────────────────────────┤
│  Index Parser                       │
│  Flags → offsets → resource entries │
├─────────────────────────────────────┤
│  DBPF Reader                        │
│  Header parsing, file I/O           │
└─────────────────────────────────────┘
```

### Key Design Decisions

1. **Lazy loading** - Don't decompress resources until accessed. A package with 10,000 resources shouldn't load them all into memory.

2. **Streaming reads** - Use file seeks, not read() the entire file.

3. **Immutable by default** - Reading doesn't modify. Separate write path later.

4. **Type registry pattern** - Resource handlers registered by Type ID, so we can add new types without changing core code.

---

## File Structure

```
s4lt/
├── core/
│   ├── __init__.py
│   ├── dbpf.py          # Package class, main entry point
│   ├── header.py        # Header parsing
│   ├── index.py         # Index table parsing
│   ├── compression.py   # RefPack + zlib decompression
│   ├── resource.py      # Resource class
│   └── types.py         # Type ID registry and names
```

---

## DBPF Header Format (96 bytes)

| Offset | Size | Field |
|--------|------|-------|
| 0x00 | 4 | Magic "DBPF" |
| 0x04 | 4 | Major version (2) |
| 0x08 | 4 | Minor version (1) |
| 0x0C | 24 | Unknown/padding |
| 0x24 | 4 | Index entry count |
| 0x28 | 4 | Index offset location |
| 0x2C | 4 | Index size in bytes |
| 0x30 | 48 | More unknown/reserved |

---

## Index Format

### Index Header
- 4 bytes: Flags (which fields are constant vs per-entry)
- N x 4 bytes: Constant values for flagged fields

### Flag Bits
| Bit | Field |
|-----|-------|
| 0 | ResourceType |
| 1 | ResourceGroup |
| 2 | InstanceHi |
| 3 | InstanceLo |
| 4 | ChunkOffset |
| 5 | FileSize |
| 6 | MemSize |
| 7 | Compressed |

If a bit is SET, that field is constant for all entries (read once from header).
If a bit is CLEAR, that field is per-entry (read from each entry).

### Per Entry (up to 32 bytes when all fields present)
- Type ID (4 bytes) - What kind of resource
- Group ID (4 bytes) - Grouping/namespace
- Instance Hi (4 bytes) - Unique ID high bits
- Instance Lo (4 bytes) - Unique ID low bits
- Offset (4 bytes) - Where in file
- File Size (4 bytes) - Compressed size (bit 31 = extended compression info)
- Mem Size (4 bytes) - Uncompressed size
- Compressed (2 bytes) - Compression type indicator

---

## Compression Types

| Value | Type | Handler |
|-------|------|---------|
| 0x0000 | Uncompressed | Pass through |
| 0x5A42 | zlib | Python zlib.decompress() |
| 0xFFFF | RefPack | Custom implementation needed |
| 0xFFFE | RefPack | Alternative marker |

### RefPack Algorithm
EA's proprietary compression. LZ77-based with custom encoding:
- 2-byte header with flags
- Variable-length commands for literals and back-references
- Need to implement from scratch based on community documentation

---

## Common Resource Types

| Type ID | Name | Description |
|---------|------|-------------|
| 0x034AEECB | CAS Part | Create-a-Sim clothing/hair |
| 0x0333406C | XML Tuning | Game behavior definitions |
| 0x220557DA | String Table | Localized text |
| 0x00B2D882 | DDS Texture | DirectDraw Surface images |
| 0x3C1AF1F2 | PNG Thumbnail | Preview images |
| 0x015A1849 | Geometry | 3D mesh data |
| 0x00AE6C67 | Bone | Skeleton/rig data |
| 0xC0DB5AE7 | Catalog | Build/Buy catalog entry |

---

## Public API

```python
from s4lt.core import Package

# Open a package
pkg = Package.open("path/to/mod.package")

# Package info
print(pkg.version)        # (2, 1)
print(len(pkg.resources)) # 47

# Iterate resources
for resource in pkg.resources:
    print(f"Type: {resource.type_id:08X}")
    print(f"Type Name: {resource.type_name}")
    print(f"Group: {resource.group_id:08X}")
    print(f"Instance: {resource.instance_id:016X}")
    print(f"Compressed: {resource.is_compressed}")
    print(f"Size: {resource.compressed_size} -> {resource.uncompressed_size}")

# Extract a resource (decompresses on demand)
data = pkg.resources[0].extract()

# Find resources by type
tuning = pkg.find_by_type(0x0333406C)
cas_parts = pkg.find_by_type(0x034AEECB)

# Close when done
pkg.close()

# Context manager support
with Package.open("mod.package") as pkg:
    for r in pkg.resources:
        print(r)
```

---

## Error Handling

```python
class DBPFError(Exception):
    """Base exception for DBPF parsing errors"""

class InvalidMagicError(DBPFError):
    """File is not a valid DBPF archive"""

class UnsupportedVersionError(DBPFError):
    """DBPF version not supported (not 2.x)"""

class CompressionError(DBPFError):
    """Failed to decompress resource"""

class CorruptedIndexError(DBPFError):
    """Index table is corrupted or truncated"""
```

---

## Testing Strategy

1. **Unit tests** for each component:
   - Header parsing with known good/bad files
   - Index parsing with various flag combinations
   - Compression/decompression roundtrip
   - Resource type identification

2. **Integration tests** with real .package files:
   - Open and list resources
   - Extract and verify known content
   - Handle edge cases (empty packages, huge packages)

3. **Test files needed:**
   - Simple mod with few resources
   - Complex mod with many resource types
   - Corrupted package for error handling
   - Empty package

---

## Implementation Order

1. `types.py` - Resource type ID constants and names
2. `header.py` - Parse 96-byte header
3. `index.py` - Parse index table with flag handling
4. `resource.py` - Resource class with lazy extraction
5. `compression.py` - zlib first, then RefPack
6. `dbpf.py` - Package class tying it all together
7. CLI test script to verify against real files

---

## Next Steps After Phase 1

With the core engine complete, we can build:
- **Phase 2:** Mod Scanner - uses Package to crawl and index mods
- **Phase 3:** Tray Manager - uses Package to read tray files
- **Phase 6:** Package Editor - extends Package with write support
