"""Setup wizard and settings routes."""

import sqlite3
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from s4lt.config.paths import detect_all_paths, is_steam_deck
from s4lt.config.settings import get_settings, save_settings, Settings, CONFIG_FILE
from s4lt.web.deps import get_db
from s4lt.web.paths import get_templates_dir
from s4lt import __version__


logger = logging.getLogger(__name__)

router = APIRouter(tags=["setup"])
templates = Jinja2Templates(directory=get_templates_dir())


def needs_setup() -> bool:
    """Check if first-run setup is needed."""
    settings = get_settings()
    # Need setup if no mods path configured or config file doesn't exist
    return settings.mods_path is None or not CONFIG_FILE.exists()


@router.get("/setup")
async def setup_wizard(request: Request):
    """Render setup wizard page."""
    # Auto-detect paths
    detected = detect_all_paths()
    settings = get_settings()

    # Check if we're on Steam Deck
    on_deck = is_steam_deck()

    return templates.TemplateResponse(
        request,
        "setup.html",
        {
            "active": "setup",
            "version": __version__,
            "detected_mods": str(detected.get('mods')) if detected.get('mods') else None,
            "detected_tray": str(detected.get('tray')) if detected.get('tray') else None,
            "detected_saves": str(detected.get('saves')) if detected.get('saves') else None,
            "current_mods": str(settings.mods_path) if settings.mods_path else None,
            "current_tray": str(settings.tray_path) if settings.tray_path else None,
            "on_steam_deck": on_deck,
            "needs_setup": needs_setup(),
        },
    )


@router.post("/setup/save")
async def save_setup(
    request: Request,
    mods_path: str = Form(...),
    tray_path: str = Form(None),
    saves_path: str = Form(None),
):
    """Save setup configuration."""
    settings = get_settings()

    # Validate paths
    mods = Path(mods_path) if mods_path else None
    if mods and not mods.is_dir():
        return JSONResponse(
            {"error": f"Mods folder not found: {mods_path}"},
            status_code=400
        )

    settings.mods_path = mods

    if tray_path:
        tray = Path(tray_path)
        if tray.is_dir():
            settings.tray_path = tray

    save_settings(settings)
    logger.info(f"Settings saved: mods={settings.mods_path}, tray={settings.tray_path}")

    return RedirectResponse("/setup/scan", status_code=303)


@router.get("/setup/scan")
async def setup_scan_page(request: Request):
    """Render the scan progress page."""
    settings = get_settings()

    if not settings.mods_path:
        return RedirectResponse("/setup", status_code=303)

    return templates.TemplateResponse(
        request,
        "setup_scan.html",
        {
            "active": "setup",
            "version": __version__,
            "mods_path": str(settings.mods_path),
        },
    )


@router.get("/setup/scan/stream")
async def stream_scan_progress(request: Request):
    """Stream scan progress via Server-Sent Events."""
    from s4lt.config.settings import get_settings, DB_PATH
    from s4lt.db.schema import init_db
    from s4lt.mods import discover_packages, index_package
    from s4lt.organize.categorizer import categorize_mod, ModCategory
    from starlette.responses import StreamingResponse
    import json
    import asyncio

    settings = get_settings()
    if not settings.mods_path:
        async def error_gen():
            yield f"data: {json.dumps({'error': 'Mods path not configured'})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

    async def generate():
        # Initialize database
        init_db(DB_PATH)

        # Discover packages
        yield f"data: {json.dumps({'status': 'discovering', 'message': 'Discovering mods...'})}\n\n"
        await asyncio.sleep(0.01)  # Allow UI to update

        packages = list(discover_packages(settings.mods_path))
        total = len(packages)

        yield f"data: {json.dumps({'status': 'discovered', 'total': total, 'message': f'Found {total} packages'})}\n\n"
        await asyncio.sleep(0.01)

        if total == 0:
            yield f"data: {json.dumps({'status': 'complete', 'total': 0, 'indexed': 0, 'categories': {}})}\n\n"
            return

        # Index packages
        import sqlite3 as sql
        conn = sql.connect(DB_PATH, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sql.Row

        indexed = 0
        broken = 0
        errors = 0
        categories = {
            ModCategory.SCRIPT.value: 0,
            ModCategory.CAS.value: 0,
            ModCategory.BUILD_BUY.value: 0,
            ModCategory.TUNING.value: 0,
            ModCategory.OTHER.value: 0,
        }

        try:
            for i, pkg_path in enumerate(packages):
                try:
                    # Log progress every 50 packages
                    if i % 50 == 0:
                        logger.info(f"Indexing {i+1}/{total}: {pkg_path.name}")

                    # Send progress update
                    progress_data = {
                        'status': 'indexing',
                        'current': i + 1,
                        'total': total,
                        'percent': round((i + 1) / total * 100),
                        'filename': pkg_path.name,
                    }
                    yield f"data: {json.dumps(progress_data)}\n\n"

                    mod_id = index_package(conn, settings.mods_path, pkg_path)
                    if mod_id:
                        category = categorize_mod(conn, mod_id)
                        conn.execute(
                            "UPDATE mods SET category = ? WHERE id = ?",
                            (category.value, mod_id)
                        )
                        categories[category.value] = categories.get(category.value, 0) + 1
                        indexed += 1
                    else:
                        # index_package returned None = broken/corrupt package
                        broken += 1

                except Exception as e:
                    logger.warning(f"Error indexing {pkg_path.name}: {e}")
                    errors += 1

                # Yield control periodically to keep stream alive
                if i % 5 == 0:
                    await asyncio.sleep(0.001)

            conn.commit()
            logger.info(f"Scan complete: {indexed} indexed, {broken} broken, {errors} errors")
        finally:
            conn.close()

        # Send completion
        yield f"data: {json.dumps({'status': 'complete', 'total': total, 'indexed': indexed, 'broken': broken, 'errors': errors, 'categories': categories})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/setup/scan/start")
async def start_initial_scan(request: Request):
    """Legacy endpoint - redirects to SSE stream."""
    return JSONResponse({"redirect": "/setup/scan/stream"})


@router.get("/settings")
async def settings_page(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render settings page."""
    settings = get_settings()
    detected = detect_all_paths()
    on_deck = is_steam_deck()

    # Get database stats
    cursor = conn.execute("SELECT COUNT(*) FROM mods")
    total_mods = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM resources")
    total_resources = cursor.fetchone()[0]

    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "active": "settings",
            "version": __version__,
            "settings": settings,
            "detected_mods": str(detected.get('mods')) if detected.get('mods') else None,
            "detected_tray": str(detected.get('tray')) if detected.get('tray') else None,
            "detected_saves": str(detected.get('saves')) if detected.get('saves') else None,
            "on_steam_deck": on_deck,
            "total_mods": total_mods,
            "total_resources": total_resources,
        },
    )


@router.post("/settings/save")
async def save_settings_form(
    request: Request,
    mods_path: str = Form(None),
    tray_path: str = Form(None),
    include_subfolders: bool = Form(True),
):
    """Save settings from form."""
    settings = get_settings()

    if mods_path:
        mods = Path(mods_path)
        if mods.is_dir():
            settings.mods_path = mods

    if tray_path:
        tray = Path(tray_path)
        if tray.is_dir():
            settings.tray_path = tray

    settings.include_subfolders = include_subfolders

    save_settings(settings)
    logger.info(f"Settings updated: {settings}")

    return RedirectResponse("/settings?saved=1", status_code=303)


@router.post("/settings/rescan")
async def trigger_rescan(request: Request):
    """Trigger a full rescan of the mods folder."""
    from s4lt.config.settings import get_settings, DB_PATH
    from s4lt.db.schema import init_db
    from s4lt.mods import discover_packages, index_package
    from s4lt.organize.categorizer import categorize_mod

    settings = get_settings()
    if not settings.mods_path:
        return JSONResponse({"error": "Mods path not configured"}, status_code=400)

    # Clear existing data
    import sqlite3 as sql
    conn = sql.connect(DB_PATH, check_same_thread=False)
    conn.execute("DELETE FROM resources")
    conn.execute("DELETE FROM mods")
    conn.commit()

    # Re-index
    packages = list(discover_packages(settings.mods_path))
    for pkg_path in packages:
        try:
            mod_id = index_package(conn, settings.mods_path, pkg_path)
            if mod_id:
                category = categorize_mod(conn, mod_id)
                conn.execute(
                    "UPDATE mods SET category = ? WHERE id = ?",
                    (category.value, mod_id)
                )
        except Exception as e:
            logger.warning(f"Error indexing {pkg_path}: {e}")

    conn.commit()
    conn.close()

    return RedirectResponse("/settings?rescanned=1", status_code=303)
