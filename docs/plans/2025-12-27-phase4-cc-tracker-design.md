# Phase 4: CC Tracking & Missing CC Detection - Design

## Goal

For any tray item (Sim, lot, room), identify which CC it uses and detect missing CC.

## Architecture

### Two-Index System

```
┌─────────────────┐     ┌──────────────────┐
│  EA Index       │     │  Mods Index      │
│  (base game)    │     │  (Phase 2)       │
│                 │     │                  │
│  ~/.local/share │     │  ~/.local/share  │
│  /s4lt/ea.db    │     │  /s4lt/s4lt.db   │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │ TGI Lookup  │
              │             │
              │ tray file → │
              │ extract TGIs│
              │ → classify  │
              └─────────────┘
```

### Classification Logic

- TGI in EA Index → Base game content (ignore)
- TGI in Mods Index → CC (report which mod)
- TGI in neither → Missing CC (warn user)

### New Files

```
s4lt/
├── ea/
│   ├── __init__.py
│   ├── scanner.py      # Scan game install folder
│   ├── index.py        # EA index database operations
│   └── paths.py        # Game install path detection
├── tray/
│   ├── cc_tracker.py   # TGI extraction from tray binaries
│   └── missing.py      # Missing CC detection logic
```

---

## EA Content Index

### Database Schema (ea.db)

```sql
CREATE TABLE ea_resources (
    instance_id INTEGER PRIMARY KEY,  -- 64-bit Instance ID
    type_id INTEGER NOT NULL,         -- 32-bit Type ID
    group_id INTEGER NOT NULL,        -- 32-bit Group ID
    package_name TEXT NOT NULL,       -- e.g., "SimulationFullBuild0.package"
    pack TEXT                         -- "BaseGame", "EP01", "GP05", etc.
);

CREATE TABLE ea_scan_info (
    id INTEGER PRIMARY KEY,
    game_path TEXT NOT NULL,
    last_scan TEXT NOT NULL,          -- ISO timestamp
    package_count INTEGER,
    resource_count INTEGER
);
```

### Game Install Path Detection

```python
EA_SEARCH_PATHS = [
    # NonSteamLaunchers (Steam Deck)
    "~/.local/share/Steam/steamapps/compatdata/NonSteamLaunchers/pfx/drive_c/Program Files/EA Games/The Sims 4/",
    # Standard Steam Proton
    "~/.steam/steam/steamapps/common/The Sims 4/",
    "~/.local/share/Steam/steamapps/common/The Sims 4/",
    # Flatpak Steam
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/common/The Sims 4/",
    # Lutris/Wine
    "~/Games/the-sims-4/drive_c/Program Files/EA Games/The Sims 4/",
]

def find_game_folder() -> Path | None:
    """Find game install. Try known paths, then filesystem search."""
    # 1. Check configured path
    # 2. Try EA_SEARCH_PATHS
    # 3. Fallback: find ClientFullBuild0.package
    result = subprocess.run(
        ["find", str(Path.home()), "-name", "ClientFullBuild0.package", "-type", "f"],
        capture_output=True, text=True, timeout=60
    )
    # Parse result, derive game folder from package path
```

**Validation:** Confirm valid install by checking for `Data/Client/ClientFullBuild0.package`.

### Packages to Index

- `Data/Client/*.package` - Core game data
- `Data/Simulation/*.package` - Gameplay content
- `EP*/`, `GP*/`, `SP*/`, `FP*/` - Expansion/Game/Stuff/Free packs

**Index Size Estimate:** ~2-3 million TGIs, ~100-200MB database

---

## TGI Extraction from Tray Files

### Approach

Reference s4pe/s4pi C# source for format details, implement Python parser.

### Key Binary Structures

```python
# TGI format in tray files (16 bytes)
struct TGI:
    type_id: uint32      # Resource type
    group_id: uint32     # Resource group
    instance_id: uint64  # Resource instance

# Common resource types we care about:
CAS_PART = 0x034AEECB        # Hair, clothes, accessories
OBJECT_DEF = 0x319E4F1D      # Build/buy objects
TEXTURE = 0x00B2D882         # DDS textures
```

### New Module: `s4lt/tray/cc_tracker.py`

```python
@dataclass
class CCReference:
    tgi: tuple[int, int, int]  # (type, group, instance)
    source: str                 # "ea", "mod:<path>", "missing"
    mod_path: Path | None       # If from mods folder

def extract_tgis(tray_item: TrayItem) -> list[tuple[int, int, int]]:
    """Extract all TGI references from a tray item's binary files."""

def classify_tgis(tgis: list, ea_db: Connection, mods_db: Connection) -> list[CCReference]:
    """Classify each TGI as base game, CC, or missing."""

def get_cc_summary(tray_item: TrayItem) -> dict:
    """Return mod-centric summary: {mod_path: [tgis...], 'missing': [tgis...]}"""
```

---

## CLI Integration

### 1. Enhanced `s4lt tray info`

```
$ s4lt tray info "Smith Family"

Smith Family
  Type: household
  ID: 0x0000000012345678
  Files: 5

CC Usage:
  3 items from CoolCreator_Hair.package
  2 items from BodyPresets.package
  1 item from EyeColors.package
  ⚠ 2 missing CC items
```

### 2. Enhanced `s4lt tray list`

```
$ s4lt tray list --cc

Households (3)
  Smith Family (6 CC, 0 missing)
  Jones Family (12 CC, 2 missing) ⚠
  Test Sim (0 CC)
```

### 3. New `s4lt tray cc` command

```
$ s4lt tray cc "Smith Family" --json

$ s4lt tray cc "Smith Family" --verbose
# Shows every TGI with full details

$ s4lt tray cc --missing
# List all tray items with missing CC

$ s4lt tray cc --by-mod CoolCreator_Hair.package
# Show all tray items using this mod
```

### 4. New `s4lt ea scan` command

```
$ s4lt ea scan
Scanning game folder: /home/deck/.../The Sims 4/
Found 847 packages...
Indexed 2,341,892 resources
Saved to ~/.local/share/s4lt/ea.db
```

---

## Error Handling & Edge Cases

### Missing EA Index

```
$ s4lt tray cc "Smith Family"
⚠ EA content not indexed. Run 's4lt ea scan' first.
  (Without EA index, all non-mod TGIs will show as "unknown")

Continue anyway? [y/N]
```

### Game folder not found

```
$ s4lt ea scan
Could not auto-detect game install folder.
Enter path to The Sims 4 folder: /path/to/game
```

### Corrupt tray files

- Log warning, skip file, continue with others
- `--strict` flag to fail on any parse error

### Large tray folders

- Progress bar during scan
- Cache CC analysis results in database (invalidate when tray file modified)

### Edge Cases

- **Merged packages:** One .package contains multiple creators' content → show package name, not "creator"
- **Renamed packages:** User renamed mod file → still works (we index by TGI, not filename)
- **Deleted mods:** Was in index, now file missing → "missing mod" vs "missing CC" distinction
- **Override mods:** Same TGI in multiple mods → report first match, note conflict

### Performance Targets

- EA scan: < 5 minutes (one-time)
- CC lookup per tray item: < 1 second
- Full tray folder scan: < 30 seconds for 100 items

---

## Dependencies

- **Phase 2 (Mods Index):** Uses existing `resources` table for TGI lookups
- **Phase 3 (Tray Manager):** Extends `TrayItem` class with CC tracking methods
- **s4pe/s4pi:** Reference C# source for binary format parsing
