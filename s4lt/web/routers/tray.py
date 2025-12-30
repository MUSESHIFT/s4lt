"""Tray browser routes."""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response

from s4lt.web.deps import get_tray_path
from s4lt.web.paths import get_templates_dir
from s4lt.tray import discover_tray_items, TrayItem, TrayItemType, extract_thumbnail
from s4lt.tray.trayitem import parse_trayitem
from s4lt import __version__

router = APIRouter(prefix="/tray", tags=["tray"])
templates = Jinja2Templates(directory=get_templates_dir())


@router.get("")
async def tray_list(
    request: Request,
    item_type: str | None = None,
    search: str | None = None,
):
    """Render tray browser page."""
    tray_path = get_tray_path()

    items = []
    type_counts: dict[str, int] = {}

    if tray_path and tray_path.exists():
        discoveries = discover_tray_items(tray_path)

        for disc in discoveries:
            try:
                # Get item type from discovery
                disc_type: TrayItemType = disc["type"]
                item_id: str = disc["id"]
                files: list[Path] = disc["files"]

                # Try to parse name from trayitem
                name = item_id
                try:
                    meta = parse_trayitem(disc["trayitem_path"])
                    name = meta.name
                except Exception:
                    pass

                # Check for thumbnails
                thumb_extensions = {".hhi", ".sgi", ".bpi", ".midi"}
                has_thumbnail = any(
                    f.suffix.lower() in thumb_extensions for f in files
                )

                type_value = disc_type.value

                # Count types before filtering
                type_counts[type_value] = type_counts.get(type_value, 0) + 1

                # Apply filters
                if item_type and type_value.lower() != item_type.lower():
                    continue
                if search and search.lower() not in name.lower():
                    continue

                items.append({
                    "id": item_id,
                    "name": name,
                    "type": type_value,
                    "has_thumbnail": has_thumbnail,
                })
            except Exception:
                continue

    return templates.TemplateResponse(
        request,
        "tray.html",
        {
            "active": "tray",
            "version": __version__,
            "items": items,
            "total": len(items),
            "item_type": item_type or "",
            "search": search or "",
            "type_counts": type_counts,
            "tray_path": str(tray_path) if tray_path else "Not configured",
        },
    )


@router.get("/{item_id}/thumbnail")
async def get_thumbnail(item_id: str):
    """Get thumbnail for a tray item."""
    tray_path = get_tray_path()
    if not tray_path:
        return Response(status_code=404)

    discoveries = discover_tray_items(tray_path)
    for disc in discoveries:
        try:
            if disc["id"] == item_id:
                files: list[Path] = disc["files"]
                # Find thumbnail files
                thumb_extensions = {".hhi", ".sgi", ".bpi", ".midi"}
                for f in files:
                    if f.suffix.lower() in thumb_extensions:
                        try:
                            data, fmt = extract_thumbnail(f)
                            if data:
                                return Response(content=data, media_type="image/png")
                        except Exception:
                            continue
        except Exception:
            continue

    return Response(status_code=404)
