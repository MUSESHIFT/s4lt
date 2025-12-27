"""Mods browser routes."""

import sqlite3
from fastapi import APIRouter, Request, Depends, Query
from fastapi.templating import Jinja2Templates
from pathlib import Path

from s4lt.web.deps import get_db, get_mods_path
from s4lt.organize.categorizer import categorize_mod, ModCategory
from s4lt import __version__

router = APIRouter(prefix="/mods", tags=["mods"])
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("")
async def mods_list(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    category: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=10, le=200),
):
    """Render mods browser page."""
    offset = (page - 1) * per_page

    # Build query
    query = "SELECT * FROM mods WHERE broken = 0"
    params = []

    if search:
        query += " AND filename LIKE ?"
        params.append(f"%{search}%")

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY filename LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    cursor = conn.execute(query, params)
    mods = [dict(row) for row in cursor.fetchall()]

    # Get total count
    count_query = "SELECT COUNT(*) FROM mods WHERE broken = 0"
    count_params = []
    if search:
        count_query += " AND filename LIKE ?"
        count_params.append(f"%{search}%")
    if category:
        count_query += " AND category = ?"
        count_params.append(category)

    cursor = conn.execute(count_query, count_params)
    total = cursor.fetchone()[0]

    # Calculate category for each mod
    for mod in mods:
        if not mod.get("category"):
            cat = categorize_mod(conn, mod["id"])
            mod["category"] = cat.value

    # Get category counts
    cursor = conn.execute("""
        SELECT category, COUNT(*) as count
        FROM mods
        WHERE broken = 0 AND category IS NOT NULL
        GROUP BY category
    """)
    categories = {row[0]: row[1] for row in cursor.fetchall()}

    mods_path = get_mods_path()

    return templates.TemplateResponse(
        request,
        "mods.html",
        {
            "active": "mods",
            "version": __version__,
            "mods": mods,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page if total > 0 else 1,
            "search": search or "",
            "category": category or "",
            "categories": categories,
            "mods_path": mods_path,
        },
    )


@router.post("/{mod_id}/toggle")
async def toggle_mod(
    request: Request,
    mod_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Toggle mod enabled/disabled state."""
    from s4lt.organize.toggle import enable_mod, disable_mod, is_enabled

    cursor = conn.execute("SELECT path FROM mods WHERE id = ?", (mod_id,))
    row = cursor.fetchone()
    if not row:
        return {"error": "Mod not found"}

    mods_path = get_mods_path()
    if not mods_path:
        return {"error": "Mods path not configured"}

    mod_path = mods_path / row[0]

    if is_enabled(mod_path):
        disable_mod(mod_path)
        new_state = "disabled"
    else:
        enable_mod(mod_path)
        new_state = "enabled"

    return {"status": new_state}
