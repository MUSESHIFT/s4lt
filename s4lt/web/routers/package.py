"""Package viewer and editor routes."""

from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response

from s4lt.core import Package, get_type_name
from s4lt.editor.session import get_session, close_session
from s4lt import __version__

router = APIRouter(prefix="/package", tags=["package"])
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/{path:path}")
async def view_package(request: Request, path: str):
    """View package contents."""
    decoded_path = unquote(path)
    pkg_path = Path(decoded_path)

    if not pkg_path.exists():
        raise HTTPException(status_code=404, detail="Package not found")

    try:
        session = get_session(str(pkg_path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Build resource list
    resources = []
    for res in session.resources:
        resources.append({
            "type_id": res.type_id,
            "type_name": res.type_name,
            "group_id": res.group_id,
            "instance_id": res.instance_id,
            "size": res.uncompressed_size,
            "compressed": res.is_compressed,
            "tgi": f"{res.type_id:08X}:{res.group_id:08X}:{res.instance_id:016X}",
        })

    # Group by type for stats
    type_counts = {}
    for res in resources:
        t = res["type_name"]
        type_counts[t] = type_counts.get(t, 0) + 1

    return templates.TemplateResponse(
        request,
        "package/view.html",
        {
            "active": "package",
            "version": __version__,
            "path": str(pkg_path),
            "filename": pkg_path.name,
            "resources": resources,
            "total": len(resources),
            "type_counts": type_counts,
            "has_changes": session.has_unsaved_changes,
        },
    )
