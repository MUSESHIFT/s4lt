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
