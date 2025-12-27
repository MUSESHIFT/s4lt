"""FastAPI application factory."""

from fastapi import FastAPI
from pathlib import Path

from s4lt.web.routers import dashboard, mods, tray, profiles, api, package


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
    app.include_router(package.router)

    return app
