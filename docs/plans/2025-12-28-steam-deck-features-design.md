# Steam Deck Features Design

## Overview

Steam Deck-specific features for S4LT: controller-friendly UI, SD card storage management, and Steam library integration.

**User Paths:**
- Mods: `/home/deck/.local/share/Steam/steamapps/compatdata/NonSteamLaunchers/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4/Mods/`
- SD Card: `/run/media/deck/[SD_CARD_NAME]/`

---

## Architecture

```
s4lt/
├── deck/
│   ├── __init__.py
│   ├── detection.py    # Detect if running on Steam Deck
│   ├── storage.py      # SD card detection, move/symlink operations
│   └── steam.py        # Add to Steam library, controller config
├── web/
│   ├── static/
│   │   └── deck.css    # Controller-friendly styles
│   └── templates/
│       └── components/
│           └── storage_widget.html  # Dashboard storage summary
```

**Detection Strategy:**
- Check for `/home/deck` user directory
- Check for Steam Deck hardware ID in `/sys/devices/virtual/dmi/id/`
- Detect SD cards at `/run/media/deck/*/` (or `/run/media/$USER/*` on desktop)

**Key Principle:** All features work on any Linux system, but Steam Deck gets automatic detection and sensible defaults.

---

## SD Card Storage Management

**Core Operations:**

```python
# s4lt/deck/storage.py

def list_removable_drives() -> list[RemovableDrive]
    # Returns mounted drives at /run/media/deck/*
    # Each drive has: name, path, total_size, free_space

def get_storage_summary(mods_path: Path, sd_path: Path | None) -> StorageSummary
    # Returns: internal_used, internal_free, sd_used, sd_free, symlink_count

def move_to_sd(mod_paths: list[Path], sd_mods_path: Path) -> MoveResult
    # 1. Create sd_mods_path/S4LT/ if not exists
    # 2. Move each file/folder to SD card
    # 3. Create symlink in original location pointing to SD
    # 4. Verify symlink works
    # Returns: success_count, failed_paths, space_freed

def move_to_internal(mod_paths: list[Path], mods_path: Path) -> MoveResult
    # 1. Resolve symlink to get SD location
    # 2. Remove symlink
    # 3. Move file back to internal
    # 4. Verify file exists
```

**Safety Features:**
- Never delete originals until move is verified
- Check destination has enough free space before starting
- Batch operations are atomic - if one fails, rollback all
- SD card must be mounted read-write

---

## Steam Integration

**CLI Commands:**

```bash
s4lt steam install    # Add S4LT to Steam library
s4lt steam uninstall  # Remove from Steam library
```

**What `s4lt steam install` does:**

1. Find Steam shortcuts file: `~/.steam/steam/userdata/<user_id>/config/shortcuts.vdf`
2. Create shortcut entry:
   - App Name: "S4LT - Sims 4 Linux Toolkit"
   - Exe: path to s4lt binary
   - Launch Options: `serve --open`
3. Add controller config: D-pad = arrows, A = Enter, B = Escape
4. Output: "Added S4LT to Steam library. Restart Steam to see it."

**Edge Cases:**
- Multiple Steam user IDs: prompt to choose or use most recent
- Already installed: update existing entry

---

## Controller-Friendly UI

**CSS Approach:**

```css
/* deck.css */
.deck-mode .btn { min-height: 64px; min-width: 64px; font-size: 1.25rem; }
.deck-mode *:focus { outline: 3px solid #60a5fa; outline-offset: 2px; }
.deck-mode .card { padding: 1.5rem; margin-bottom: 1rem; }
```

**D-pad Navigation:**
- Add `tabindex` to interactive elements in logical order
- Arrow keys move focus (native browser behavior)
- Enter/Space activates focused element
- No custom JavaScript needed

**Detection & Toggle:**
- Auto-detect Steam Deck on first visit, set cookie
- `<body class="deck-mode">` when enabled
- Manual toggle in Settings for desktop users who want larger UI

---

## Storage Dashboard & Move UI

**Dashboard Widget:**

```
┌─────────────────────────────────────────┐
│ Storage                                 │
├─────────────────────────────────────────┤
│ Internal:  12.3 GB mods  (45 GB free)   │
│ SD Card:    8.1 GB mods  (89 GB free)   │
│                                         │
│ [Manage Storage →]                      │
└─────────────────────────────────────────┘
```

**Manage Storage Page (`/storage`):**
- List mods on internal, sorted by size
- Checkbox selection for batch moves
- "Move to SD Card" button
- List mods on SD card with 🔗 symlink indicator
- "Move to Internal" button
- Progress toast during moves

---

## Error Handling

**SD Card Not Mounted:**
- Dashboard: "No SD card detected"
- Manage Storage still shows internal only
- Helpful message about inserting SD card

**SD Card Removed While Mods Symlinked:**
- Startup check for broken symlinks
- Warning banner: "⚠️ 3 mods unavailable - SD card not mounted"
- Link to affected mods list

**Not Enough Space:**
- Check before starting move
- Clear error: "Need 2.1 GB, only 1.8 GB free"

**Move Interrupted:**
- Detect orphaned files on SD without symlinks
- Offer to complete or restore

**Permissions:**
- Read-only SD card: clear error message
- No symlink support (FAT32): recommend ext4/btrfs

---

## Scope

**In:**
- `s4lt/deck/` module
- Controller-friendly CSS
- Storage widget + manage page
- `s4lt steam install/uninstall`
- Symlink health checking

**Out (YAGNI):**
- Auto-moving based on usage patterns
- Auto profile switching on SD insert/remove
- Custom Steam Input layouts
- SD card formatting tools

**CLI Commands:**
```bash
s4lt steam install
s4lt steam uninstall
s4lt storage
s4lt storage move <path> --to-sd
s4lt storage move <path> --to-internal
```

**Testing:**
- Mock `/run/media/deck/` for SD card tests
- Mock Steam shortcuts.vdf parsing
- Test symlink creation/resolution
- Test storage calculations
