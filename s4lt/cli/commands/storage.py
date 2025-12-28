"""Storage management commands."""

from pathlib import Path

import click

from s4lt.cli.output import console
from s4lt.config.paths import find_mods_folder
from s4lt.deck.storage import (
    get_storage_summary,
    get_sd_card_path,
    list_removable_drives,
    move_to_sd,
    move_to_internal,
)


@click.command("summary")
def storage_summary():
    """Show storage summary."""
    mods_path = find_mods_folder()
    if mods_path is None:
        console.print("[red]Mods folder not found.[/red]")
        raise SystemExit(1)

    sd_path = get_sd_card_path()
    summary = get_storage_summary(mods_path, sd_path)

    console.print("[bold]Storage Summary[/bold]")
    console.print("=" * 40)
    console.print(f"Internal: {summary.internal_used_gb:.1f} GB mods ({summary.internal_free_gb:.0f} GB free)")

    if sd_path:
        drives = list_removable_drives()
        sd_name = drives[0].name if drives else "SD Card"
        console.print(f"{sd_name}: {summary.sd_used_gb:.1f} GB mods ({summary.sd_free_gb:.0f} GB free)")
        if summary.symlink_count > 0:
            console.print(f"\n{summary.symlink_count} mod(s) symlinked to SD card")
    else:
        console.print("No SD card detected")


@click.command()
@click.argument("path")
@click.option("--to-sd", is_flag=True, help="Move to SD card")
@click.option("--to-internal", is_flag=True, help="Move to internal storage")
def move(path: str, to_sd: bool, to_internal: bool):
    """Move a mod between internal and SD card."""
    if not to_sd and not to_internal:
        console.print("[red]Specify --to-sd or --to-internal[/red]")
        raise SystemExit(1)

    if to_sd and to_internal:
        console.print("[red]Cannot specify both --to-sd and --to-internal[/red]")
        raise SystemExit(1)

    mod_path = Path(path)
    if not mod_path.exists():
        console.print(f"[red]Path not found: {path}[/red]")
        raise SystemExit(1)

    if to_sd:
        sd_path = get_sd_card_path()
        if sd_path is None:
            console.print("[red]No SD card detected[/red]")
            raise SystemExit(1)

        sd_mods_path = sd_path / "S4LT"
        result = move_to_sd([mod_path], sd_mods_path)

        if result.all_succeeded:
            console.print(f"[green]Moved {mod_path.name} to SD card ({result.bytes_moved / 1_000_000:.1f} MB)[/green]")
        else:
            console.print(f"[red]Failed to move {mod_path.name}[/red]")
            raise SystemExit(1)

    else:  # to_internal
        mods_path = find_mods_folder()
        if mods_path is None:
            console.print("[red]Mods folder not found[/red]")
            raise SystemExit(1)

        result = move_to_internal([mod_path], mods_path)

        if result.all_succeeded:
            console.print(f"[green]Moved {mod_path.name} to internal ({result.bytes_moved / 1_000_000:.1f} MB)[/green]")
        else:
            console.print(f"[red]Failed to move {mod_path.name}[/red]")
            raise SystemExit(1)
