"""CC Browser routes."""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from s4lt.web.paths import get_templates_dir
from s4lt.web.deps import get_mods_path
from s4lt.mods.scanner import discover_packages
from s4lt.core.categorizer import (
    categorize_package,
    get_category_display_name,
    get_subcategory_display_name,
)
from s4lt.core.thumbnails import extract_thumbnail, get_placeholder_thumbnail
from s4lt import __version__

router = APIRouter(prefix="/cc", tags=["cc"])
templates = Jinja2Templates(directory=get_templates_dir())
logger = logging.getLogger(__name__)


@router.get("", response_class=HTMLResponse)
async def cc_browser(
    request: Request,
    type: Optional[str] = Query(None, description="Filter by category: cas, buildbuy"),
    search: Optional[str] = Query(None, description="Search by filename"),
    sort: Optional[str] = Query("name", description="Sort: name, size, date"),
):
    """CC Browser with thumbnail grid."""
    mods_path = get_mods_path()

    cc_items = []

    if mods_path and mods_path.exists():
        # Discover all packages
        packages = discover_packages(mods_path, include_scripts=False)

        for pkg_path in packages:
            # Get relative path for display
            try:
                rel_path = pkg_path.relative_to(mods_path)
            except ValueError:
                rel_path = pkg_path

            # Categorize
            category_info = categorize_package(pkg_path)

            # Apply type filter
            if type:
                if category_info and category_info.category != type:
                    continue

            # Apply search filter
            if search:
                if search.lower() not in pkg_path.name.lower():
                    continue

            # Get stats
            stat = pkg_path.stat()

            item = {
                "id": hash(str(pkg_path)) & 0xFFFFFFFF,  # Simple ID for API
                "path": str(pkg_path),
                "rel_path": str(rel_path),
                "filename": pkg_path.name,
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "mtime": stat.st_mtime,
                "category": category_info.category if category_info else "other",
                "subcategory": category_info.subcategory if category_info else "unknown",
                "category_display": get_category_display_name(
                    category_info.category if category_info else "other"
                ),
                "subcategory_display": get_subcategory_display_name(
                    category_info.subcategory if category_info else "unknown"
                ),
                "has_thumbnail": category_info.has_thumbnail if category_info else False,
                "resource_count": category_info.total_resources if category_info else 0,
            }
            cc_items.append(item)

    # Sort
    if sort == "size":
        cc_items.sort(key=lambda x: x["size"], reverse=True)
    elif sort == "date":
        cc_items.sort(key=lambda x: x["mtime"], reverse=True)
    else:
        cc_items.sort(key=lambda x: x["filename"].lower())

    # Count by category
    category_counts = {}
    for item in cc_items:
        cat = item["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return templates.TemplateResponse(
        "cc.html",
        {
            "request": request,
            "version": __version__,
            "cc_items": cc_items[:100],  # Limit for performance
            "total_count": len(cc_items),
            "category_counts": category_counts,
            "current_type": type,
            "current_search": search or "",
            "current_sort": sort,
        },
    )


@router.get("/thumbnail/{item_id}")
async def get_thumbnail(item_id: int, path: str):
    """Get thumbnail for a package."""
    try:
        pkg_path = Path(path)
        if not pkg_path.exists():
            return Response(
                content=get_placeholder_thumbnail(),
                media_type="image/png",
            )

        thumbnail = extract_thumbnail(pkg_path)
        if thumbnail:
            return Response(content=thumbnail, media_type="image/png")

        return Response(
            content=get_placeholder_thumbnail(),
            media_type="image/png",
        )

    except Exception as e:
        logger.warning(f"Thumbnail error: {e}")
        return Response(
            content=get_placeholder_thumbnail(),
            media_type="image/png",
        )


@router.get("/{item_id}", response_class=HTMLResponse)
async def cc_detail(request: Request, item_id: int, path: str):
    """Detail page for a single CC item."""
    mods_path = get_mods_path()

    pkg_path = Path(path)
    if not pkg_path.exists():
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Package not found", "version": __version__},
            status_code=404,
        )

    # Get relative path
    try:
        rel_path = pkg_path.relative_to(mods_path) if mods_path else pkg_path
    except ValueError:
        rel_path = pkg_path

    # Categorize and get details
    category_info = categorize_package(pkg_path)
    stat = pkg_path.stat()

    item = {
        "id": item_id,
        "path": str(pkg_path),
        "rel_path": str(rel_path),
        "filename": pkg_path.name,
        "folder": str(pkg_path.parent),
        "size": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "mtime": stat.st_mtime,
        "category": category_info.category if category_info else "other",
        "subcategory": category_info.subcategory if category_info else "unknown",
        "category_display": get_category_display_name(
            category_info.category if category_info else "other"
        ),
        "subcategory_display": get_subcategory_display_name(
            category_info.subcategory if category_info else "unknown"
        ),
        "resource_counts": category_info.resource_counts if category_info else {},
        "total_resources": category_info.total_resources if category_info else 0,
        "has_thumbnail": category_info.has_thumbnail if category_info else False,
    }

    return templates.TemplateResponse(
        "cc_detail.html",
        {
            "request": request,
            "version": __version__,
            "item": item,
        },
    )
