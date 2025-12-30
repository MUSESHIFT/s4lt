"""FastAPI application factory."""

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from s4lt.web.routers import dashboard, mods, tray, profiles, api, package, storage, setup, debug, cc, conflicts
from s4lt.web.paths import get_static_dir, get_templates_dir
from s4lt.deck.detection import is_steam_deck
from s4lt import __version__

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="S4LT",
        description="Sims 4 Linux Toolkit",
        version=__version__,
    )

    # Mount static files
    static_dir = get_static_dir()
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # First-run setup redirect middleware
    @app.middleware("http")
    async def setup_redirect_middleware(request: Request, call_next):
        # Skip for static files, setup pages, and API endpoints
        path = request.url.path
        skip_paths = ["/static/", "/setup", "/api/"]
        if any(path.startswith(p) for p in skip_paths):
            return await call_next(request)

        # Check if setup is needed
        if setup.needs_setup():
            return RedirectResponse("/setup", status_code=303)

        return await call_next(request)

    # Deck mode detection middleware
    @app.middleware("http")
    async def deck_mode_middleware(request: Request, call_next):
        response = await call_next(request)

        # Set deck_mode cookie on first visit
        if "deck_mode" not in request.cookies:
            deck_mode = "1" if is_steam_deck() else "0"
            response.set_cookie("deck_mode", deck_mode, max_age=31536000)

        return response

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Request failed: {request.url}", exc_info=exc)

        # Get log file path
        try:
            from s4lt.logging import get_log_file
            log_file = get_log_file()
            log_path = str(log_file) if log_file else "~/.local/share/s4lt/logs/"
        except ImportError:
            log_path = "~/.local/share/s4lt/logs/"

        # Return JSON for API requests
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=500,
                content={
                    "error": str(exc),
                    "path": str(request.url),
                    "log_file": log_path
                }
            )

        # Return HTML error page for browser requests
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error - S4LT</title>
            <style>
                body {{ font-family: system-ui, sans-serif; background: #1a1a2e; color: #eee; padding: 40px; }}
                .error-box {{ background: #2d2d44; border-radius: 8px; padding: 24px; max-width: 600px; margin: 0 auto; }}
                h1 {{ color: #ff6b6b; margin-top: 0; }}
                pre {{ background: #1a1a2e; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 12px; }}
                .log-path {{ background: #3d3d5c; padding: 8px 12px; border-radius: 4px; font-family: monospace; }}
                a {{ color: #4dabf7; }}
            </style>
        </head>
        <body>
            <div class="error-box">
                <h1>Something went wrong</h1>
                <p><strong>Error:</strong> {str(exc)}</p>
                <p><strong>Path:</strong> {request.url.path}</p>
                <p>Check the log file for details:</p>
                <p class="log-path">{log_path}</p>
                <p><a href="/">← Back to Dashboard</a> | <a href="/debug">View Debug Info</a></p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=500)

    # Include routers
    app.include_router(setup.router)  # Setup first for first-run experience
    app.include_router(dashboard.router)
    app.include_router(cc.router)  # CC Browser
    app.include_router(mods.router)
    app.include_router(tray.router)
    app.include_router(conflicts.router)  # Conflict detection
    app.include_router(profiles.router)
    app.include_router(api.router)
    app.include_router(package.router)
    app.include_router(storage.router)
    app.include_router(debug.router)  # Debug page

    return app
