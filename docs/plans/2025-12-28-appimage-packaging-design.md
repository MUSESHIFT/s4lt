# S4LT AppImage Packaging Design

## Overview

Package S4LT as a standalone AppImage for easy distribution to Sims players on Linux/Steam Deck.

## Goals

- Single downloadable file: `S4LT-0.7.0-x86_64.AppImage`
- User downloads, marks executable, double-clicks to run
- Native desktop window (no browser required)
- System tray for background operation
- Target audience: Sims players, not developers

## Architecture

### Stack

- **pywebview** - Native window with embedded webview
- **pystray** - System tray icon for background mode
- **FastAPI** - Runs in background thread, serves to webview
- **PyInstaller + appimage-builder** - Packaging

### User Experience

1. Double-click `S4LT.AppImage`
2. Native window opens showing the S4LT UI
3. Tray icon appears in system tray
4. Close window → app minimizes to tray
5. Click tray icon → window reopens
6. Right-click tray → menu options
7. "Quit" stops server and exits

### Tray Menu

- **Open S4LT** - Show/focus window
- **Restart Server** - Restart FastAPI backend
- **View Logs** - Open log viewer window
- **Settings** - Open settings (future)
- **Quit** - Stop server, close window, exit

## File Structure

```
/root/s4lt/
├── s4lt/
│   └── desktop/
│       ├── __init__.py
│       ├── app.py        # Main desktop app (pywebview + server)
│       ├── tray.py       # System tray with pystray
│       └── launcher.py   # Entry point for PyInstaller
├── assets/
│   ├── s4lt-icon.svg     # Source icon (green plumbob + S4LT)
│   └── s4lt-icon.png     # 256x256 rendered
├── appimage/
│   ├── s4lt.spec         # PyInstaller config
│   ├── AppImageBuilder.yml
│   └── s4lt.desktop      # Desktop entry file
└── dist/
    └── S4LT-0.7.0-x86_64.AppImage
```

## Implementation Details

### Desktop App (`s4lt/desktop/app.py`)

- Start FastAPI server in background thread on port 8040
- Create pywebview window pointing to `http://localhost:8040`
- Window title: "S4LT - Sims 4 Linux Toolkit"
- Window size: 1200x800, resizable
- On window close: minimize to tray (don't exit)

### System Tray (`s4lt/desktop/tray.py`)

- Uses pystray for cross-platform tray support
- Icon loaded from bundled assets
- Menu with Open/Restart/Logs/Settings/Quit options

### Launcher (`s4lt/desktop/launcher.py`)

- PyInstaller entry point
- Initialize logging to `~/.local/share/s4lt/logs/`
- Start tray in separate thread
- Start main webview window (blocks until quit)

### New Dependencies

```toml
dependencies = [
    # ... existing ...
    "pywebview>=4.0",
    "pystray>=0.19",
]
```

### New CLI Command

```bash
s4lt desktop  # Launch the desktop app
```

## Packaging

### PyInstaller Config

- Entry: `s4lt/desktop/launcher.py`
- Hidden imports: uvicorn, fastapi, jinja2, multipart, etc.
- Include data: `web/templates/`, `web/static/`, `assets/`
- One-folder mode (faster startup than one-file)
- Strip binaries for smaller size

### AppImage Config

- Base: Ubuntu 22.04 runtime
- Include: libwebkit2gtk (for pywebview)
- Desktop integration via s4lt.desktop
- Icon at multiple sizes (16, 32, 48, 64, 128, 256)
- AppStream metadata for software centers

### Build Process

```bash
# 1. Create venv, install deps
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Run PyInstaller
pyinstaller appimage/s4lt.spec

# 3. Run appimage-builder
appimage-builder --recipe appimage/AppImageBuilder.yml

# 4. Output: S4LT-0.7.0-x86_64.AppImage (~60-80MB)
```

## Deliverables

1. `S4LT-0.7.0-x86_64.AppImage` - Standalone executable
2. `README-INSTALL.md` - 3-step install instructions for mod sites
3. `assets/s4lt-icon.svg` + `.png` - App icon

## Install Instructions (for README)

### Linux (3 steps)

1. Download `S4LT-0.7.0-x86_64.AppImage`
2. Right-click → Properties → Permissions → "Allow executing as program"
3. Double-click to run

### Steam Deck

1. Switch to Desktop Mode (hold Power → Desktop Mode)
2. Download the AppImage to your Desktop
3. Right-click → Properties → Permissions → Is Executable
4. Double-click to launch
5. (Optional) Add to Steam as non-Steam game for Gaming Mode
