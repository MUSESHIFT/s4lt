# Phase 2 Design: Mod Scanner

## Overview

The Mod Scanner builds on Phase 1's DBPF engine to provide:
- Recursive folder scanning of Mods directory
- Full resource indexing with human-readable name extraction
- SQLite database for fast queries and caching
- Conflict detection grouped into clusters
- Content-based duplicate detection
- Rich CLI with machine-readable output options

## Architecture

```
s4lt/
├── core/               # Phase 1 (done)
├── mods/               # Phase 2
│   ├── __init__.py
│   ├── scanner.py      # Folder crawler, file discovery
│   ├── indexer.py      # Parse packages, extract metadata
│   ├── conflicts.py    # Conflict cluster detection
│   ├── duplicates.py   # Content-based duplicate finder
│   └── paths.py        # Platform path detection
├── db/
│   ├── __init__.py
│   ├── schema.py       # SQLite schema definition
│   ├── connection.py   # DB connection management
│   └── queries.py      # Common queries
├── cli/
│   ├── __init__.py
│   ├── main.py         # Click app entry point
│   ├── scan.py         # s4lt scan
│   ├── conflicts.py    # s4lt conflicts
│   ├── duplicates.py   # s4lt duplicates
│   └── output.py       # Rich formatting helpers
└── config/
    ├── __init__.py
    └── settings.py     # User config (paths, preferences)
```

**Data flow:**
1. `scanner.py` walks the Mods folder, finds `.package` files
2. For each file, check DB - skip if unchanged (same mtime/size)
3. Changed files go to `indexer.py` which uses `core.Package` to extract all resources
4. Resources stored in SQLite with TGI + extracted names
5. `conflicts.py` queries DB to find TGI collisions, groups into clusters
6. `duplicates.py` compares resource sets to find content-identical packages

## Database Schema

SQLite database at `~/.local/share/s4lt/s4lt.db`:

```sql
-- Mod packages
CREATE TABLE mods (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,      -- Relative to Mods folder
    filename TEXT NOT NULL,         -- Just the filename
    size INTEGER NOT NULL,          -- Bytes
    mtime REAL NOT NULL,            -- Last modified timestamp
    hash TEXT NOT NULL,             -- SHA256 of file
    resource_count INTEGER,         -- Number of resources
    scan_time REAL,                 -- When we indexed it
    broken INTEGER DEFAULT 0        -- 1 if failed to parse
);

-- Resources inside packages
CREATE TABLE resources (
    id INTEGER PRIMARY KEY,
    mod_id INTEGER NOT NULL REFERENCES mods(id) ON DELETE CASCADE,
    type_id INTEGER NOT NULL,       -- Resource type
    group_id INTEGER NOT NULL,      -- Resource group
    instance_id INTEGER NOT NULL,   -- Resource instance (64-bit)
    type_name TEXT,                 -- "Tuning", "CASPart", etc.
    name TEXT,                      -- Extracted human name (from XML)
    compressed_size INTEGER,
    uncompressed_size INTEGER
);

-- Indexes for fast conflict/duplicate queries
CREATE INDEX idx_resources_tgi ON resources(type_id, group_id, instance_id);
CREATE INDEX idx_resources_mod ON resources(mod_id);
CREATE INDEX idx_mods_hash ON mods(hash);

-- Config storage
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

**Key design choices:**
- Paths stored relative to Mods folder (portable if folder moves)
- `mtime` + `size` for quick change detection before hashing
- `hash` for exact duplicate detection
- `broken` flag for packages that fail to parse (logged, skipped)
- Cascade delete: removing a mod removes all its resources

## Path Detection

Auto-detect Mods folder by checking common locations in order:

```python
SEARCH_PATHS = [
    # Steam Deck (NonSteamLauncher / Proton)
    "~/.local/share/Steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4",

    # Standard Steam Proton
    "~/.steam/steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4",

    # Flatpak Steam
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4",

    # Lutris / Wine
    "~/.wine/drive_c/users/{user}/Documents/Electronic Arts/The Sims 4",

    # Custom Wine prefix (check common names)
    "~/Games/the-sims-4/drive_c/users/{user}/Documents/Electronic Arts/The Sims 4",
]
```

**First-run flow:**
1. Check each path, expand `~` and `{user}`
2. Look for `Mods/` subfolder existing
3. If found, show: `Found Mods folder: /path/to/Mods (847 files). Use this? [Y/n]`
4. If multiple found, present choice
5. If none found, prompt for manual path
6. Save to `~/.config/s4lt/config.toml`

**Config file format:**
```toml
[paths]
mods = "/home/deck/.local/share/Steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4/Mods"
# tray = "..."  # Future phases
# saves = "..." # Future phases

[scan]
include_subfolders = true
ignore_patterns = ["__MACOSX", ".DS_Store", "*.disabled"]
```

## Conflict Detection

Conflicts are TGI collisions grouped into clusters:

```python
@dataclass
class ConflictCluster:
    mods: list[str]              # Paths of conflicting mods
    resources: list[ResourceTGI] # Shared TGI values
    resource_types: set[str]     # "Tuning", "CASPart", etc.
    severity: str                # "low", "medium", "high"
```

**Severity levels:**
- **High**: Same CASPart, Mesh, or Texture (visual breakage likely)
- **Medium**: Same Tuning or SimData (gameplay changes may conflict)
- **Low**: Same StringTable or Thumbnail (usually safe, last-loaded wins)

**Detection algorithm:**
1. Query: `SELECT type_id, group_id, instance_id, COUNT(DISTINCT mod_id) as mod_count FROM resources GROUP BY type_id, group_id, instance_id HAVING mod_count > 1`
2. For each collision, get the list of mods involved
3. Build graph: mods as nodes, shared resources as edges
4. Find connected components = conflict clusters
5. Calculate severity based on resource types in cluster

**Output example:**
```
⚠️  Conflict Cluster #1 (HIGH) - 2 mods, 3 resources
   ├── SimsyGirl_CoolHair.package
   └── AnotherCreator_HairRetexture.package
   Shared: CASPart, Geometry, Thumbnail

ℹ️  Conflict Cluster #2 (LOW) - 3 mods, 1 resource
   ├── ModA.package
   ├── ModB.package
   └── ModC.package
   Shared: StringTable
```

## Duplicate Detection

Three-tier duplicate detection from fast to thorough:

**Tier 1: Exact duplicates (same hash)**
```sql
SELECT hash, GROUP_CONCAT(path) as paths, COUNT(*) as count
FROM mods GROUP BY hash HAVING count > 1
```
Instant - just a DB query. Catches byte-for-byte identical files.

**Tier 2: Renamed duplicates (same hash, different name)**
Same as Tier 1, but highlights when filenames differ.

**Tier 3: Content duplicates (same resources inside)**
```python
# For each mod, create a "resource fingerprint"
# = sorted tuple of (type_id, group_id, instance_id)
# Mods with identical fingerprints are content duplicates

def get_resource_fingerprint(mod_id: int) -> tuple:
    resources = db.query(
        "SELECT type_id, group_id, instance_id FROM resources WHERE mod_id = ? ORDER BY type_id, group_id, instance_id",
        mod_id
    )
    return tuple(resources)
```

This catches:
- Re-exported packages (same CC, different wrapper)
- Merged then re-split packages
- Packages from different sources containing same CC

**Output example:**
```
📦 Duplicate Group #1 - Exact match (3 files, wasting 2.4 MB)
   ├── Mods/Hair/CoolHair.package (KEEP - oldest)
   ├── Mods/CoolHair_backup.package (delete?)
   └── Mods/New CC/CoolHair.package (delete?)

📦 Duplicate Group #2 - Same content, different package
   ├── CreatorA_Dress.package (847 KB)
   └── CreatorB_Reupload.package (923 KB, larger wrapper)
```

## CLI Commands

Using Click for the CLI framework:

**`s4lt scan`** - Index the Mods folder
```bash
s4lt scan              # Full scan (first run) or incremental update
s4lt scan --full       # Force full rescan, ignore cache
s4lt scan --stats      # Just show stats, don't update
```

Output:
```
🔍 Scanning /home/deck/.../Mods
   Found 1,247 packages (3 new, 2 modified, 1 deleted)

   Indexing... ████████████████████████ 100% (5/5)

✅ Scan complete
   Total: 1,247 mods (142,839 resources)
   New: 3 | Updated: 2 | Removed: 1 | Broken: 0
   Time: 4.2s
```

**`s4lt conflicts`** - Show conflict clusters
```bash
s4lt conflicts            # Show all conflicts
s4lt conflicts --high     # Only high severity
s4lt conflicts --json     # Machine-readable output
```

**`s4lt duplicates`** - Find duplicates
```bash
s4lt duplicates           # Show all duplicates
s4lt duplicates --exact   # Only exact hash matches
s4lt duplicates --waste   # Sort by wasted disk space
```

**`s4lt info <package>`** - Show package details
```bash
s4lt info CoolHair.package
```
```
📦 CoolHair.package
   Path: Mods/Hair/CoolHair.package
   Size: 1.2 MB
   Resources: 12

   Contents:
   ├── CASPart (1)
   ├── Geometry (2)
   ├── Tuning (3) - "coolhair_CASPart", "coolhair_Outfit"...
   ├── Thumbnail (4)
   └── StringTable (2)

   Conflicts with: HairRetexture.package (3 resources)
```

## Name Extraction from Tuning

Tuning resources are XML that contain human-readable names:

```xml
<?xml version="1.0" encoding="utf-8"?>
<I c="CASPart" i="cas_part" m="sims4.cas.cas_part" n="coolhair_EP01" s="12345678901234567">
  <T n="display_name">Cool Wavy Hair</T>
  ...
</I>
```

**Extraction strategy:**
```python
def extract_name(resource: Resource) -> str | None:
    if resource.type_name != "Tuning":
        return None

    try:
        data = resource.extract()
        if not data.startswith(b'<?xml'):
            return None

        root = ET.fromstring(data)

        # Try common name attributes/elements
        if name := root.get('n'):
            return name

        for elem in root.iter('T'):
            if elem.get('n') in ('display_name', 'name'):
                return elem.text

        return root.get('s')

    except Exception:
        return None
```

## Incremental Scanning

```python
def needs_reindex(path: Path, db_record: ModRecord | None) -> bool:
    if db_record is None:
        return True  # New file

    stat = path.stat()
    if stat.st_mtime != db_record.mtime:
        return True
    if stat.st_size != db_record.size:
        return True

    return False  # Unchanged

def scan_folder(mods_path: Path, full: bool = False):
    disk_files = set(mods_path.rglob("*.package"))
    db_files = {Path(r.path) for r in db.get_all_mods()}

    new_files = disk_files - db_files
    deleted_files = db_files - disk_files
    existing_files = disk_files & db_files
    modified_files = [f for f in existing_files if needs_reindex(f, db.get_mod(f))]

    for f in deleted_files:
        db.delete_mod(f)

    for f in new_files | modified_files:
        index_package(f)
```

## Error Handling

```python
def index_package(path: Path):
    try:
        with Package.open(path) as pkg:
            mod_id = db.upsert_mod(path, pkg)
            for resource in pkg.resources:
                name = extract_name(resource)
                db.insert_resource(mod_id, resource, name)

    except DBPFError as e:
        db.mark_broken(path, str(e))
        log.warning(f"Failed to parse {path.name}: {e}")

    except Exception as e:
        log.error(f"Unexpected error on {path.name}: {e}")
```

**Broken package tracking:**
- Stored in DB with `broken=1` and error message
- `s4lt scan` reports count of broken packages
- `s4lt broken` command lists them with error details

## Dependencies

New dependencies for Phase 2:
- `click` - CLI framework
- `rich` - Terminal formatting, progress bars
- `tomli` / `tomllib` - Config file parsing (stdlib in 3.11+)

## Summary

Phase 2 delivers:
- Full Mods folder indexing with incremental updates
- Human-readable names extracted from tuning XML
- Conflict clusters with severity levels
- Content-based duplicate detection
- Rich CLI: `scan`, `conflicts`, `duplicates`, `info`
- SQLite caching for fast subsequent operations
