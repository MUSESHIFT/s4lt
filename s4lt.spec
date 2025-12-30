# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for S4LT desktop application."""

import sys
from pathlib import Path

block_cipher = None

# Get the project root
project_root = Path(SPECPATH)

# Collect data files
datas = [
    # Web templates and static files
    (str(project_root / 's4lt' / 'web' / 'templates'), 'web/templates'),
    (str(project_root / 's4lt' / 'web' / 'static'), 'web/static'),
    # Asset files (icons)
    (str(project_root / 'assets'), 'assets'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'jinja2',
    'fastapi',
    'starlette',
    'pystray._xorg',
    'PIL._tkinter_finder',
    'webview',
    'webview.platforms.gtk',
    's4lt.web.routers.dashboard',
    's4lt.web.routers.mods',
    's4lt.web.routers.tray',
    's4lt.web.routers.profiles',
    's4lt.web.routers.api',
    's4lt.web.routers.package',
    's4lt.web.routers.storage',
    's4lt.web.routers.setup',
]

a = Analysis(
    ['s4lt/desktop/launcher.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='s4lt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'assets' / 's4lt-icon.png'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='s4lt',
)
