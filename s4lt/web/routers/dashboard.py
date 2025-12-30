"""Dashboard routes."""

import sqlite3
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates

from s4lt.web.deps import get_db, get_mods_path
from s4lt.web.paths import get_templates_dir
from s4lt.deck.storage import get_storage_summary, get_sd_card_path, check_symlink_health
from s4lt.organize.categorizer import ModCategory
from s4lt import __version__

router = APIRouter()
templates = Jinja2Templates(directory=get_templates_dir())


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

    # Get category counts
    category_counts = {
        ModCategory.SCRIPT.value: 0,
        ModCategory.CAS.value: 0,
        ModCategory.BUILD_BUY.value: 0,
        ModCategory.TUNING.value: 0,
        ModCategory.OTHER.value: 0,
    }

    cursor = conn.execute(
        "SELECT category, COUNT(*) as count FROM mods WHERE broken = 0 GROUP BY category"
    )
    for row in cursor.fetchall():
        if row[0] and row[0] in category_counts:
            category_counts[row[0]] = row[1]

    # Check vanilla mode
    cursor = conn.execute("SELECT COUNT(*) FROM profiles WHERE name = '_pre_vanilla'")
    is_vanilla = cursor.fetchone()[0] > 0

    mods_path = get_mods_path()

    # Get storage summary for the storage widget
    sd_path = get_sd_card_path()
    storage = get_storage_summary(mods_path, sd_path) if mods_path else None

    # Check for broken symlinks
    symlink_issues = check_symlink_health(mods_path) if mods_path else []

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
            "categories": category_counts,
            "is_vanilla": is_vanilla,
            "mods_path": str(mods_path) if mods_path else "Not configured",
            "storage": storage,
            "symlink_issues": symlink_issues,
        },
    )
