# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for S4LT desktop application."""

import sys
from pathlib import Path

# Get the project root
project_root = Path(SPECPATH).parent

block_cipher = None

# Collect data files
datas = [
    # Web UI assets
    (str(project_root / 's4lt' / 'web' / 'templates'), 's4lt/web/templates'),
    (str(project_root / 's4lt' / 'web' / 'static'), 's4lt/web/static'),
    # App assets (icons)
    (str(project_root / 'assets'), 'assets'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    # FastAPI and uvicorn
    'uvicorn',
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
    # FastAPI deps
    'fastapi',
    'starlette',
    'starlette.routing',
    'starlette.middleware',
    'starlette.staticfiles',
    'anyio._backends._asyncio',
    # Jinja2
    'jinja2',
    'jinja2.ext',
    # Python multipart
    'multipart',
    'python_multipart',
    # Pillow
    'PIL',
    'PIL.Image',
    # pystray
    'pystray',
    'pystray._xorg',
    # pywebview
    'webview',
    'webview.platforms.gtk',
    # S4LT modules
    's4lt.web',
    's4lt.web.app',
    's4lt.web.routers',
    's4lt.web.routers.dashboard',
    's4lt.web.routers.mods',
    's4lt.web.routers.tray',
    's4lt.web.routers.profiles',
    's4lt.web.routers.api',
    's4lt.web.routers.package',
    's4lt.web.routers.storage',
    's4lt.core',
    's4lt.mods',
    's4lt.tray',
    's4lt.config',
    's4lt.ea',
    's4lt.organize',
    's4lt.editor',
    's4lt.deck',
    's4lt.db',
    's4lt.desktop',
]

a = Analysis(
    [str(project_root / 's4lt' / 'desktop' / 'launcher.py')],
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
    strip=True,
    upx=True,
    console=False,  # No console window
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
    strip=True,
    upx=True,
    upx_exclude=[],
    name='s4lt',
)
