"""FastAPI application factory."""

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from s4lt.web.routers import dashboard, mods, tray, profiles, api, package, storage, setup
from s4lt.web.paths import get_static_dir
from s4lt.deck.detection import is_steam_deck
from s4lt import __version__


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

    # Include routers
    app.include_router(setup.router)  # Setup first for first-run experience
    app.include_router(dashboard.router)
    app.include_router(mods.router)
    app.include_router(tray.router)
    app.include_router(profiles.router)
    app.include_router(api.router)
    app.include_router(package.router)
    app.include_router(storage.router)

    return app
