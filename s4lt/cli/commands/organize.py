"""Organize command implementation."""

import click
from pathlib import Path

from s4lt.cli.output import console
from s4lt.config.settings import get_settings
from s4lt.db.schema import get_connection, init_db


def run_organize(by_type: bool, by_creator: bool, yes: bool) -> None:
    """Run the organize command."""
    from s4lt.organize.sorter import organize_by_type, organize_by_creator

    settings = get_settings()
    mods_path = Path(settings.paths.mods)
    db_path = Path(settings.paths.data) / "s4lt.db"
    init_db(db_path)
    conn = get_connection(db_path)

    try:
        if by_type:
            result = organize_by_type(conn, mods_path, dry_run=True)
            action = "type"
        elif by_creator:
            result = organize_by_creator(conn, mods_path, dry_run=True)
            action = "creator"
        else:
            console.print("[red]Error: Specify --by-type or --by-creator[/red]")
            return

        if not result.moves:
            console.print("[green]All mods are already organized.[/green]")
            return

        # Show preview
        console.print(f"\n[bold]Will organize {len(result.moves)} mods by {action}:[/bold]\n")

        # Group by target folder
        by_folder: dict[Path, list] = {}
        for move in result.moves:
            folder = move.target.parent
            if folder not in by_folder:
                by_folder[folder] = []
            by_folder[folder].append(move)

        for folder, moves in sorted(by_folder.items()):
            console.print(f"  → {folder.name}/: {len(moves)} mods")

        if not yes:
            console.print()
            if not click.confirm("Proceed?"):
                console.print("[yellow]Cancelled.[/yellow]")
                return

        # Execute
        if by_type:
            result = organize_by_type(conn, mods_path, dry_run=False)
        else:
            result = organize_by_creator(conn, mods_path, dry_run=False)

        console.print(f"\n[green]Organized {len(result.moves)} mods.[/green]")
    finally:
        conn.close()
