"""Info command implementation."""

import sys
from collections import Counter
from pathlib import Path

from rich.panel import Panel
from rich.tree import Tree

from s4lt.cli.output import console, format_size, print_warning, print_error
from s4lt.config import get_settings
from s4lt.config.settings import DB_PATH
from s4lt.db import get_connection


def run_info(package: str):
    """Run the info command."""
    if not DB_PATH.exists():
        print_warning("No scan data. Run 's4lt scan' first.")
        sys.exit(1)

    settings = get_settings()
    if not settings.mods_path:
        print_warning("Mods folder not configured. Run 's4lt scan' first.")
        sys.exit(1)

    conn = get_connection(DB_PATH)

    try:
        # Find the mod - try exact path first, then search by filename
        cursor = conn.execute(
            "SELECT * FROM mods WHERE path = ? OR filename = ?",
            (package, package),
        )
        mod = cursor.fetchone()

        if not mod:
            # Try partial match
            cursor = conn.execute(
                "SELECT * FROM mods WHERE path LIKE ? OR filename LIKE ?",
                (f"%{package}%", f"%{package}%"),
            )
            mod = cursor.fetchone()

        if not mod:
            print_error(f"Package not found: {package}")
            sys.exit(1)

        mod = dict(mod)

        # Get resources
        cursor = conn.execute(
            "SELECT * FROM resources WHERE mod_id = ?",
            (mod["id"],),
        )
        resources = [dict(r) for r in cursor.fetchall()]

        # Count by type
        type_counts = Counter(r["type_name"] or "Unknown" for r in resources)

        # Find conflicts
        cursor = conn.execute("""
            SELECT DISTINCT m2.path
            FROM resources r1
            JOIN resources r2 ON r1.type_id = r2.type_id
                AND r1.group_id = r2.group_id
                AND r1.instance_id = r2.instance_id
            JOIN mods m2 ON r2.mod_id = m2.id
            WHERE r1.mod_id = ? AND r2.mod_id != ? AND m2.broken = 0
        """, (mod["id"], mod["id"]))
        conflicting_mods = [r[0] for r in cursor.fetchall()]

        # Display
        console.print()
        console.print(f"[bold]📦 {mod['filename']}[/bold]")
        console.print(f"   Path: [cyan]{mod['path']}[/cyan]")
        console.print(f"   Size: {format_size(mod['size'])}")
        console.print(f"   Resources: {mod['resource_count']}")

        if mod["broken"]:
            console.print(f"   [red]BROKEN: {mod['error_message']}[/red]")

        console.print()
        console.print("   [bold]Contents:[/bold]")
        tree = Tree("   ")
        for type_name, count in type_counts.most_common():
            # Get example names for this type
            names = [r["name"] for r in resources if r["type_name"] == type_name and r["name"]][:3]
            name_str = f' - "{", ".join(names)}"...' if names else ""
            tree.add(f"{type_name} ({count}){name_str}")
        console.print(tree)

        if conflicting_mods:
            console.print()
            console.print(f"   [yellow]⚠ Conflicts with:[/yellow]")
            for cmod in conflicting_mods[:5]:
                console.print(f"      [cyan]{cmod}[/cyan]")
            if len(conflicting_mods) > 5:
                console.print(f"      ... and {len(conflicting_mods) - 5} more")

        console.print()

    finally:
        conn.close()
