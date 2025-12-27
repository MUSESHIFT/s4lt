"""Dashboard routes."""

import sqlite3
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from pathlib import Path

from s4lt.web.deps import get_db, get_mods_path
from s4lt import __version__

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/")
async def dashboard(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render dashboard page."""
    # Get stats from database
    cursor = conn.execute("SELECT COUNT(*) FROM mods WHERE broken = 0")
    total_mods = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM mods WHERE broken = 1")
    broken_mods = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM resources")
    total_resources = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM profiles")
    total_profiles = cursor.fetchone()[0]

    # Check vanilla mode
    cursor = conn.execute("SELECT COUNT(*) FROM profiles WHERE name = '_pre_vanilla'")
    is_vanilla = cursor.fetchone()[0] > 0

    mods_path = get_mods_path()

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "active": "dashboard",
            "version": __version__,
            "stats": {
                "total_mods": total_mods,
                "broken_mods": broken_mods,
                "total_resources": total_resources,
                "total_profiles": total_profiles,
            },
            "is_vanilla": is_vanilla,
            "mods_path": str(mods_path) if mods_path else "Not configured",
        },
    )
