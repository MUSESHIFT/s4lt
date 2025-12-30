"""Storage management routes."""

from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from s4lt.web.deps import get_mods_path
from s4lt.web.paths import get_templates_dir
from s4lt.deck.storage import (
    get_storage_summary,
    get_sd_card_path,
    list_removable_drives,
    move_to_sd,
    move_to_internal,
)
from s4lt import __version__

router = APIRouter(prefix="/storage", tags=["storage"])
templates = Jinja2Templates(directory=get_templates_dir())


@dataclass
class ModInfo:
    """Info about a mod for display."""
    name: str
    path: str
    size_mb: float
    is_symlink: bool


def _get_mod_list(mods_path: Path, only_symlinks: bool = False) -> list[ModInfo]:
    """Get list of mods with sizes."""
    mods = []

    if not mods_path.exists():
        return mods

    for item in sorted(mods_path.iterdir()):
        is_symlink = item.is_symlink()

        if only_symlinks and not is_symlink:
            continue
        if not only_symlinks and is_symlink:
            continue

        # Calculate size
        try:
            if is_symlink:
                target = item.resolve()
                if target.is_file():
                    size = target.stat().st_size
                else:
                    size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
            elif item.is_file():
                size = item.stat().st_size
            else:
                size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
        except OSError:
            size = 0

        mods.append(ModInfo(
            name=item.name,
            path=str(item),
            size_mb=size / 1_000_000,
            is_symlink=is_symlink,
        ))

    # Sort by size descending
    return sorted(mods, key=lambda m: m.size_mb, reverse=True)


@router.get("")
async def storage_page(request: Request):
    """Storage management page."""
    mods_path = get_mods_path()
    sd_path = get_sd_card_path()
    drives = list_removable_drives()

    storage = get_storage_summary(mods_path, sd_path) if mods_path else None
    internal_mods = _get_mod_list(mods_path, only_symlinks=False) if mods_path else []
    sd_mods = _get_mod_list(mods_path, only_symlinks=True) if mods_path else []

    return templates.TemplateResponse(
        request,
        "storage.html",
        {
            "active": "storage",
            "version": __version__,
            "storage": storage,
            "internal_mods": internal_mods,
            "sd_mods": sd_mods,
            "sd_available": sd_path is not None,
            "sd_name": drives[0].name if drives else None,
        },
    )


@router.post("/move-to-sd")
async def move_mods_to_sd(request: Request):
    """Move selected mods to SD card."""
    form = await request.form()
    paths = form.getlist("paths")

    sd_path = get_sd_card_path()
    if sd_path is None:
        return RedirectResponse("/storage", status_code=303)

    sd_mods_path = sd_path / "S4LT"
    mod_paths = [Path(p) for p in paths]

    move_to_sd(mod_paths, sd_mods_path)

    return RedirectResponse("/storage", status_code=303)


@router.post("/move-to-internal")
async def move_mods_to_internal(request: Request):
    """Move selected mods back to internal."""
    form = await request.form()
    paths = form.getlist("paths")

    mods_path = get_mods_path()
    if mods_path is None:
        return RedirectResponse("/storage", status_code=303)

    symlink_paths = [Path(p) for p in paths]

    move_to_internal(symlink_paths, mods_path)

    return RedirectResponse("/storage", status_code=303)
