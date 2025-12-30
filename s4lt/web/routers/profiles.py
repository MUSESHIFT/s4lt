"""Profile management routes."""

import sqlite3
from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from s4lt.web.deps import get_db, get_mods_path
from s4lt.web.paths import get_templates_dir
from s4lt.organize.profiles import (
    list_profiles,
    create_profile,
    delete_profile,
    save_profile_snapshot,
    switch_profile,
)
from s4lt.organize.vanilla import toggle_vanilla, is_vanilla_mode
from s4lt.organize.exceptions import ProfileExistsError, ProfileNotFoundError
from s4lt import __version__

router = APIRouter(prefix="/profiles", tags=["profiles"])
templates = Jinja2Templates(directory=get_templates_dir())


@router.get("")
async def profiles_list(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render profiles page."""
    profiles = list_profiles(conn)
    is_vanilla = is_vanilla_mode(conn)
    mods_path = get_mods_path()

    profile_data = []
    for p in profiles:
        if p.name.startswith("_"):
            continue  # Skip internal profiles
        profile_data.append({
            "id": p.id,
            "name": p.name,
            "created": datetime.fromtimestamp(p.created_at).strftime("%Y-%m-%d %H:%M"),
            "is_auto": p.is_auto,
        })

    return templates.TemplateResponse(
        request,
        "profiles.html",
        {
            "active": "profiles",
            "version": __version__,
            "profiles": profile_data,
            "is_vanilla": is_vanilla,
            "mods_path": str(mods_path) if mods_path else None,
        },
    )


@router.post("/create")
async def create_new_profile(
    request: Request,
    name: str = Form(...),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Create a new profile from current state."""
    mods_path = get_mods_path()
    if not mods_path:
        return RedirectResponse("/profiles?error=no_mods_path", status_code=303)

    try:
        profile = create_profile(conn, name)
        save_profile_snapshot(conn, profile.id, mods_path)
    except ProfileExistsError:
        return RedirectResponse("/profiles?error=exists", status_code=303)

    return RedirectResponse("/profiles?success=created", status_code=303)


@router.post("/{name}/load")
async def load_profile(
    name: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Load/activate a profile."""
    mods_path = get_mods_path()
    if not mods_path:
        return RedirectResponse("/profiles?error=no_mods_path", status_code=303)

    try:
        switch_profile(conn, name, mods_path)
    except ProfileNotFoundError:
        return RedirectResponse("/profiles?error=not_found", status_code=303)

    return RedirectResponse("/profiles?success=loaded", status_code=303)


@router.post("/{name}/delete")
async def delete_existing_profile(
    name: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Delete a profile."""
    try:
        delete_profile(conn, name)
    except ProfileNotFoundError:
        pass

    return RedirectResponse("/profiles?success=deleted", status_code=303)


@router.post("/vanilla/toggle")
async def toggle_vanilla_mode(
    conn: sqlite3.Connection = Depends(get_db),
):
    """Toggle vanilla mode."""
    mods_path = get_mods_path()
    if not mods_path:
        return RedirectResponse("/profiles?error=no_mods_path", status_code=303)

    toggle_vanilla(conn, mods_path)
    return RedirectResponse("/profiles", status_code=303)
