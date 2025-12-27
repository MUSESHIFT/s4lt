# Phase 6: Package Editor Design

> **Goal:** Build a complete s4pe/s4pi replacement for Linux with web-based editing.

## Overview

Phase 6 adds full package editing capabilities to S4LT:
- View and browse .package contents
- Edit XML tuning with schema-aware validation
- Edit string tables with table/text views
- Preview thumbnails and textures
- Merge multiple packages with conflict resolution
- Split packages by type or group
- CLI commands for automation

## Architecture

### Core Enhancement: DBPF Write Support

Extend `s4lt/core` with write capabilities:

- `Package.save()` - Write modified package to disk
- `Package.add_resource(type, group, instance, data)` - Add new resource
- `Package.remove_resource(tgi)` - Remove resource by TGI
- `Package.update_resource(tgi, data)` - Update existing resource
- Automatic backup creation on first modification (`.package.bak`)

### New Module: `s4lt/editor`

```
s4lt/editor/
├── __init__.py
├── session.py      # Edit session state management
├── xml_schema.py   # Tuning type definitions, validation
├── stbl.py         # String table parsing/editing
├── preview.py      # Thumbnail/texture rendering
├── merge.py        # Package merge with conflict detection
└── split.py        # Package splitting logic
```

### Web UI Extension

New routes under `/package/`:
- `/package/<path>` - Package viewer/editor page
- `/package/<path>/resource/<tgi>` - Resource detail/edit view
- `/api/package/...` - HTMX endpoints for save, extract, etc.

### Save Strategy: Copy-on-Write

- Create `.package.bak` backup before first modification
- Subsequent saves write directly to the package
- Safe balance of protection and simplicity

## Package Viewer

### Resource List Table

Sortable, filterable table showing all resources:

| Column | Description |
|--------|-------------|
| Type | Human-readable name (CASP, STBL, _XML) with hex on hover |
| Group | Hex display, click to copy |
| Instance | Hex display, click to copy |
| Name | Extracted from resource if available |
| Size | Decompressed size |
| Compressed | Indicator if internally compressed |

### Filtering

- Search box: Filter by type, name, or TGI
- Type dropdown: Show only specific resource types
- Quick filters: "Tuning only", "Textures only", "Strings only"

### Actions

Per resource:
- View/Edit (opens detail panel)
- Extract (download single resource)
- Delete (with confirmation)

Bulk:
- Select multiple → Extract all, Delete all
- Export resource list as CSV

## XML Tuning Editor

### Editor Interface

Split panel layout:
- Left: Code editor with XML content
- Right: Validation panel showing errors/warnings

### Syntax Features

- Syntax highlighting (tags, attributes, values, comments)
- Line numbers with error markers
- Auto-indent on Enter
- Bracket matching for `<tag>...</tag>`

### Schema-Aware Validation

Tuning schema registry with ~50 common types:

```python
TUNING_SCHEMAS = {
    "buff": {"required": ["buff_type", "visible"], "optional": ["mood_type", ...]},
    "trait": {"required": ["trait_type", "display_name"], ...},
    "object": {"required": ["tuning_id"], ...},
}
```

Validation levels:
- **Error**: Malformed XML, missing required tags → blocks save
- **Warning**: Unknown tags, deprecated attributes → save with confirmation
- **Info**: Suggestions, best practices → informational only

### Autocomplete

When typing `<` inside a known tuning type:
- Suggest valid child tags
- Show required vs optional
- Insert template with required attributes

## String Table Editor

### Table View (Default)

Interactive grid:

| String ID | Text | Actions |
|-----------|------|---------|
| 0x12345678 | "Custom buff text" | Edit, Delete |

Features:
- Click cell to inline edit
- Add new string (auto-generate ID or manual)
- Sort by ID or text
- Search/filter
- Pagination for large STBLs

### Text View (Toggle)

Raw format for bulk operations:

```
0x12345678: This is my custom buff
0x23456789: Feeling groovy!
```

Features:
- Full textarea editing
- Copy/paste friendly
- Parse validation on toggle back

### Import/Export

- Export as CSV (ID, Text columns)
- Export as JSON `{"0x12345678": "text", ...}`
- Import from CSV/JSON

## Resource Previews

### Texture Preview

Supported formats:
- DST (Sims 4 texture format) → decode to PNG
- DDS (DirectDraw Surface) → decode to PNG
- PNG/JPEG if embedded

Display features:
- Inline image preview
- Dimensions and format info
- Zoom controls
- Download as PNG

### Non-Previewable Resources

- Hex dump view (first 256 bytes)
- Resource metadata display
- Raw download option

## Package Merge

### Workflow

1. Load all input packages
2. Collect resources, detect conflicts (same TGI)
3. Show interactive conflict resolution UI
4. User selects which version to keep
5. Merge and save

### Conflict Resolution UI

| Resource | Source A | Source B | Keep |
|----------|----------|----------|------|
| 0x034AEECB:0:0x123... | v1.package (2.1 KB) | v2.package (2.4 KB) | ○ A ● B |

## Package Split

### Split Modes

- `--by-type` → One package per resource type
- `--by-group` → Split by Group ID
- `--extract-all` → Individual files (not packages)

### Output Structure

```
split/
├── mymod_XML.package
├── mymod_STBL.package
├── mymod_DST.package
└── mymod_OTHER.package
```

## CLI Commands

```bash
# View package contents
s4lt package view mymod.package
s4lt package view mymod.package --type XML
s4lt package view mymod.package --json

# Extract resources
s4lt package extract mymod.package 0x034AEECB:0:0x12345678
s4lt package extract mymod.package --type STBL --output ./strings/
s4lt package extract mymod.package --all --output ./extracted/

# Open web editor
s4lt package edit mymod.package

# Merge packages
s4lt package merge combined.package mod1.package mod2.package
s4lt package merge combined.package ./mods/*.package

# Split package
s4lt package split mymod.package --by-type --output ./split/
s4lt package split mymod.package --by-group
s4lt package split mymod.package --extract-all
```

### Exit Codes

- 0: Success
- 1: Package read error
- 2: Resource not found
- 3: Merge conflict (non-interactive)
- 4: Write error

## Implementation Tasks

1. DBPF write support in core
2. Backup/save session management
3. Package viewer page + API
4. Resource detail view
5. XML syntax highlighting
6. XML schema registry
7. XML validation + autocomplete
8. STBL table view editor
9. STBL text view + toggle
10. STBL import/export
11. Texture preview (DST/DDS decode)
12. Merge logic + conflict detection
13. Merge web UI
14. Split logic + CLI
15. CLI package subcommand group

## Dependencies

- Pillow: Image processing for texture previews
- Existing: FastAPI, HTMX, TailwindCSS from Phase 5
