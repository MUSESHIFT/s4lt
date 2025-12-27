"""Conflicts command implementation."""

import json
import sys

from rich.tree import Tree

from s4lt.cli.output import console, print_info, print_warning
from s4lt.config.settings import DB_PATH
from s4lt.db import get_connection, init_db
from s4lt.mods.conflicts import find_conflicts


def run_conflicts(high_only: bool = False, json_output: bool = False):
    """Run the conflicts command."""
    if not DB_PATH.exists():
        if json_output:
            print(json.dumps({"error": "No scan data. Run 's4lt scan' first."}))
        else:
            print_warning("No scan data. Run 's4lt scan' first.")
        sys.exit(1)

    conn = get_connection(DB_PATH)

    try:
        clusters = find_conflicts(conn)

        if high_only:
            clusters = [c for c in clusters if c.severity == "high"]

        if json_output:
            result = []
            for cluster in clusters:
                result.append({
                    "severity": cluster.severity,
                    "mods": cluster.mods,
                    "resource_types": list(cluster.resource_types),
                    "resource_count": len(cluster.resources),
                })
            print(json.dumps(result))
            return

        if not clusters:
            print_info("No conflicts found!")
            return

        console.print(f"\n[bold]Found {len(clusters)} conflict cluster(s)[/bold]\n")

        for i, cluster in enumerate(clusters, 1):
            severity_color = {
                "high": "red",
                "medium": "yellow",
                "low": "blue",
            }[cluster.severity]

            header = f"[{severity_color}]{'⚠' if cluster.severity != 'low' else 'ℹ'}[/{severity_color}]  Conflict Cluster #{i} ([{severity_color}]{cluster.severity.upper()}[/{severity_color}]) - {len(cluster.mods)} mods, {len(cluster.resources)} resources"
            console.print(header)

            tree = Tree("   ")
            for mod in cluster.mods:
                tree.add(f"[cyan]{mod}[/cyan]")

            console.print(tree)
            console.print(f"   Shared: {', '.join(sorted(cluster.resource_types))}")
            console.print()

    finally:
        conn.close()
