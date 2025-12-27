# Phase 5: Web UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a web-based dashboard for S4LT using FastAPI backend with HTMX + TailwindCSS frontend.

**Architecture:** FastAPI serves both the API endpoints and HTML templates. HTMX handles dynamic updates without full page reloads. TailwindCSS via CDN for styling. SQLite database already exists from CLI.

**Tech Stack:** FastAPI, Jinja2 templates, HTMX, TailwindCSS (CDN), uvicorn

---

## Task 1: Add web dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Update pyproject.toml**

```toml
[project]
name = "s4lt"
version = "0.4.0"
description = "Sims 4 Linux Toolkit"
requires-python = ">=3.11"
dependencies = [
    "click>=8.0",
    "rich>=13.0",
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "jinja2>=3.1.0",
    "python-multipart>=0.0.6",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "httpx>=0.26.0"]

[project.scripts]
s4lt = "s4lt.cli.main:cli"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["s4lt*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
```

**Step 2: Install dependencies**

Run: `pip install -e ".[dev]"`

**Step 3: Verify installation**

Run: `python -c "import fastapi; import jinja2; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add web dependencies (FastAPI, Jinja2, uvicorn)"
```

---

## Task 2: Create web module structure

**Files:**
- Create: `s4lt/web/__init__.py`
- Create: `s4lt/web/app.py`
- Create: `s4lt/web/deps.py`
- Create: `tests/web/__init__.py`

**Step 1: Create web module**

`s4lt/web/__init__.py`:
```python
"""S4LT Web UI."""

from s4lt.web.app import create_app

__all__ = ["create_app"]
```

`s4lt/web/deps.py`:
```python
"""Dependency injection for web routes."""

import sqlite3
from pathlib import Path
from typing import Generator

from s4lt.config.settings import get_settings, DATA_DIR, DB_PATH
from s4lt.db.schema import init_db, get_connection


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Get database connection dependency."""
    init_db(DB_PATH)
    conn = get_connection(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def get_mods_path() -> Path | None:
    """Get mods path from settings."""
    settings = get_settings()
    return settings.mods_path


def get_tray_path() -> Path | None:
    """Get tray path from settings."""
    settings = get_settings()
    return settings.tray_path
```

`s4lt/web/app.py`:
```python
"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="S4LT",
        description="Sims 4 Linux Toolkit",
        version="0.4.0",
    )

    # Templates directory
    templates_dir = Path(__file__).parent / "templates"
    templates_dir.mkdir(exist_ok=True)

    return app
```

`tests/web/__init__.py`:
```python
"""Tests for web module."""
```

**Step 2: Verify import works**

Run: `python -c "from s4lt.web import create_app; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add s4lt/web/ tests/web/
git commit -m "feat(web): create module structure"
```

---

## Task 3: Create base template with TailwindCSS

**Files:**
- Create: `s4lt/web/templates/base.html`
- Create: `s4lt/web/templates/components/nav.html`

**Step 1: Create base template**

`s4lt/web/templates/base.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}S4LT{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <style>
        .htmx-indicator { display: none; }
        .htmx-request .htmx-indicator { display: inline; }
        .htmx-request.htmx-indicator { display: inline; }
    </style>
</head>
<body class="bg-gray-900 text-gray-100 min-h-screen">
    {% include "components/nav.html" %}

    <main class="container mx-auto px-4 py-8">
        {% block content %}{% endblock %}
    </main>

    <footer class="text-center text-gray-500 text-sm py-4">
        S4LT v{{ version }} - Sims 4 Linux Toolkit
    </footer>
</body>
</html>
```

`s4lt/web/templates/components/nav.html`:
```html
<nav class="bg-gray-800 border-b border-gray-700">
    <div class="container mx-auto px-4">
        <div class="flex items-center justify-between h-16">
            <a href="/" class="text-xl font-bold text-blue-400">S4LT</a>
            <div class="flex space-x-4">
                <a href="/" class="px-3 py-2 rounded hover:bg-gray-700 {% if active == 'dashboard' %}bg-gray-700{% endif %}">Dashboard</a>
                <a href="/mods" class="px-3 py-2 rounded hover:bg-gray-700 {% if active == 'mods' %}bg-gray-700{% endif %}">Mods</a>
                <a href="/tray" class="px-3 py-2 rounded hover:bg-gray-700 {% if active == 'tray' %}bg-gray-700{% endif %}">Tray</a>
                <a href="/profiles" class="px-3 py-2 rounded hover:bg-gray-700 {% if active == 'profiles' %}bg-gray-700{% endif %}">Profiles</a>
            </div>
        </div>
    </div>
</nav>
```

**Step 2: Commit**

```bash
git add s4lt/web/templates/
git commit -m "feat(web): add base template with TailwindCSS and HTMX"
```

---

## Task 4: Dashboard page with stats

**Files:**
- Create: `s4lt/web/routers/__init__.py`
- Create: `s4lt/web/routers/dashboard.py`
- Create: `s4lt/web/templates/dashboard.html`
- Modify: `s4lt/web/app.py`
- Create: `tests/web/test_dashboard.py`

**Step 1: Write the failing test**

`tests/web/test_dashboard.py`:
```python
"""Tests for dashboard routes."""

from fastapi.testclient import TestClient

from s4lt.web import create_app


def test_dashboard_returns_html():
    """Dashboard should return HTML page."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "S4LT" in response.text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/web/test_dashboard.py -v`
Expected: FAIL (no route defined)

**Step 3: Implement dashboard router**

`s4lt/web/routers/__init__.py`:
```python
"""Web routers."""
```

`s4lt/web/routers/dashboard.py`:
```python
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
        "dashboard.html",
        {
            "request": request,
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
```

`s4lt/web/templates/dashboard.html`:
```html
{% extends "base.html" %}

{% block title %}Dashboard - S4LT{% endblock %}

{% block content %}
<h1 class="text-3xl font-bold mb-8">Dashboard</h1>

<!-- Stats Grid -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
    <div class="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div class="text-gray-400 text-sm">Total Mods</div>
        <div class="text-3xl font-bold text-blue-400">{{ stats.total_mods }}</div>
    </div>
    <div class="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div class="text-gray-400 text-sm">Resources</div>
        <div class="text-3xl font-bold text-green-400">{{ "{:,}".format(stats.total_resources) }}</div>
    </div>
    <div class="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div class="text-gray-400 text-sm">Profiles</div>
        <div class="text-3xl font-bold text-purple-400">{{ stats.total_profiles }}</div>
    </div>
    <div class="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div class="text-gray-400 text-sm">Broken</div>
        <div class="text-3xl font-bold {% if stats.broken_mods > 0 %}text-red-400{% else %}text-gray-400{% endif %}">{{ stats.broken_mods }}</div>
    </div>
</div>

<!-- Status -->
<div class="bg-gray-800 rounded-lg p-6 border border-gray-700 mb-8">
    <h2 class="text-xl font-bold mb-4">Status</h2>
    <div class="space-y-2">
        <div class="flex justify-between">
            <span class="text-gray-400">Mods Folder:</span>
            <span class="text-gray-100">{{ mods_path }}</span>
        </div>
        <div class="flex justify-between">
            <span class="text-gray-400">Mode:</span>
            <span class="{% if is_vanilla %}text-yellow-400{% else %}text-green-400{% endif %}">
                {% if is_vanilla %}Vanilla{% else %}Normal{% endif %}
            </span>
        </div>
    </div>
</div>

<!-- Quick Actions -->
<div class="bg-gray-800 rounded-lg p-6 border border-gray-700">
    <h2 class="text-xl font-bold mb-4">Quick Actions</h2>
    <div class="flex flex-wrap gap-4">
        <button
            hx-post="/api/scan"
            hx-swap="none"
            class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded font-medium">
            <span class="htmx-indicator">Scanning...</span>
            <span>Scan Mods</span>
        </button>
        <button
            hx-post="/api/vanilla/toggle"
            hx-swap="outerHTML"
            hx-target="body"
            class="px-4 py-2 {% if is_vanilla %}bg-green-600 hover:bg-green-700{% else %}bg-yellow-600 hover:bg-yellow-700{% endif %} rounded font-medium">
            {% if is_vanilla %}Exit Vanilla Mode{% else %}Enter Vanilla Mode{% endif %}
        </button>
    </div>
</div>
{% endblock %}
```

Update `s4lt/web/app.py`:
```python
"""FastAPI application factory."""

from fastapi import FastAPI
from pathlib import Path

from s4lt.web.routers import dashboard


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="S4LT",
        description="Sims 4 Linux Toolkit",
        version="0.4.0",
    )

    # Include routers
    app.include_router(dashboard.router)

    return app
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/web/test_dashboard.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add s4lt/web/ tests/web/
git commit -m "feat(web): add dashboard with stats"
```

---

## Task 5: Mods browser page

**Files:**
- Create: `s4lt/web/routers/mods.py`
- Create: `s4lt/web/templates/mods.html`
- Create: `s4lt/web/templates/components/mod_row.html`
- Modify: `s4lt/web/app.py`
- Create: `tests/web/test_mods.py`

**Step 1: Write the failing test**

`tests/web/test_mods.py`:
```python
"""Tests for mods routes."""

from fastapi.testclient import TestClient

from s4lt.web import create_app


def test_mods_page_returns_html():
    """Mods page should return HTML."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/mods")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Mods" in response.text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/web/test_mods.py -v`
Expected: FAIL

**Step 3: Implement mods router**

`s4lt/web/routers/mods.py`:
```python
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
    if search:
        count_query += " AND filename LIKE ?"
    if category:
        count_query += " AND category = ?"

    cursor = conn.execute(count_query, params[:-2] if params else [])
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
        "mods.html",
        {
            "request": request,
            "active": "mods",
            "version": __version__,
            "mods": mods,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
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
```

`s4lt/web/templates/mods.html`:
```html
{% extends "base.html" %}

{% block title %}Mods Browser - S4LT{% endblock %}

{% block content %}
<div class="flex justify-between items-center mb-6">
    <h1 class="text-3xl font-bold">Mods Browser</h1>
    <span class="text-gray-400">{{ total }} mods</span>
</div>

<!-- Filters -->
<div class="bg-gray-800 rounded-lg p-4 border border-gray-700 mb-6">
    <form class="flex flex-wrap gap-4" method="get">
        <input
            type="text"
            name="search"
            value="{{ search }}"
            placeholder="Search mods..."
            class="px-4 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500">
        <select name="category" class="px-4 py-2 bg-gray-700 border border-gray-600 rounded">
            <option value="">All Categories</option>
            {% for cat, count in categories.items() %}
            <option value="{{ cat }}" {% if category == cat %}selected{% endif %}>{{ cat }} ({{ count }})</option>
            {% endfor %}
        </select>
        <button type="submit" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded">Filter</button>
    </form>
</div>

<!-- Mods Table -->
<div class="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
    <table class="w-full">
        <thead class="bg-gray-700">
            <tr>
                <th class="px-4 py-3 text-left">Filename</th>
                <th class="px-4 py-3 text-left">Category</th>
                <th class="px-4 py-3 text-left">Size</th>
                <th class="px-4 py-3 text-left">Resources</th>
                <th class="px-4 py-3 text-right">Actions</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-gray-700">
            {% for mod in mods %}
            <tr class="hover:bg-gray-750">
                <td class="px-4 py-3">
                    <div class="font-medium">{{ mod.filename }}</div>
                    <div class="text-sm text-gray-400">{{ mod.path }}</div>
                </td>
                <td class="px-4 py-3">
                    <span class="px-2 py-1 rounded text-sm
                        {% if mod.category == 'CAS' %}bg-pink-600
                        {% elif mod.category == 'BuildBuy' %}bg-blue-600
                        {% elif mod.category == 'Script' %}bg-purple-600
                        {% elif mod.category == 'Tuning' %}bg-green-600
                        {% else %}bg-gray-600{% endif %}">
                        {{ mod.category or 'Unknown' }}
                    </span>
                </td>
                <td class="px-4 py-3 text-gray-400">{{ "%.1f"|format(mod.size / 1024) }} KB</td>
                <td class="px-4 py-3 text-gray-400">{{ mod.resource_count or 0 }}</td>
                <td class="px-4 py-3 text-right">
                    <button
                        hx-post="/mods/{{ mod.id }}/toggle"
                        hx-swap="none"
                        class="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-sm">
                        Toggle
                    </button>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<!-- Pagination -->
{% if pages > 1 %}
<div class="flex justify-center gap-2 mt-6">
    {% if page > 1 %}
    <a href="?page={{ page - 1 }}&search={{ search }}&category={{ category }}"
       class="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded">Previous</a>
    {% endif %}
    <span class="px-4 py-2 text-gray-400">Page {{ page }} of {{ pages }}</span>
    {% if page < pages %}
    <a href="?page={{ page + 1 }}&search={{ search }}&category={{ category }}"
       class="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded">Next</a>
    {% endif %}
</div>
{% endif %}
{% endblock %}
```

Update `s4lt/web/app.py`:
```python
"""FastAPI application factory."""

from fastapi import FastAPI
from pathlib import Path

from s4lt.web.routers import dashboard, mods


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="S4LT",
        description="Sims 4 Linux Toolkit",
        version="0.4.0",
    )

    # Include routers
    app.include_router(dashboard.router)
    app.include_router(mods.router)

    return app
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/web/test_mods.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add s4lt/web/ tests/web/
git commit -m "feat(web): add mods browser with search and filtering"
```

---

## Task 6: Tray browser page

**Files:**
- Create: `s4lt/web/routers/tray.py`
- Create: `s4lt/web/templates/tray.html`
- Modify: `s4lt/web/app.py`
- Create: `tests/web/test_tray.py`

**Step 1: Write the failing test**

`tests/web/test_tray.py`:
```python
"""Tests for tray routes."""

from fastapi.testclient import TestClient

from s4lt.web import create_app


def test_tray_page_returns_html():
    """Tray page should return HTML."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/tray")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Tray" in response.text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/web/test_tray.py -v`
Expected: FAIL

**Step 3: Implement tray router**

`s4lt/web/routers/tray.py`:
```python
"""Tray browser routes."""

import sqlite3
import base64
from fastapi import APIRouter, Request, Depends, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response
from pathlib import Path

from s4lt.web.deps import get_db, get_tray_path
from s4lt.tray import discover_tray_items, TrayItem, extract_thumbnail
from s4lt import __version__

router = APIRouter(prefix="/tray", tags=["tray"])
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("")
async def tray_list(
    request: Request,
    item_type: str | None = None,
    search: str | None = None,
):
    """Render tray browser page."""
    tray_path = get_tray_path()

    items = []
    if tray_path and tray_path.exists():
        discoveries = discover_tray_items(tray_path)

        for disc in discoveries:
            try:
                item = TrayItem.from_discovery(disc)

                # Apply filters
                if item_type and item.item_type.value.lower() != item_type.lower():
                    continue
                if search and search.lower() not in item.name.lower():
                    continue

                items.append({
                    "id": item.item_id,
                    "name": item.name,
                    "type": item.item_type.value,
                    "has_thumbnail": bool(item.thumbnails),
                })
            except Exception:
                continue

    # Get type counts
    type_counts = {}
    for item in items:
        t = item["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    return templates.TemplateResponse(
        "tray.html",
        {
            "request": request,
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
            item = TrayItem.from_discovery(disc)
            if item.item_id == item_id and item.thumbnails:
                thumb_path = item.get_primary_thumbnail()
                if thumb_path:
                    data = extract_thumbnail(thumb_path)
                    return Response(content=data, media_type="image/png")
        except Exception:
            continue

    return Response(status_code=404)
```

`s4lt/web/templates/tray.html`:
```html
{% extends "base.html" %}

{% block title %}Tray Browser - S4LT{% endblock %}

{% block content %}
<div class="flex justify-between items-center mb-6">
    <h1 class="text-3xl font-bold">Tray Browser</h1>
    <span class="text-gray-400">{{ total }} items</span>
</div>

<!-- Info -->
<div class="bg-gray-800 rounded-lg p-4 border border-gray-700 mb-6">
    <div class="text-gray-400">Tray Path: {{ tray_path }}</div>
</div>

<!-- Filters -->
<div class="bg-gray-800 rounded-lg p-4 border border-gray-700 mb-6">
    <form class="flex flex-wrap gap-4" method="get">
        <input
            type="text"
            name="search"
            value="{{ search }}"
            placeholder="Search by name..."
            class="px-4 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500">
        <select name="item_type" class="px-4 py-2 bg-gray-700 border border-gray-600 rounded">
            <option value="">All Types</option>
            {% for t, count in type_counts.items() %}
            <option value="{{ t }}" {% if item_type == t %}selected{% endif %}>{{ t }} ({{ count }})</option>
            {% endfor %}
        </select>
        <button type="submit" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded">Filter</button>
    </form>
</div>

<!-- Tray Grid -->
<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
    {% for item in items %}
    <div class="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden hover:border-blue-500 transition-colors">
        <div class="aspect-square bg-gray-900 flex items-center justify-center">
            {% if item.has_thumbnail %}
            <img src="/tray/{{ item.id }}/thumbnail" alt="{{ item.name }}" class="w-full h-full object-cover">
            {% else %}
            <span class="text-gray-600 text-4xl">?</span>
            {% endif %}
        </div>
        <div class="p-3">
            <div class="font-medium truncate" title="{{ item.name }}">{{ item.name }}</div>
            <div class="text-sm text-gray-400">{{ item.type }}</div>
        </div>
    </div>
    {% endfor %}
</div>

{% if not items %}
<div class="text-center text-gray-500 py-12">
    <p>No tray items found.</p>
    <p class="text-sm mt-2">Make sure the tray path is configured correctly.</p>
</div>
{% endif %}
{% endblock %}
```

Update `s4lt/web/app.py`:
```python
"""FastAPI application factory."""

from fastapi import FastAPI

from s4lt.web.routers import dashboard, mods, tray


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="S4LT",
        description="Sims 4 Linux Toolkit",
        version="0.4.0",
    )

    # Include routers
    app.include_router(dashboard.router)
    app.include_router(mods.router)
    app.include_router(tray.router)

    return app
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/web/test_tray.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add s4lt/web/ tests/web/
git commit -m "feat(web): add tray browser with thumbnails"
```

---

## Task 7: Profiles page with switcher

**Files:**
- Create: `s4lt/web/routers/profiles.py`
- Create: `s4lt/web/templates/profiles.html`
- Modify: `s4lt/web/app.py`
- Create: `tests/web/test_profiles.py`

**Step 1: Write the failing test**

`tests/web/test_profiles.py`:
```python
"""Tests for profiles routes."""

from fastapi.testclient import TestClient

from s4lt.web import create_app


def test_profiles_page_returns_html():
    """Profiles page should return HTML."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/profiles")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Profiles" in response.text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/web/test_profiles.py -v`
Expected: FAIL

**Step 3: Implement profiles router**

`s4lt/web/routers/profiles.py`:
```python
"""Profile management routes."""

import sqlite3
from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pathlib import Path

from s4lt.web.deps import get_db, get_mods_path
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
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


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
        "profiles.html",
        {
            "request": request,
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
```

`s4lt/web/templates/profiles.html`:
```html
{% extends "base.html" %}

{% block title %}Profiles - S4LT{% endblock %}

{% block content %}
<div class="flex justify-between items-center mb-6">
    <h1 class="text-3xl font-bold">Profiles</h1>
</div>

<!-- Vanilla Mode -->
<div class="bg-gray-800 rounded-lg p-6 border border-gray-700 mb-6">
    <div class="flex justify-between items-center">
        <div>
            <h2 class="text-xl font-bold">Vanilla Mode</h2>
            <p class="text-gray-400 text-sm mt-1">
                {% if is_vanilla %}
                All mods are currently disabled. Exit to restore your previous setup.
                {% else %}
                Temporarily disable all mods to test without CC.
                {% endif %}
            </p>
        </div>
        <form action="/profiles/vanilla/toggle" method="post">
            <button type="submit" class="px-6 py-3 rounded font-medium
                {% if is_vanilla %}bg-green-600 hover:bg-green-700{% else %}bg-yellow-600 hover:bg-yellow-700{% endif %}">
                {% if is_vanilla %}Exit Vanilla Mode{% else %}Enter Vanilla Mode{% endif %}
            </button>
        </form>
    </div>
</div>

<!-- Create Profile -->
<div class="bg-gray-800 rounded-lg p-6 border border-gray-700 mb-6">
    <h2 class="text-xl font-bold mb-4">Create Profile</h2>
    <form action="/profiles/create" method="post" class="flex gap-4">
        <input
            type="text"
            name="name"
            placeholder="Profile name..."
            required
            class="flex-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500">
        <button type="submit" class="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded font-medium">
            Save Current State
        </button>
    </form>
</div>

<!-- Profiles List -->
<div class="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
    <table class="w-full">
        <thead class="bg-gray-700">
            <tr>
                <th class="px-4 py-3 text-left">Name</th>
                <th class="px-4 py-3 text-left">Created</th>
                <th class="px-4 py-3 text-right">Actions</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-gray-700">
            {% for profile in profiles %}
            <tr class="hover:bg-gray-750">
                <td class="px-4 py-3 font-medium">{{ profile.name }}</td>
                <td class="px-4 py-3 text-gray-400">{{ profile.created }}</td>
                <td class="px-4 py-3 text-right space-x-2">
                    <form action="/profiles/{{ profile.name }}/load" method="post" class="inline">
                        <button type="submit" class="px-3 py-1 bg-green-600 hover:bg-green-700 rounded text-sm">
                            Load
                        </button>
                    </form>
                    <form action="/profiles/{{ profile.name }}/delete" method="post" class="inline"
                          onsubmit="return confirm('Delete profile {{ profile.name }}?')">
                        <button type="submit" class="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-sm">
                            Delete
                        </button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    {% if not profiles %}
    <div class="text-center text-gray-500 py-8">
        <p>No profiles saved yet.</p>
        <p class="text-sm mt-2">Create a profile to save your current mod configuration.</p>
    </div>
    {% endif %}
</div>
{% endblock %}
```

Update `s4lt/web/app.py`:
```python
"""FastAPI application factory."""

from fastapi import FastAPI

from s4lt.web.routers import dashboard, mods, tray, profiles


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="S4LT",
        description="Sims 4 Linux Toolkit",
        version="0.4.0",
    )

    # Include routers
    app.include_router(dashboard.router)
    app.include_router(mods.router)
    app.include_router(tray.router)
    app.include_router(profiles.router)

    return app
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/web/test_profiles.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add s4lt/web/ tests/web/
git commit -m "feat(web): add profiles page with switcher"
```

---

## Task 8: API endpoints for HTMX actions

**Files:**
- Create: `s4lt/web/routers/api.py`
- Modify: `s4lt/web/app.py`
- Create: `tests/web/test_api.py`

**Step 1: Write the failing test**

`tests/web/test_api.py`:
```python
"""Tests for API routes."""

from fastapi.testclient import TestClient

from s4lt.web import create_app


def test_api_status():
    """API status endpoint should return JSON."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/status")

    assert response.status_code == 200
    data = response.json()
    assert "version" in data
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/web/test_api.py -v`
Expected: FAIL

**Step 3: Implement API router**

`s4lt/web/routers/api.py`:
```python
"""API endpoints for HTMX and JSON consumers."""

import sqlite3
from fastapi import APIRouter, Depends, BackgroundTasks
from pathlib import Path

from s4lt.web.deps import get_db, get_mods_path
from s4lt.organize.vanilla import toggle_vanilla, is_vanilla_mode
from s4lt import __version__

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/status")
async def get_status(conn: sqlite3.Connection = Depends(get_db)):
    """Get current system status."""
    cursor = conn.execute("SELECT COUNT(*) FROM mods WHERE broken = 0")
    total_mods = cursor.fetchone()[0]

    is_vanilla = is_vanilla_mode(conn)
    mods_path = get_mods_path()

    return {
        "version": __version__,
        "total_mods": total_mods,
        "is_vanilla": is_vanilla,
        "mods_configured": mods_path is not None,
    }


@router.post("/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    """Trigger a background mod scan."""
    from s4lt.config.settings import get_settings, DB_PATH
    from s4lt.db.schema import init_db, get_connection
    from s4lt.mods import discover_packages, categorize_changes, index_package

    settings = get_settings()
    if not settings.mods_path:
        return {"error": "Mods path not configured"}

    def do_scan():
        init_db(DB_PATH)
        conn = get_connection(DB_PATH)
        try:
            disk_files = set(discover_packages(settings.mods_path))
            new_files, modified_files, _ = categorize_changes(conn, settings.mods_path, disk_files)
            for pkg_path in new_files | modified_files:
                index_package(conn, settings.mods_path, pkg_path)
        finally:
            conn.close()

    background_tasks.add_task(do_scan)
    return {"status": "scanning"}


@router.post("/vanilla/toggle")
async def api_toggle_vanilla(conn: sqlite3.Connection = Depends(get_db)):
    """Toggle vanilla mode via API."""
    mods_path = get_mods_path()
    if not mods_path:
        return {"error": "Mods path not configured"}

    result = toggle_vanilla(conn, mods_path)
    return {
        "is_vanilla": result.is_vanilla,
        "mods_changed": result.mods_changed,
    }
```

Update `s4lt/web/app.py`:
```python
"""FastAPI application factory."""

from fastapi import FastAPI

from s4lt.web.routers import dashboard, mods, tray, profiles, api


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="S4LT",
        description="Sims 4 Linux Toolkit",
        version="0.4.0",
    )

    # Include routers
    app.include_router(dashboard.router)
    app.include_router(mods.router)
    app.include_router(tray.router)
    app.include_router(profiles.router)
    app.include_router(api.router)

    return app
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/web/test_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add s4lt/web/ tests/web/
git commit -m "feat(web): add API endpoints for HTMX actions"
```

---

## Task 9: CLI serve command

**Files:**
- Create: `s4lt/cli/commands/serve.py`
- Modify: `s4lt/cli/main.py`

**Step 1: Create serve command**

`s4lt/cli/commands/serve.py`:
```python
"""Serve command implementation."""

import click

from s4lt.cli.output import console


def run_serve(host: str, port: int, reload: bool) -> None:
    """Run the web server."""
    import uvicorn
    from s4lt.web import create_app

    console.print(f"\n[bold]Starting S4LT Web UI[/bold]")
    console.print(f"  URL: [cyan]http://{host}:{port}[/cyan]")
    console.print(f"  Press Ctrl+C to stop\n")

    uvicorn.run(
        "s4lt.web:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )
```

**Step 2: Add to main CLI**

Add to `s4lt/cli/main.py` before the `if __name__` block:

```python
@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Auto-reload on changes")
def serve(host: str, port: int, reload: bool):
    """Start the web UI server."""
    from s4lt.cli.commands.serve import run_serve
    run_serve(host=host, port=port, reload=reload)
```

**Step 3: Verify CLI works**

Run: `python -c "from s4lt.cli.main import cli; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add s4lt/cli/commands/serve.py s4lt/cli/main.py
git commit -m "feat(cli): add serve command for web UI"
```

---

## Task 10: Version bump and final verification

**Files:**
- Modify: `pyproject.toml`
- Modify: `s4lt/__init__.py`

**Step 1: Update versions to 0.5.0**

`pyproject.toml`: Change `version = "0.4.0"` to `version = "0.5.0"`

`s4lt/__init__.py`: Change `__version__ = "0.4.0"` to `__version__ = "0.5.0"`

**Step 2: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass

**Step 3: Verify web server starts**

Run: `timeout 5 python -c "from s4lt.web import create_app; app = create_app(); print('App created')" || true`
Expected: `App created`

**Step 4: Commit**

```bash
git add pyproject.toml s4lt/__init__.py
git commit -m "chore: bump version to v0.5.0

Phase 5: Web UI complete"
```

**Step 5: Create tag**

```bash
git tag -a v0.5.0 -m "Phase 5: Web UI

Features:
- FastAPI backend
- Dashboard with stats
- Mods browser with search/filter
- Tray browser with thumbnails
- Profile switcher
- Vanilla mode toggle
- HTMX for dynamic updates
- TailwindCSS styling
- CLI serve command"
```

---

## Summary

| Task | Description | Tests |
|------|-------------|-------|
| 1 | Add web dependencies | - |
| 2 | Create web module structure | - |
| 3 | Base template with TailwindCSS | - |
| 4 | Dashboard with stats | 1 |
| 5 | Mods browser | 1 |
| 6 | Tray browser | 1 |
| 7 | Profiles page | 1 |
| 8 | API endpoints | 1 |
| 9 | CLI serve command | - |
| 10 | Version bump | - |

**Total: 10 tasks, 5 new tests**

Run with: `s4lt serve` → Open http://127.0.0.1:8000
