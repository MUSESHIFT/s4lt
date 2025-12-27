"""Tray command implementations."""

import json
import sys
from pathlib import Path

import click

from s4lt.cli.output import (
    console,
    print_success,
    print_error,
    print_warning,
)
from s4lt.config import find_tray_folder, get_settings, save_settings
from s4lt.tray import discover_tray_items, TrayItem, TrayItemType


def run_tray_list(
    item_type: str | None = None,
    json_output: bool = False,
):
    """List all tray items."""
    settings = get_settings()

    # Find tray folder
    if settings.tray_path is None:
        if json_output:
            print(json.dumps({"error": "Tray folder not configured"}))
            sys.exit(1)

        console.print("\n[bold]Tray Folder Setup[/bold]\n")

        tray_path = find_tray_folder()
        if tray_path:
            console.print(f"Found Tray folder: [cyan]{tray_path}[/cyan]")
            if click.confirm("Use this path?", default=True):
                settings.tray_path = tray_path
            else:
                path_str = click.prompt("Enter Tray folder path")
                settings.tray_path = Path(path_str)
        else:
            console.print("[yellow]Could not auto-detect Tray folder.[/yellow]")
            path_str = click.prompt("Enter Tray folder path")
            settings.tray_path = Path(path_str)

        if not settings.tray_path.is_dir():
            print_error(f"Path does not exist: {settings.tray_path}")
            sys.exit(1)

        save_settings(settings)
        console.print("[green]Saved configuration.[/green]\n")

    tray_path = settings.tray_path

    # Discover tray items
    if not json_output:
        console.print(f"[bold]Scanning[/bold] {tray_path}\n")

    discovered = discover_tray_items(tray_path)

    # Filter by type if specified
    if item_type:
        type_filter = {
            "household": TrayItemType.HOUSEHOLD,
            "lot": TrayItemType.LOT,
            "room": TrayItemType.ROOM,
        }.get(item_type.lower())

        if type_filter:
            discovered = [d for d in discovered if d["type"] == type_filter]

    # Load full TrayItem objects for names
    items = []
    for d in discovered:
        try:
            item = TrayItem.from_path(tray_path, d["id"])
            items.append({
                "id": item.id,
                "name": item.name,
                "type": item.item_type.value,
                "files": len(item.files),
                "thumbnails": len(item.list_thumbnails()),
            })
        except Exception as e:
            items.append({
                "id": d["id"],
                "name": "(error loading)",
                "type": d["type"].value if d["type"] else "unknown",
                "files": len(d.get("files", [])),
                "error": str(e),
            })

    if json_output:
        print(json.dumps({"items": items, "total": len(items)}))
        return

    # Display results
    if not items:
        print_warning("No tray items found.")
        return

    # Group by type
    households = [i for i in items if i["type"] == "household"]
    lots = [i for i in items if i["type"] == "lot"]
    rooms = [i for i in items if i["type"] == "room"]
    other = [i for i in items if i["type"] not in ("household", "lot", "room")]

    print_success(f"Found {len(items)} tray items")
    console.print()

    if households:
        console.print(f"[bold cyan]Households ({len(households)})[/bold cyan]")
        for h in households:
            console.print(f"  {h['name']}")
        console.print()

    if lots:
        console.print(f"[bold green]Lots ({len(lots)})[/bold green]")
        for lot in lots:
            console.print(f"  {lot['name']}")
        console.print()

    if rooms:
        console.print(f"[bold yellow]Rooms ({len(rooms)})[/bold yellow]")
        for r in rooms:
            console.print(f"  {r['name']}")
        console.print()

    if other:
        console.print(f"[dim]Unknown ({len(other)})[/dim]")
        for o in other:
            console.print(f"  {o['id']}")


def run_tray_export(
    name_or_id: str,
    output_dir: str | None = None,
    include_thumb: bool = True,
):
    """Export a tray item to a directory."""
    settings = get_settings()

    if settings.tray_path is None:
        print_error("Tray folder not configured. Run 's4lt tray list' first.")
        sys.exit(1)

    tray_path = settings.tray_path

    # Find the item
    discovered = discover_tray_items(tray_path)

    target = None
    for d in discovered:
        if d["id"] == name_or_id:
            target = d
            break
        try:
            item = TrayItem.from_path(tray_path, d["id"])
            if item.name.lower() == name_or_id.lower():
                target = d
                break
        except Exception:
            pass

    if not target:
        print_error(f"Tray item not found: {name_or_id}")
        sys.exit(1)

    # Load the full item
    item = TrayItem.from_path(tray_path, target["id"])

    # Determine output directory
    if output_dir:
        out_path = Path(output_dir)
    else:
        # Use item name, sanitized
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in item.name)
        out_path = Path.cwd() / safe_name

    out_path.mkdir(parents=True, exist_ok=True)

    # Copy all files
    console.print(f"Exporting [bold]{item.name}[/bold] to {out_path}")

    import shutil
    for f in item.files:
        dest = out_path / f.name
        shutil.copy2(f, dest)
        console.print(f"  Copied {f.name}")

    # Optionally export primary thumbnail as readable image
    if include_thumb:
        data, fmt = item.get_primary_thumbnail()
        if data:
            thumb_path = out_path / f"thumbnail.{fmt}"
            thumb_path.write_bytes(data)
            console.print(f"  Saved thumbnail.{fmt}")

    print_success(f"Exported {len(item.files)} files")


def run_tray_info(name_or_id: str, json_output: bool = False):
    """Show detailed information about a tray item."""
    settings = get_settings()

    if settings.tray_path is None:
        if json_output:
            print(json.dumps({"error": "Tray folder not configured"}))
        else:
            print_error("Tray folder not configured. Run 's4lt tray list' first.")
        sys.exit(1)

    tray_path = settings.tray_path

    # Find the item
    discovered = discover_tray_items(tray_path)

    target = None
    for d in discovered:
        if d["id"] == name_or_id:
            target = d
            break
        try:
            item = TrayItem.from_path(tray_path, d["id"])
            if item.name.lower() == name_or_id.lower():
                target = d
                break
        except Exception:
            pass

    if not target:
        if json_output:
            print(json.dumps({"error": f"Tray item not found: {name_or_id}"}))
        else:
            print_error(f"Tray item not found: {name_or_id}")
        sys.exit(1)

    # Load full item
    item = TrayItem.from_path(tray_path, target["id"])

    info = {
        "id": item.id,
        "name": item.name,
        "type": item.item_type.value,
        "files": [str(f.name) for f in item.files],
        "file_count": len(item.files),
        "thumbnails": [str(f.name) for f in item.list_thumbnails()],
        "has_thumbnail": len(item.list_thumbnails()) > 0,
    }

    if json_output:
        print(json.dumps(info))
        return

    console.print(f"\n[bold]{item.name}[/bold]")
    console.print(f"  Type: [cyan]{item.item_type.value}[/cyan]")
    console.print(f"  ID: [dim]{item.id}[/dim]")
    console.print()

    console.print("[bold]Files:[/bold]")
    for f in sorted(item.files, key=lambda x: x.suffix):
        size = f.stat().st_size
        console.print(f"  {f.name} ({size:,} bytes)")

    console.print()
    thumbs = item.list_thumbnails()
    if thumbs:
        console.print(f"[bold]Thumbnails:[/bold] {len(thumbs)} available")
    else:
        console.print("[dim]No thumbnails found[/dim]")


def run_tray_cc(
    name_or_id: str,
    verbose: bool = False,
    json_output: bool = False,
):
    """Show CC usage for a tray item."""
    from s4lt.tray.cc_tracker import get_cc_summary
    from s4lt.ea import init_ea_db, get_ea_db_path
    from s4lt.db.schema import get_connection
    from s4lt.config.settings import DB_PATH

    settings = get_settings()

    if settings.tray_path is None:
        print_error("Tray folder not configured. Run 's4lt tray list' first.")
        sys.exit(1)

    tray_path = settings.tray_path

    # Check EA index
    ea_db_path = get_ea_db_path()
    if not ea_db_path.exists():
        if not json_output:
            print_warning("EA content not indexed. Run 's4lt ea scan' first.")
            print_warning("Without EA index, all non-mod TGIs show as 'unknown'.")
            if not click.confirm("Continue anyway?", default=False):
                sys.exit(0)

    # Find the item
    discovered = discover_tray_items(tray_path)
    target = None

    for d in discovered:
        if d["id"] == name_or_id:
            target = d
            break
        try:
            item = TrayItem.from_path(tray_path, d["id"])
            if item.name.lower() == name_or_id.lower():
                target = d
                break
        except Exception:
            pass

    if not target:
        if json_output:
            print(json.dumps({"error": f"Tray item not found: {name_or_id}"}))
        else:
            print_error(f"Tray item not found: {name_or_id}")
        sys.exit(1)

    # Load item and analyze
    item = TrayItem.from_path(tray_path, target["id"])

    # Connect to databases
    ea_conn = init_ea_db(ea_db_path) if ea_db_path.exists() else None
    mods_conn = get_connection(DB_PATH) if DB_PATH.exists() else None

    if ea_conn is None and mods_conn is None:
        print_error("No indexes available. Run 's4lt scan' and 's4lt ea scan' first.")
        sys.exit(1)

    # Get summary
    if mods_conn:
        summary = get_cc_summary(item, ea_conn, mods_conn)
    else:
        summary = {"mods": {}, "missing_count": 0, "ea_count": 0, "total": 0}

    if json_output:
        print(json.dumps({
            "name": item.name,
            "id": item.id,
            "type": item.item_type.value,
            "cc": summary,
        }))
    else:
        console.print(f"\n[bold]{item.name}[/bold]")
        console.print(f"  Type: [cyan]{item.item_type.value}[/cyan]")
        console.print()

        if summary["mods"]:
            console.print("[bold]CC Usage:[/bold]")
            for mod_name, count in sorted(summary["mods"].items()):
                console.print(f"  {count} items from [cyan]{mod_name}[/cyan]")
        else:
            console.print("[dim]No CC detected[/dim]")

        if summary["missing_count"] > 0:
            console.print(f"\n[red]Warning: {summary['missing_count']} missing CC items[/red]")

        if verbose:
            console.print(f"\n[dim]EA resources: {summary['ea_count']}[/dim]")
            console.print(f"[dim]Total TGIs: {summary['total']}[/dim]")

    if ea_conn:
        ea_conn.close()
    if mods_conn:
        mods_conn.close()
