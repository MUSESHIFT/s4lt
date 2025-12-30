# S4LT: Sims 4 Linux Toolkit

Native Linux mod manager for The Sims 4. Built for Steam Deck and desktop Linux.

**No terminal required. Just click and play.**

## Features

- **Auto-detect Mods folder** - Works with Steam, NonSteamLaunchers, Heroic, Lutris
- **Smart categorization** - Automatically sorts mods into Script Mods, CAS CC, Build/Buy CC, Tuning
- **Enable/Disable mods** - Toggle switches, no renaming files manually
- **Vanilla Mode** - One click to disable all mods for testing
- **Mod Profiles** - Save and switch between different mod configurations
- **Conflict Detection** - Find mods that override the same resources
- **Tray Manager** - Browse your saved Sims and Lots
- **Steam Deck optimized** - Touch-friendly UI, SD card support

## Install (Steam Deck)

1. Download `S4LT-0.8.0-x86_64.AppImage` from [Releases](../../releases)
2. Move to your home folder
3. Right-click → Properties → Permissions → Allow executing as program
4. Double-click to run

**That's it!** S4LT will auto-detect your mods folder.

## Install (Desktop Linux)

### AppImage (Recommended)
```bash
wget https://github.com/YOUR_USERNAME/s4lt/releases/download/v0.8.0/S4LT-0.8.0-x86_64.AppImage
chmod +x S4LT-0.8.0-x86_64.AppImage
./S4LT-0.8.0-x86_64.AppImage
```

### From Source
```bash
git clone https://github.com/YOUR_USERNAME/s4lt.git
cd s4lt
pip install -e .
s4lt-desktop  # Launch GUI
s4lt --help   # CLI
```

## Screenshots

*Coming soon*

## Mod Categories

S4LT automatically categorizes your mods:

| Category | Description | Examples |
|----------|-------------|----------|
| **Script Mod** | Contains Python code | MCCC, Wicked Whims, Basemental |
| **CAS CC** | Create-a-Sim items | Hair, clothes, makeup, skins |
| **Build/Buy CC** | Objects and building | Furniture, walls, floors |
| **Tuning Mod** | Gameplay tweaks | Career mods, trait mods |
| **Other** | Mixed or unknown | Merged packs |

## Common Mods Folder Paths

S4LT checks these locations automatically:

| Setup | Path |
|-------|------|
| NonSteamLaunchers | `~/.local/share/Steam/steamapps/compatdata/NonSteamLaunchers/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4/` |
| Steam Proton | `~/.local/share/Steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4/` |
| Flatpak Steam | `~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/compatdata/1222670/pfx/...` |
| Heroic | `~/.config/heroic/prefixes/The Sims 4/pfx/drive_c/...` |
| Lutris | `~/Games/the-sims-4/drive_c/users/$USER/Documents/Electronic Arts/The Sims 4/` |

## CLI Usage

```bash
# Scan mods folder
s4lt scan

# Show conflicts
s4lt conflicts
s4lt conflicts --high

# Find duplicates
s4lt duplicates

# Package info
s4lt info path/to/mod.package

# Tray items
s4lt tray list
s4lt tray cc "My Sim"

# Profiles
s4lt profile list
s4lt profile save "My CC Setup"
s4lt profile load "Vanilla Plus"

# Toggle mods
s4lt enable "*.package"
s4lt disable "BrokenMod.package"

# Vanilla mode
s4lt vanilla  # Toggle all mods off/on

# Start web UI
s4lt serve
```

## Building from Source

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Build AppImage
./build-appimage.sh
```

## Requirements

- Python 3.11+
- Linux (tested on Ubuntu 22.04, Steam Deck)
- GTK 3 or Qt 5/6 for desktop app

## License

MIT

## Credits

Built for the Sims modding community. Inspired by the need for native Linux tools.
