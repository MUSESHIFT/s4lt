"""API endpoints for HTMX and JSON consumers."""

import sqlite3
from fastapi import APIRouter, Depends, BackgroundTasks
from pathlib import Path

from s4lt.web.deps import get_db, get_mods_path
from s4lt.organize.vanilla import toggle_vanilla, is_vanilla_mode
from s4lt import __version__

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/status")
async def get_status(conn: sqlite3.Connection = Depends(get_db)):
    """Get current system status."""
    cursor = conn.execute("SELECT COUNT(*) FROM mods WHERE broken = 0")
    total_mods = cursor.fetchone()[0]

    is_vanilla = is_vanilla_mode(conn)
    mods_path = get_mods_path()

    return {
        "version": __version__,
        "total_mods": total_mods,
        "is_vanilla": is_vanilla,
        "mods_configured": mods_path is not None,
    }


@router.post("/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    """Trigger a background mod scan."""
    from s4lt.config.settings import get_settings, DB_PATH
    from s4lt.db.schema import init_db
    from s4lt.mods import discover_packages, categorize_changes, index_package

    settings = get_settings()
    if not settings.mods_path:
        return {"error": "Mods path not configured"}

    def do_scan():
        init_db(DB_PATH)
        # Use check_same_thread=False for background task
        import sqlite3 as sql
        conn = sql.connect(DB_PATH, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sql.Row
        try:
            disk_files = set(discover_packages(settings.mods_path))
            new_files, modified_files, _ = categorize_changes(conn, settings.mods_path, disk_files)
            for pkg_path in new_files | modified_files:
                index_package(conn, settings.mods_path, pkg_path)
        finally:
            conn.close()

    background_tasks.add_task(do_scan)
    return {"status": "scanning"}


@router.post("/vanilla/toggle")
async def api_toggle_vanilla(conn: sqlite3.Connection = Depends(get_db)):
    """Toggle vanilla mode via API."""
    mods_path = get_mods_path()
    if not mods_path:
        return {"error": "Mods path not configured"}

    result = toggle_vanilla(conn, mods_path)
    return {
        "is_vanilla": result.is_vanilla,
        "mods_changed": result.mods_changed,
    }
