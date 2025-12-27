# S4LT: Sims 4 Linux Toolkit

Native Linux tools for Sims 4 mod management. No Wine. No Proton. No bullshit.

## Status

**Phase 1: Core Engine** - Complete
**Phase 2: Mod Scanner** - Complete

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

## Phase 1: DBPF Core Engine

The core DBPF parser is now functional:

```python
from s4lt import Package

# Open and inspect a package
with Package.open("path/to/mod.package") as pkg:
    print(f"Version: {pkg.version}")
    print(f"Resources: {len(pkg)}")

    for resource in pkg.resources:
        print(f"  {resource.type_name}: {resource.instance_id:016X}")

    # Extract a resource
    data = pkg.resources[0].extract()
```

### CLI Testing

```bash
python -m s4lt.cli.package_info path/to/mod.package
```

## Phase 2: Mod Scanner

Scan, index, and analyze your Mods folder:

```bash
# First run - detects Mods folder automatically
s4lt scan

# Show conflicts
s4lt conflicts
s4lt conflicts --high  # High severity only

# Find duplicates
s4lt duplicates

# Package info
s4lt info CoolHair.package
```

### Features

- **Full indexing** with human-readable names from tuning XML
- **Conflict detection** grouped by severity (high/medium/low)
- **Duplicate detection** - exact matches and content-identical packages
- **Incremental updates** - only re-indexes changed files
- **SQLite caching** for fast subsequent operations

## Usage (Future)

```bash
# Coming in Phase 3+
s4lt package view X    # View package contents
s4lt tray list         # List saved Sims/Lots
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
