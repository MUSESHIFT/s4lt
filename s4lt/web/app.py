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
