"""EA content commands."""

import sys

import click

from s4lt.cli.output import console, print_success, print_error, print_warning
from s4lt.config import get_settings, save_settings
from s4lt.ea import (
    find_game_folder,
    validate_game_folder,
    init_ea_db,
    get_ea_db_path,
    EADatabase,
    scan_ea_content,
)


def run_ea_scan(game_path_arg: str | None = None):
    """Scan EA game content and build index."""
    from pathlib import Path
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

    settings = get_settings()

    # Determine game path
    if game_path_arg:
        game_path = Path(game_path_arg)
        if not validate_game_folder(game_path):
            print_error(f"Invalid game folder: {game_path}")
            print_error("Expected to find Data/Client/ClientFullBuild0.package")
            sys.exit(1)
    elif settings.game_path:
        game_path = settings.game_path
    else:
        console.print("\n[bold]Game Folder Setup[/bold]\n")

        game_path = find_game_folder()
        if game_path:
            console.print(f"Found game folder: [cyan]{game_path}[/cyan]")
            if not click.confirm("Use this path?", default=True):
                path_str = click.prompt("Enter game folder path")
                game_path = Path(path_str)
        else:
            console.print("[yellow]Could not auto-detect game folder.[/yellow]")
            console.print("Searching filesystem (this may take a minute)...")

            from s4lt.ea.paths import find_game_folder_search
            game_path = find_game_folder_search()

            if game_path:
                console.print(f"Found: [cyan]{game_path}[/cyan]")
                if not click.confirm("Use this path?", default=True):
                    path_str = click.prompt("Enter game folder path")
                    game_path = Path(path_str)
            else:
                path_str = click.prompt("Enter game folder path")
                game_path = Path(path_str)

        if not validate_game_folder(game_path):
            print_error(f"Invalid game folder: {game_path}")
            sys.exit(1)

        settings.game_path = game_path
        save_settings(settings)
        console.print("[green]Saved configuration.[/green]\n")

    # Initialize database
    db_path = get_ea_db_path()
    conn = init_ea_db(db_path)
    db = EADatabase(conn)

    # Check if already scanned
    existing = db.get_scan_info()
    if existing:
        console.print(f"[dim]Previous scan: {existing['resource_count']:,} resources[/dim]")
        if not click.confirm("Rescan?", default=False):
            conn.close()
            return
        # Clear existing data
        conn.execute("DELETE FROM ea_resources")
        conn.commit()

    console.print(f"\n[bold]Scanning[/bold] {game_path}\n")

    # Scan with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Scanning packages...", total=None)

        def update_progress(name: str, current: int, total: int):
            progress.update(task, description=f"[cyan]{name}[/cyan]", completed=current, total=total)

        pkg_count, res_count = scan_ea_content(game_path, db, update_progress)

    console.print()
    print_success(f"Indexed {res_count:,} resources from {pkg_count} packages")
    console.print(f"[dim]Saved to {db_path}[/dim]")

    conn.close()


def run_ea_status():
    """Show EA index status."""
    db_path = get_ea_db_path()

    if not db_path.exists():
        print_warning("EA content not indexed. Run 's4lt ea scan' first.")
        return

    conn = init_ea_db(db_path)
    db = EADatabase(conn)

    info = db.get_scan_info()
    if not info:
        print_warning("EA content not indexed. Run 's4lt ea scan' first.")
        conn.close()
        return

    console.print("\n[bold]EA Content Index[/bold]\n")
    console.print(f"  Game path: [cyan]{info['game_path']}[/cyan]")
    console.print(f"  Last scan: {info['last_scan']}")
    console.print(f"  Packages: {info['package_count']:,}")
    console.print(f"  Resources: {info['resource_count']:,}")
    console.print()

    conn.close()
