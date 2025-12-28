"""FastAPI application factory."""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from s4lt.web.routers import dashboard, mods, tray, profiles, api, package, storage
from s4lt.deck.detection import is_steam_deck


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="S4LT",
        description="Sims 4 Linux Toolkit",
        version="0.4.0",
    )

    # Mount static files
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

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
    app.include_router(dashboard.router)
    app.include_router(mods.router)
    app.include_router(tray.router)
    app.include_router(profiles.router)
    app.include_router(api.router)
    app.include_router(package.router)
    app.include_router(storage.router)

    return app
