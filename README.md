# S4LT: Sims 4 Linux Toolkit

Native Linux tools for Sims 4 mod management. No Wine. No Proton. No bullshit.

## Status

**Phase 1: Core Engine** - In Progress

## Features (Planned)

- **Mod Manager** - Scan, organize, detect conflicts, manage loadouts
- **Tray Manager** - Browse saved Sims/Lots, track CC usage
- **Package Editor** - View and edit .package files
- **Tuning Editor** - Create gameplay tweaks without coding
- **Save Manager** - Backup, restore, and edit saves
- **Steam Deck Support** - Controller UI, SD card management, sync

## Installation

```bash
# Coming soon
pip install s4lt
```

## Usage

```bash
# Coming soon
s4lt scan              # Scan mods folder
s4lt conflicts         # Show conflicts
s4lt package view X    # View package contents
```

## Development

```bash
cd /root/s4lt
python -m pytest tests/
```

## Documentation

- [Full Specification](docs/S4LT-FULL-SPEC.md)
- [Phase 1 Design](docs/plans/2025-12-26-dbpf-core-engine-design.md)

## License

MIT
