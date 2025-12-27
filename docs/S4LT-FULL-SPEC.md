# S4LT: SIMS 4 LINUX TOOLKIT — FULL SPECIFICATION

A complete replacement for every Windows-only Sims 4 tool:
- Sims 4 Studio
- Tray Importer
- s4pe
- Mod Conflict Detector
- Sims 4 Mod Manager

Built native for Linux. First-class Steam Deck support. No Wine. No Proton.

---

## CORE MODULES

### 1. DBPF ENGINE (foundation)
```
core/
├── dbpf.py           # Read/write DBPF 2.1 format
├── compression.py    # RefPack + zlib decompression
├── resources.py      # Resource type registry
├── index.py          # Index table parser
└── types/
    ├── cas.py        # CAS part resources
    ├── tuning.py     # XML tuning
    ├── mesh.py       # 3D geometry
    ├── texture.py    # DDS/PNG textures
    ├── stbl.py       # String tables
    └── thumb.py      # Thumbnails
```

Capabilities:
- Open any .package file
- Parse header and index table
- Decompress resources
- Identify resource types by Type ID
- Extract individual resources
- Modify and repack
- Create new packages from scratch

### 2. MOD MANAGER
```
mods/
├── scanner.py        # Recursive folder scan
├── indexer.py        # Build mod database
├── hasher.py         # Generate file hashes
├── categorizer.py    # Auto-detect mod type
├── conflicts.py      # Resource collision detection
├── duplicates.py     # Find duplicate files
├── broken.py         # Detect corrupted packages
├── organizer.py      # Auto-sort into folders
├── toggler.py        # Enable/disable system
├── profiles.py       # Loadout management
└── cleaner.py        # Remove junk/orphans
```

Capabilities:
- Scan and index entire Mods folder
- Categorize: CAS, Build/Buy, Gameplay, Script, Tuning, Override
- Detect conflicts (two mods editing same resource)
- Find exact and near-duplicates
- Find corrupted/broken packages
- Auto-sort by type or creator
- Enable/disable without deleting
- Create loadout profiles (Gameplay, Screenshot, Building, Vanilla)
- One-click switch between profiles
- Broken mod detection against known database

### 3. TRAY MANAGER
```
tray/
├── reader.py         # Parse .tray files
├── browser.py        # Browse saved content
├── thumbnails.py     # Extract preview images
├── cc_tracker.py     # Find CC used in each item
├── missing.py        # Detect missing CC
├── exporter.py       # Export tray items
├── importer.py       # Import from others
├── bundler.py        # Package with CC included
└── gallery.py        # Gallery URL parser
```

Capabilities:
- Browse all Sims/Lots/Rooms with thumbnails
- Filter by type, size, tags
- Search by name
- List all CC used in each tray item
- Detect missing CC from Mods folder
- Export as .tray file
- Export with all CC bundled as .zip
- Import tray files from others
- Preview before importing
- Warn about missing CC
- Parse gallery URLs from metadata
- Find orphaned/duplicate tray items

### 4. PACKAGE EDITOR
```
packages/
├── viewer.py         # View package contents
├── previewer.py      # Preview resources
├── extractor.py      # Extract to files
├── editor.py         # Modify resources
├── creator.py        # Create new packages
├── merger.py         # Combine packages
├── splitter.py       # Split packages
└── optimizer.py      # Compress/clean packages
```

Capabilities:
- Open any .package and list contents
- Preview thumbnails and textures
- View XML tuning formatted
- View string tables
- Hex view for raw data
- Edit XML tuning directly
- Replace textures
- Edit string tables
- Extract any resource
- Batch extract by type
- Create new packages
- Merge multiple into one
- Split into logical chunks
- Optimize/compress

### 5. TUNING EDITOR
```
tuning/
├── browser.py        # Browse game tuning
├── indexer.py        # Index base game files
├── editor.py         # Visual tuning editor
├── override.py       # Generate override packages
└── presets.py        # Common tweak templates
```

Capabilities:
- Index all base game tuning
- Search by keyword
- Filter by category
- Visual editor for common values
- Generate override mods without coding

Quick Tweaks:
- Skill gain multiplier
- Relationship decay rate
- Need decay rate
- Pregnancy duration
- Aging speed per stage
- Career advancement speed
- Bill amounts
- Lot trait effects
- Autonomous behavior weights

### 6. SAVE MANAGER
```
saves/
├── browser.py        # List and view saves
├── metadata.py       # Extract save info
├── backup.py         # Backup system
├── restore.py        # Restore from backup
├── editor.py         # Edit save data
└── cleaner.py        # Remove corrupted saves
```

Capabilities:
- List all saves with metadata
- Show household/lot info
- Show in-game date and playtime
- One-click backup
- Scheduled auto-backup
- Versioned backups (keep last N)
- Sync to droplet/cloud
- Edit household funds
- Edit Sim skills/relationships
- Remove corrupted data
- Clean old autosaves

### 7. CC CREATOR TOOLS
```
creator/
├── batch.py          # Batch operations
├── thumbgen.py       # Thumbnail generator
├── validator.py      # Pre-release checks
├── packager.py       # Release packaging
└── manifest.py       # Generate documentation
```

Capabilities:
- Batch rename packages
- Add creator tags
- Update version numbers
- Generate clean thumbnails
- Custom thumbnail templates
- Conflict check against vanilla
- Conflict check against popular mods
- Package for release
- Generate readme/manifest

### 8. DIAGNOSTICS
```
diagnostics/
├── analyzer.py       # Mod impact analysis
├── logparser.py      # Parse LastException.txt
├── reporter.py       # Generate reports
└── fixer.py          # Auto-fix common issues
```

Capabilities:
- Estimate load time impact per mod
- Identify script-heavy mods
- Find resource-heavy mods
- Parse game error logs
- Explain errors in plain English
- Link errors to specific mods
- Suggest fixes
- Total mod/resource counts
- Disk space analysis
- RAM impact estimation

---

## USER INTERFACES

### CLI (Terminal)
```
cli/
├── main.py           # Entry point
├── commands/
│   ├── scan.py       # s4lt scan
│   ├── conflicts.py  # s4lt conflicts
│   ├── organize.py   # s4lt organize
│   ├── tray.py       # s4lt tray
│   ├── package.py    # s4lt package
│   ├── profile.py    # s4lt profile
│   └── backup.py     # s4lt backup
└── output.py         # Formatting/colors
```

Commands:
```bash
s4lt scan                    # Scan and index mods folder
s4lt conflicts               # Show all conflicts
s4lt duplicates              # Show duplicates
s4lt organize                # Auto-sort mods
s4lt profile list            # List loadout profiles
s4lt profile switch gaming   # Switch to profile
s4lt profile create minimal  # Create new profile
s4lt tray list               # List tray items
s4lt tray export "My Sim"    # Export tray item
s4lt package view mod.package # View package contents
s4lt backup create           # Backup saves
s4lt doctor                  # Run diagnostics
```

### Web UI
```
ui/web/
├── app.py            # FastAPI application
├── routes/
│   ├── dashboard.py
│   ├── mods.py
│   ├── tray.py
│   ├── packages.py
│   ├── saves.py
│   └── settings.py
├── static/
│   ├── css/
│   ├── js/
│   └── images/
└── templates/
    ├── base.html
    ├── dashboard.html
    ├── mods.html
    ├── tray.html
    └── packages.html
```

Features:
- Dashboard with stats overview
- Visual mod browser with thumbnails
- Drag-and-drop uploads
- Click-to-toggle mods
- Tray browser with previews
- Package viewer
- Profile switcher
- Works in Steam Deck browser
- Works from phone on same network
- Responsive/touch-friendly

### Native Desktop App (PyQt/GTK)
```
ui/desktop/
├── app.py            # Application entry
├── main_window.py    # Main window
├── panels/
│   ├── mods.py
│   ├── tray.py
│   ├── packages.py
│   └── saves.py
├── dialogs/
│   ├── conflict.py
│   ├── profile.py
│   └── settings.py
└── widgets/
    ├── mod_card.py
    ├── tray_card.py
    └── resource_tree.py
```

Features:
- Native Linux look and feel
- System tray icon
- File manager integration (right-click .package → Open with S4LT)
- Keyboard shortcuts
- Drag and drop
- Dark mode

---

## STEAM DECK SPECIFIC

### Game Mode Integration
```
deck/
├── launcher.py       # Steam shortcut generator
├── controller.py     # Controller navigation
├── overlay.py        # Quick access overlay
└── shortcuts.py      # Steam Input bindings
```

Features:
- Add S4LT to Steam as non-Steam game
- Controller-friendly UI (big buttons, D-pad navigation)
- Steam Input bindings for common actions
- Quick toggles from game mode
- Launch before Sims 4 for profile switching

### Storage Management
```
deck/storage/
├── analyzer.py       # Track internal vs SD usage
├── mover.py          # Move mods with symlinks
├── balancer.py       # Auto-balance storage
└── sync.py           # Sync between locations
```

Features:
- See what's on internal vs SD card
- Move mods to SD card (creates symlinks so game still finds them)
- Auto-balance based on available space
- Track which mods are where
- One-click "move all to SD"

### PC Sync
```
deck/sync/
├── client.py         # Deck-side sync
├── server.py         # PC/droplet-side sync
├── diff.py           # Calculate differences
└── transfer.py       # File transfer
```

Features:
- Sync mods between Deck and PC
- Sync tray items
- Sync save games
- Sync settings and profiles
- Runs on droplet as relay
- Works over local network or internet

---

## COMMUNITY FEATURES

### Mod Database
```
community/
├── database.py       # Community mod database client
├── broken.py         # Known broken mods list
├── conflicts.py      # Known conflict pairs
├── updates.py        # Update checker
└── recommendations.py # Mod recommendations
```

Features:
- Pull from community mod databases
- Check mods against known broken list
- Check for known conflicts
- Check for updates (if sources known)
- Get recommended mods by category
- Submit broken mod reports

### Sharing
```
community/sharing/
├── profiles.py       # Export/import loadout profiles
├── bundles.py        # Tray + CC bundles
├── lists.py          # Mod list export
└── publisher.py      # Publish to community
```

Features:
- Export loadout profile as shareable JSON
- Import someone else's profile
- Export tray item with all CC bundled
- Export mod list (with download links if known)
- Publish to community repository

---

## DATA STORAGE

### SQLite Database
```
db/
├── schema.py         # Database schema
├── mods.py           # Mods table operations
├── resources.py      # Resources table
├── tray.py           # Tray items table
├── profiles.py       # Profiles table
├── sources.py        # CC source URLs
└── cache.py          # Thumbnail cache
```

Tables:
- mods (path, hash, type, creator, date_added, enabled, profile)
- resources (mod_id, type_id, group_id, instance_id, name)
- conflicts (resource_id, mod_id_a, mod_id_b)
- tray_items (path, type, name, thumbnail, cc_list)
- profiles (name, enabled_mods, created, last_used)
- sources (mod_hash, url, creator, download_date)

---

## FILE PATHS

Steam Deck:
```
SIMS4_DOCS = /home/deck/.local/share/Steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4
MODS = {SIMS4_DOCS}/Mods
TRAY = {SIMS4_DOCS}/Tray
SAVES = {SIMS4_DOCS}/saves
```

Standard Linux (Lutris/Wine):
```
SIMS4_DOCS = ~/.wine/drive_c/users/{user}/Documents/Electronic Arts/The Sims 4
```

Config:
```
S4LT_CONFIG = ~/.config/s4lt/
S4LT_DATA = ~/.local/share/s4lt/
S4LT_CACHE = ~/.cache/s4lt/
```

---

## TECH STACK

- Python 3.11+
- SQLite (local database)
- FastAPI (web UI backend)
- HTMX + TailwindCSS (web UI frontend)
- PyQt6 or GTK4 (desktop app)
- Click (CLI framework)
- Pillow (image processing)
- struct (binary parsing)
- zlib (decompression)

---

## BUILD PHASES

### Phase 1: Core Engine
- [ ] DBPF reader (header, index, resources)
- [ ] Decompression (RefPack, zlib)
- [ ] Resource type identification
- [ ] Basic extraction

### Phase 2: Mod Scanner
- [ ] Folder crawler
- [ ] Package indexer
- [ ] SQLite database
- [ ] Conflict detection
- [ ] Duplicate detection
- [ ] CLI: scan, conflicts, duplicates

### Phase 3: Tray Manager
- [ ] Tray file parser
- [ ] Thumbnail extraction
- [ ] CC tracking
- [ ] Missing CC detection
- [ ] CLI: tray list, tray export

### Phase 4: Organization
- [ ] Auto-categorization
- [ ] Folder sorting
- [ ] Enable/disable system
- [ ] Profile management
- [ ] CLI: organize, profile

### Phase 5: Web UI
- [ ] FastAPI backend
- [ ] Dashboard
- [ ] Mod browser
- [ ] Tray browser
- [ ] Profile switcher

### Phase 6: Package Editor
- [ ] Resource viewer
- [ ] XML editor
- [ ] Texture preview
- [ ] String table editor
- [ ] Save modified packages

### Phase 7: Steam Deck
- [ ] Controller UI
- [ ] Storage manager
- [ ] Steam shortcut
- [ ] SD card symlinks

### Phase 8: Advanced
- [ ] Tuning editor
- [ ] Save editor
- [ ] Desktop app
- [ ] PC sync
- [ ] Community features
