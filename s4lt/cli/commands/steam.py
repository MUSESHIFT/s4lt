"""Steam integration commands."""

import shutil
import sys

import click

from s4lt.cli.output import console
from s4lt.deck.steam import add_to_steam, remove_from_steam


@click.command()
def install():
    """Add S4LT to Steam library."""
    # Find s4lt executable
    exe_path = shutil.which("s4lt")
    if exe_path is None:
        exe_path = sys.executable.replace("python", "s4lt")

    if add_to_steam(exe_path):
        console.print("[green]Added S4LT to Steam library.[/green]")
        console.print("Restart Steam to see it in Game Mode.")
    else:
        console.print("[red]Failed to add to Steam. Is Steam installed?[/red]")
        raise SystemExit(1)


@click.command()
def uninstall():
    """Remove S4LT from Steam library."""
    if remove_from_steam():
        console.print("[green]Removed S4LT from Steam library.[/green]")
    else:
        console.print("[red]Failed to remove from Steam.[/red]")
        raise SystemExit(1)
