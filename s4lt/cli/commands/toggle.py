"""Enable/disable/vanilla command implementations."""

from pathlib import Path

from s4lt.cli.output import console
from s4lt.config.settings import get_settings
from s4lt.db.schema import get_connection, init_db


def run_enable(pattern: str | None) -> None:
    """Run the enable command."""
    from s4lt.organize.batch import batch_enable

    settings = get_settings()
    mods_path = Path(settings.paths.mods)

    result = batch_enable(mods_path, pattern=pattern or "**/*.disabled")

    if result.changed == 0:
        console.print("[yellow]No mods to enable.[/yellow]")
    else:
        console.print(f"[green]Enabled {result.changed} mods.[/green]")


def run_disable(pattern: str | None) -> None:
    """Run the disable command."""
    from s4lt.organize.batch import batch_disable

    settings = get_settings()
    mods_path = Path(settings.paths.mods)

    result = batch_disable(mods_path, pattern=pattern or "**/*.package")

    if result.changed == 0:
        console.print("[yellow]No mods to disable.[/yellow]")
    else:
        console.print(f"[green]Disabled {result.changed} mods.[/green]")


def run_vanilla() -> None:
    """Run the vanilla command."""
    from s4lt.organize.vanilla import toggle_vanilla, is_vanilla_mode

    settings = get_settings()
    mods_path = Path(settings.paths.mods)
    db_path = Path(settings.paths.data) / "s4lt.db"
    init_db(db_path)
    conn = get_connection(db_path)

    try:
        was_vanilla = is_vanilla_mode(conn)
        result = toggle_vanilla(conn, mods_path)

        if result.is_vanilla:
            console.print(f"[green]Entered vanilla mode.[/green] Disabled {result.mods_changed} mods.")
        else:
            console.print(f"[green]Exited vanilla mode.[/green] Restored {result.mods_changed} mods.")
    finally:
        conn.close()
