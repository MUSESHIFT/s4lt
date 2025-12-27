"""Duplicates command implementation."""

import json
import sys

from rich.tree import Tree

from s4lt.cli.output import console, format_size, print_info, print_warning
from s4lt.config.settings import DB_PATH
from s4lt.db import get_connection
from s4lt.mods.duplicates import find_duplicates


def run_duplicates(exact_only: bool = False, json_output: bool = False):
    """Run the duplicates command."""
    if not DB_PATH.exists():
        if json_output:
            print(json.dumps({"error": "No scan data. Run 's4lt scan' first."}))
        else:
            print_warning("No scan data. Run 's4lt scan' first.")
        sys.exit(1)

    conn = get_connection(DB_PATH)

    try:
        groups = find_duplicates(conn)

        if exact_only:
            groups = [g for g in groups if g.match_type == "exact"]

        if json_output:
            result = []
            for group in groups:
                result.append({
                    "match_type": group.match_type,
                    "mods": [{"path": m["path"], "size": m["size"]} for m in group.mods],
                    "wasted_bytes": group.wasted_bytes,
                })
            print(json.dumps(result))
            return

        if not groups:
            print_info("No duplicates found!")
            return

        total_wasted = sum(g.wasted_bytes for g in groups)
        console.print(f"\n[bold]Found {len(groups)} duplicate group(s)[/bold] (wasting {format_size(total_wasted)})\n")

        for i, group in enumerate(groups, 1):
            match_label = "Exact match" if group.match_type == "exact" else "Same content"
            header = f"[yellow]📦[/yellow] Duplicate Group #{i} - {match_label} ({len(group.mods)} files, wasting {format_size(group.wasted_bytes)})"
            console.print(header)

            tree = Tree("   ")
            for j, mod in enumerate(group.mods):
                label = "[dim](oldest)[/dim]" if j == 0 else "[dim](delete?)[/dim]"
                tree.add(f"[cyan]{mod['path']}[/cyan] ({format_size(mod['size'])}) {label}")

            console.print(tree)
            console.print()

    finally:
        conn.close()
