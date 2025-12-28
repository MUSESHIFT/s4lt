"""Package viewer and editor routes."""

from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response, StreamingResponse
import io

from s4lt.core import Package, get_type_name
from s4lt.editor.session import get_session, close_session
from s4lt.editor.xml_schema import validate_tuning, format_xml
from s4lt.editor.stbl import parse_stbl, stbl_to_text
from s4lt.editor.preview import can_preview, get_preview_png
from s4lt import __version__

router = APIRouter(prefix="/package", tags=["package"])
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

# Resource type IDs
TYPE_TUNING = 0x0333406C
TYPE_STBL = 0x220557DA


def parse_tgi(tgi: str) -> tuple[int, int, int]:
    """Parse TGI string into (type_id, group_id, instance_id)."""
    parts = tgi.split(":")
    if len(parts) != 3:
        raise HTTPException(status_code=400, detail="Invalid TGI format")
    try:
        return (int(parts[0], 16), int(parts[1], 16), int(parts[2], 16))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid TGI format: hex values required")


# API endpoints - must come BEFORE view routes (more specific routes first)
@router.post("/{path:path}/resource/{tgi}/save")
async def save_resource(request: Request, path: str, tgi: str):
    """Save resource changes."""
    decoded_path = unquote(path)
    pkg_path = Path(decoded_path)

    if not pkg_path.exists():
        raise HTTPException(status_code=404, detail="Package not found")

    form = await request.form()
    content = form.get("content", "")

    session = get_session(str(pkg_path))
    type_id, group_id, instance_id = parse_tgi(tgi)

    # Convert content back to bytes
    if type_id == TYPE_TUNING:
        data = content.encode("utf-8")
    elif type_id == TYPE_STBL:
        from s4lt.editor.stbl import text_to_stbl, build_stbl, STBLError
        try:
            entries = text_to_stbl(content)
            data = build_stbl(entries)
        except STBLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid STBL format: {e}")
    else:
        raise HTTPException(status_code=400, detail="Cannot edit this resource type")

    # Update resource
    session.update_resource(type_id, group_id, instance_id, data)

    return {"status": "updated", "has_changes": session.has_unsaved_changes}


@router.delete("/{path:path}/resource/{tgi}")
async def delete_resource(path: str, tgi: str):
    """Delete a resource."""
    decoded_path = unquote(path)
    pkg_path = Path(decoded_path)

    if not pkg_path.exists():
        raise HTTPException(status_code=404, detail="Package not found")

    session = get_session(str(pkg_path))
    type_id, group_id, instance_id = parse_tgi(tgi)

    session.delete_resource(type_id, group_id, instance_id)

    return {"status": "deleted"}


@router.get("/{path:path}/extract/{tgi}")
async def extract_resource(path: str, tgi: str):
    """Extract/download a resource."""
    decoded_path = unquote(path)
    pkg_path = Path(decoded_path)

    if not pkg_path.exists():
        raise HTTPException(status_code=404, detail="Package not found")

    session = get_session(str(pkg_path))
    type_id, group_id, instance_id = parse_tgi(tgi)

    for res in session.resources:
        if res.type_id == type_id and res.group_id == group_id and res.instance_id == instance_id:
            data = res.extract()
            filename = f"{res.type_name}_{instance_id:016X}.bin"

            return StreamingResponse(
                io.BytesIO(data),
                media_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

    raise HTTPException(status_code=404, detail="Resource not found")


@router.post("/{path:path}/save")
async def save_package(path: str):
    """Save all pending changes."""
    decoded_path = unquote(path)
    pkg_path = Path(decoded_path)

    if not pkg_path.exists():
        raise HTTPException(status_code=404, detail="Package not found")

    session = get_session(str(pkg_path))
    session.save()

    return {"status": "saved"}


@router.get("/{path:path}/resource/{tgi}/preview")
async def get_resource_preview(path: str, tgi: str):
    """Get preview image for a resource."""
    decoded_path = unquote(path)
    pkg_path = Path(decoded_path)

    if not pkg_path.exists():
        raise HTTPException(status_code=404, detail="Package not found")

    session = get_session(str(pkg_path))

    type_id, group_id, instance_id = parse_tgi(tgi)

    for res in session.resources:
        if res.type_id == type_id and res.group_id == group_id and res.instance_id == instance_id:
            if not can_preview(type_id):
                raise HTTPException(status_code=400, detail="Resource type not previewable")

            data = res.extract()
            png_data = get_preview_png(data, type_id)

            if png_data is None:
                raise HTTPException(status_code=500, detail="Failed to generate preview")

            return Response(content=png_data, media_type="image/png")

    raise HTTPException(status_code=404, detail="Resource not found")


# View routes - less specific, must come AFTER API routes
@router.get("/{path:path}/resource/{tgi}")
async def view_resource(request: Request, path: str, tgi: str):
    """View/edit a single resource."""
    decoded_path = unquote(path)
    pkg_path = Path(decoded_path)

    if not pkg_path.exists():
        raise HTTPException(status_code=404, detail="Package not found")

    session = get_session(str(pkg_path))
    type_id, group_id, instance_id = parse_tgi(tgi)

    # Find resource
    resource = None
    for res in session.resources:
        if res.type_id == type_id and res.group_id == group_id and res.instance_id == instance_id:
            resource = res
            break

    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    # Extract and process data
    data = resource.extract()
    content = None
    content_type = "binary"
    validation_errors = []

    if type_id == TYPE_TUNING:
        # XML tuning
        content_type = "xml"
        try:
            content = data.decode("utf-8")
            content = format_xml(content)
            validation_errors = validate_tuning(content)
        except UnicodeDecodeError:
            content = data.hex()
            content_type = "hex"

    elif type_id == TYPE_STBL:
        # String table
        content_type = "stbl"
        try:
            entries = parse_stbl(data)
            content = stbl_to_text(entries)
        except Exception as e:
            content = f"Error parsing STBL: {e}"
            content_type = "error"

    else:
        # Binary - show hex dump
        content_type = "hex"
        content = data[:512].hex()  # First 512 bytes

    return templates.TemplateResponse(
        request,
        "package/resource.html",
        {
            "active": "package",
            "version": __version__,
            "path": str(pkg_path),
            "filename": pkg_path.name,
            "tgi": tgi,
            "resource": {
                "type_id": type_id,
                "type_name": resource.type_name,
                "group_id": group_id,
                "instance_id": instance_id,
                "size": resource.uncompressed_size,
                "compressed": resource.is_compressed,
            },
            "content": content,
            "content_type": content_type,
            "validation_errors": validation_errors,
            "can_preview": can_preview(type_id),
        },
    )


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
