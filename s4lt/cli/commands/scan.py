"""Scan command implementation."""

import json
import sys
import time
from pathlib import Path

import click

from s4lt.cli.output import (
    console,
    format_size,
    create_progress,
    print_success,
    print_error,
    print_info,
)
from s4lt.config import find_mods_folder, get_settings, save_settings, Settings
from s4lt.config.settings import DATA_DIR, DB_PATH
from s4lt.db import init_db, get_connection, delete_mod
from s4lt.mods import discover_packages, categorize_changes, index_package


def run_scan(full: bool = False, stats_only: bool = False, json_output: bool = False):
    """Run the scan command."""
    settings = get_settings()

    # First run: find or configure mods path
    if settings.mods_path is None:
        if json_output:
            print(json.dumps({"error": "Mods folder not configured. Run without --json first."}))
            sys.exit(1)

        console.print("\n[bold]First Run Setup[/bold]\n")

        mods_path = find_mods_folder()
        if mods_path:
            console.print(f"Found Mods folder: [cyan]{mods_path}[/cyan]")
            if click.confirm("Use this path?", default=True):
                settings.mods_path = mods_path
            else:
                path_str = click.prompt("Enter Mods folder path")
                settings.mods_path = Path(path_str)
        else:
            console.print("[yellow]Could not auto-detect Mods folder.[/yellow]")
            path_str = click.prompt("Enter Mods folder path")
            settings.mods_path = Path(path_str)

        if not settings.mods_path.is_dir():
            print_error(f"Path does not exist: {settings.mods_path}")
            sys.exit(1)

        save_settings(settings)
        console.print(f"[green]Saved configuration to ~/.config/s4lt/config.toml[/green]\n")

    mods_path = settings.mods_path

    # Initialize database
    init_db(DB_PATH)
    conn = get_connection(DB_PATH)

    try:
        # Discover packages
        if not json_output:
            console.print(f"[bold]Scanning[/bold] {mods_path}\n")

        disk_files = set(discover_packages(
            mods_path,
            include_subfolders=settings.include_subfolders,
            ignore_patterns=settings.ignore_patterns,
        ))

        if full:
            # Force full rescan - treat all as new
            new_files = disk_files
            modified_files = set()
            deleted_paths = set()
        else:
            new_files, modified_files, deleted_paths = categorize_changes(conn, mods_path, disk_files)

        total_on_disk = len(disk_files)
        to_process = new_files | modified_files

        if stats_only:
            if json_output:
                stats = {
                    "total": total_on_disk,
                    "new": len(new_files),
                    "modified": len(modified_files),
                    "deleted": len(deleted_paths),
                }
                print(json.dumps(stats))
            else:
                console.print(f"  Total packages: [bold]{total_on_disk}[/bold]")
                console.print(f"  New: {len(new_files)}")
                console.print(f"  Modified: {len(modified_files)}")
                console.print(f"  Deleted: {len(deleted_paths)}")
            return

        # Process changes
        start_time = time.time()

        # Delete removed mods
        for path in deleted_paths:
            delete_mod(conn, path)

        # Index new/modified mods
        broken_count = 0
        if to_process:
            with create_progress() as progress:
                task = progress.add_task("Indexing...", total=len(to_process))

                for pkg_path in to_process:
                    result = index_package(conn, mods_path, pkg_path)
                    if result is None:
                        broken_count += 1
                    progress.advance(task)

        elapsed = time.time() - start_time

        # Get final stats
        cursor = conn.execute("SELECT COUNT(*) FROM mods WHERE broken = 0")
        total_mods = cursor.fetchone()[0]
        cursor = conn.execute("SELECT COUNT(*) FROM resources")
        total_resources = cursor.fetchone()[0]

        if json_output:
            result = {
                "total_mods": total_mods,
                "total_resources": total_resources,
                "new": len(new_files),
                "modified": len(modified_files),
                "deleted": len(deleted_paths),
                "broken": broken_count,
                "time_seconds": round(elapsed, 2),
            }
            print(json.dumps(result))
        else:
            console.print()
            print_success("Scan complete")
            console.print(f"  Total: [bold]{total_mods}[/bold] mods ({total_resources:,} resources)")
            console.print(f"  New: {len(new_files)} | Updated: {len(modified_files)} | Removed: {len(deleted_paths)} | Broken: {broken_count}")
            console.print(f"  Time: {elapsed:.1f}s")

    finally:
        conn.close()
