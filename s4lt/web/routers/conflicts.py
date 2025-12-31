"""Conflict detection and display routes."""

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from s4lt.web.paths import get_templates_dir
from s4lt.web.deps import get_mods_path
from s4lt.mods.scanner import discover_packages
from s4lt.conflicts.detector import detect_conflicts, ConflictSeverity
from s4lt import __version__

router = APIRouter(prefix="/conflicts", tags=["conflicts"])
templates = Jinja2Templates(directory=get_templates_dir())
logger = logging.getLogger(__name__)


@router.get("", response_class=HTMLResponse)
async def conflicts_page(request: Request):
    """Show detected conflicts."""
    mods_path = get_mods_path()

    report = None
    error_message = None
    if mods_path and mods_path.exists():
        try:
            packages = discover_packages(mods_path, include_scripts=True)
            report = detect_conflicts(packages)
        except Exception as e:
            logger.error(f"Failed to detect conflicts: {e}")
            error_message = str(e)

    return templates.TemplateResponse(
        "conflicts.html",
        {
            "request": request,
            "version": __version__,
            "report": report,
            "mods_path": mods_path,
            "error_message": error_message,
        },
    )


@router.post("/scan")
async def scan_conflicts():
    """Trigger a conflict scan and return results."""
    mods_path = get_mods_path()

    if not mods_path or not mods_path.exists():
        return JSONResponse({
            "success": False,
            "error": "Mods path not configured",
        })

    try:
        packages = discover_packages(mods_path, include_scripts=True)
        report = detect_conflicts(packages)

        return JSONResponse({
            "success": True,
            "report": report.to_dict(),
        })
    except Exception as e:
        logger.error(f"Conflict scan failed: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
        })


@router.post("/{conflict_id}/resolve")
async def resolve_conflict(conflict_id: int, action: str):
    """Resolve a conflict with the specified action."""
    # TODO: Implement conflict resolution
    # Actions: keep_first, keep_second, disable_all, ignore
    return JSONResponse({
        "success": False,
        "error": "Not implemented yet",
    })
