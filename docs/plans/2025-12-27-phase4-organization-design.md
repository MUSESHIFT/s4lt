# Phase 4: Organization - Design Document

**Date:** 2025-12-27
**Version:** 0.4.0
**Status:** Approved

## Overview

Phase 4 adds mod organization capabilities to S4LT: automatic categorization, folder sorting, enable/disable toggling, and profile management for switching between mod configurations.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Categorization | Primary resource type | Leverages existing DBPF parsing |
| Enable/Disable | Rename suffix (.disabled) | Simple, visible, reversible |
| Profile storage | SQLite database | Fast queries, existing infrastructure |
| Organize behavior | Move files with confirmation | Safe, user sees changes first |
| Category assignment | Majority wins + priority tiebreaker | Handles mixed mods deterministically |
| Vanilla mode | Auto-backup profile with toggle | One-click but safe |
| Batch operations | Pattern-based (glob, category, creator) | Covers 90% of use cases |
| Creator detection | Filename parsing with fuzzy grouping | Pragmatic, works with conventions |

## Module Structure

### New Module: `s4lt/organize/`

```
s4lt/organize/
├── __init__.py
├── categorizer.py    # Mod category detection
├── sorter.py         # File organization operations
├── profiles.py       # Profile CRUD operations
├── batch.py          # Batch enable/disable logic
└── exceptions.py     # Organization-specific errors
```

### Database Schema Additions

```sql
-- New tables
CREATE TABLE profiles (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_auto BOOLEAN DEFAULT FALSE
);

CREATE TABLE profile_mods (
    id INTEGER PRIMARY KEY,
    profile_id INTEGER NOT NULL,
    mod_path TEXT NOT NULL,
    enabled BOOLEAN NOT NULL,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);

-- New column on existing mods table
ALTER TABLE mods ADD COLUMN category TEXT;
```

### CLI Commands

```
s4lt/cli/commands/
├── organize.py    # organize command
├── toggle.py      # enable, disable, vanilla commands
└── profile.py     # profile subcommands
```

## Categorization System

### Categories

| Category | Description | Primary Resource Types |
|----------|-------------|----------------------|
| CAS | Create-a-Sim content | CASPart (0x034AEECB) |
| BuildBuy | Build/Buy objects | ObjectDefinition (0x319E4F1D) |
| Script | Python script mods | Python bytecode (0x9C07855E) |
| Tuning | XML tuning mods | Tuning XML (0x03B33DDF) |
| Override | EA content replacements | Resources matching EA TGIs |
| Gameplay | Mixed gameplay mods | Combination of tuning + objects |
| Unknown | Unclassifiable | No recognized resources |

### Priority Hierarchy (for tiebreakers)

```python
CATEGORY_PRIORITY = {
    ModCategory.SCRIPT: 100,      # Scripts always win
    ModCategory.CAS: 80,
    ModCategory.BUILD_BUY: 70,
    ModCategory.OVERRIDE: 60,
    ModCategory.GAMEPLAY: 50,
    ModCategory.TUNING: 40,
    ModCategory.UNKNOWN: 0,
}
```

### Algorithm

1. Query `resources` table for mod's resource types
2. Count resources per category using type-to-category mapping
3. Pick category with highest count
4. On tie, use priority hierarchy to break
5. If >50% of resources match EA base game TGIs, classify as Override
6. Cache result in `mods.category` column

## Enable/Disable Mechanism

### File Operations

```python
def disable_mod(mod_path: Path) -> bool:
    """Rename .package → .package.disabled"""
    if mod_path.suffix == '.package':
        new_path = mod_path.with_suffix('.package.disabled')
        mod_path.rename(new_path)
        return True
    return False

def enable_mod(mod_path: Path) -> bool:
    """Rename .package.disabled → .package"""
    if mod_path.suffix == '.disabled':
        new_path = mod_path.with_suffix('')
        mod_path.rename(new_path)
        return True
    return False
```

### Behavior

- Operations are idempotent (enabling an enabled mod is a no-op)
- Sims 4 ignores non-.package extensions, so disabled mods are invisible to the game
- Mods stay in their original location for easy visibility

## Profile System

### Operations

| Command | Behavior |
|---------|----------|
| `profile create <name>` | Snapshot current enabled/disabled state |
| `profile switch <name>` | Apply stored state to filesystem |
| `profile list` | Show all profiles with mod counts |
| `profile delete <name>` | Remove profile |

### Vanilla Mode

Toggle behavior with automatic backup:

```
[Normal State] ──s4lt vanilla──> [Vanilla State]
      ^                                │
      └────s4lt vanilla (restore)──────┘
```

1. First `s4lt vanilla`: Save current state as `_pre_vanilla`, disable all mods
2. Second `s4lt vanilla`: Restore `_pre_vanilla` profile, delete it
3. State tracked via existence of `_pre_vanilla` profile

### Profile Switching Logic

```python
def switch_profile(name: str) -> SwitchResult:
    profile = get_profile(name)
    enabled_count = 0
    disabled_count = 0

    for mod in profile.mods:
        if mod.enabled:
            if enable_mod(mod.path):
                enabled_count += 1
        else:
            if disable_mod(mod.path):
                disabled_count += 1

    # Disable mods not in profile (new mods added after profile creation)
    for mod in get_mods_not_in_profile(profile):
        disable_mod(mod.path)
        disabled_count += 1

    return SwitchResult(enabled=enabled_count, disabled=disabled_count)
```

## Organize Operations

### By Type

```bash
$ s4lt organize --by-type
Analyzing 47 mods...

Will organize into:
  → CAS/: 23 mods
  → BuildBuy/: 12 mods
  → Gameplay/: 8 mods
  → Script/: 4 mods

Proceed? [y/N] y

Organized 47 mods into 4 folders.
```

### By Creator

```bash
$ s4lt organize --by-creator
Analyzing 47 mods...

Will organize into:
  → SimsyCreator/: 15 mods
  → Basemental/: 8 mods
  → LittleMsSam/: 12 mods
  → _Uncategorized/: 12 mods

Proceed? [y/N]
```

### Creator Extraction

```python
def extract_creator(filename: str) -> str:
    """Parse creator from filename prefix"""
    patterns = [
        r'^([A-Za-z0-9]+)_',           # SimsyCreator_Hair.package
        r'^TS4[-_]([A-Za-z0-9]+)[-_]', # TS4-Bobby-Dress.package
        r'^([A-Za-z0-9]+)-',           # Creator-ModName.package
    ]
    for pattern in patterns:
        if match := re.match(pattern, filename):
            return normalize_creator(match.group(1))
    return "_Uncategorized"

def normalize_creator(name: str) -> str:
    """Fuzzy grouping of similar names"""
    # Lowercase comparison, common variations
    # "Simsy", "SimsyCreator", "simsy_" → "Simsy"
    return name.title()
```

### Safety Features

- Always show preview first (dry-run by default)
- Require explicit confirmation or `--yes` flag
- Update database paths after moves
- Handle .disabled files correctly

## Batch Operations

### Filters

| Filter | Example | Behavior |
|--------|---------|----------|
| Glob pattern | `"CAS/*"` | Match mod paths |
| Category | `--category Script` | Filter by detected category |
| Creator | `--creator Simsy` | Parse filename, match creator |

### CLI Examples

```bash
# By glob pattern
s4lt enable "CAS/*"
s4lt disable "*/WickedWhims*"

# By category
s4lt enable --category BuildBuy
s4lt disable --category Script

# By creator
s4lt enable --creator Simsy
s4lt disable --creator "BrokenCreator"

# Combined filters (AND logic)
s4lt disable --category CAS --creator BrokenCreator
```

## CLI Command Reference

### organize

```bash
s4lt organize [OPTIONS]

Options:
  --by-type      Sort mods into category subfolders
  --by-creator   Sort mods into creator subfolders
  --yes, -y      Skip confirmation prompt
```

### enable / disable

```bash
s4lt enable [MOD] [OPTIONS]
s4lt disable [MOD] [OPTIONS]

Arguments:
  MOD            Mod name, path, or glob pattern

Options:
  --category     Filter by category (CAS, BuildBuy, Script, etc.)
  --creator      Filter by creator name
```

### vanilla

```bash
s4lt vanilla

Toggle vanilla mode. First call disables all mods and saves state.
Second call restores previous state.
```

### profile

```bash
s4lt profile list                 Show all profiles
s4lt profile create <name>        Save current config as profile
s4lt profile switch <name>        Switch to profile
s4lt profile delete <name>        Delete profile
```

## Testing Strategy

### Test Files

```
tests/organize/
├── test_categorizer.py   # Category detection logic
├── test_sorter.py        # Organize operations
├── test_profiles.py      # Profile CRUD + switching
├── test_batch.py         # Batch enable/disable
└── test_cli_organize.py  # CLI integration
```

### Key Test Scenarios

**Categorization:**
- CAS mod detected (majority CASPart resources)
- Script wins tie (priority tiebreaker)
- Override detection (EA TGI match)
- Mixed mod categorization

**Enable/Disable:**
- Disable renames file correctly
- Enable restores file correctly
- Already enabled/disabled is no-op (idempotent)

**Profiles:**
- Create profile snapshots current state
- Switch profile applies state correctly
- Vanilla toggle creates and restores _pre_vanilla
- Delete profile removes data

**Organize:**
- Organize by type moves files to correct folders
- Organize preserves .disabled extension
- Dry-run makes no changes
- Confirmation required without --yes

**Batch:**
- Glob pattern matching works
- Category filter works
- Creator filter works
- Combined filters use AND logic

### Test Fixtures

- Temporary directory with mock .package files
- Seeded database with mod records
- Mock .package.disabled files for toggle tests

## Implementation Order

1. **Database schema** - Add tables and column
2. **Categorizer** - Resource type analysis + caching
3. **Enable/Disable** - File rename operations
4. **Profiles** - CRUD + switch logic
5. **Vanilla mode** - Toggle with auto-backup
6. **Organize** - Sort operations with confirmation
7. **Batch** - Pattern and filter support
8. **CLI commands** - Wire up all commands
9. **Tests** - Full coverage for all features

## User's Mods Path

```
/home/deck/.local/share/Steam/steamapps/compatdata/NonSteamLaunchers/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4/Mods/
```

## Success Criteria

- [ ] `s4lt organize --by-type` sorts mods into category folders
- [ ] `s4lt organize --by-creator` sorts mods by creator
- [ ] `s4lt enable/disable` toggles individual mods
- [ ] `s4lt profile create/switch/list/delete` manages profiles
- [ ] `s4lt vanilla` toggles vanilla mode with auto-restore
- [ ] Batch operations support glob, category, and creator filters
- [ ] All operations are safe (confirmation prompts, idempotent)
- [ ] 100% test coverage for new code
