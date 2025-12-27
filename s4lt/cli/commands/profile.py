"""Profile command implementations."""

from datetime import datetime
from pathlib import Path

from s4lt.cli.output import console
from s4lt.config.settings import get_settings
from s4lt.db.schema import get_connection, init_db
from s4lt.organize.exceptions import ProfileNotFoundError, ProfileExistsError


def run_profile_list() -> None:
    """List all profiles."""
    from s4lt.organize.profiles import list_profiles

    settings = get_settings()
    db_path = Path(settings.paths.data) / "s4lt.db"
    init_db(db_path)
    conn = get_connection(db_path)

    try:
        profiles = list_profiles(conn)
        if not profiles:
            console.print("[yellow]No profiles saved.[/yellow]")
            return

        console.print("[bold]Saved profiles:[/bold]\n")
        for p in profiles:
            created = datetime.fromtimestamp(p.created_at).strftime("%Y-%m-%d %H:%M")
            auto_tag = " [dim](auto)[/dim]" if p.is_auto else ""
            console.print(f"  • {p.name}{auto_tag} - created {created}")
    finally:
        conn.close()


def run_profile_save(name: str) -> None:
    """Save current mod state as a profile."""
    from s4lt.organize.profiles import create_profile, save_profile_snapshot

    settings = get_settings()
    mods_path = Path(settings.paths.mods)
    db_path = Path(settings.paths.data) / "s4lt.db"
    init_db(db_path)
    conn = get_connection(db_path)

    try:
        try:
            profile = create_profile(conn, name)
        except ProfileExistsError:
            console.print(f"[red]Profile '{name}' already exists.[/red]")
            return

        count = save_profile_snapshot(conn, profile.id, mods_path)
        console.print(f"[green]Saved profile '{name}' with {count} mods.[/green]")
    finally:
        conn.close()


def run_profile_load(name: str) -> None:
    """Load a saved profile."""
    from s4lt.organize.profiles import switch_profile

    settings = get_settings()
    mods_path = Path(settings.paths.mods)
    db_path = Path(settings.paths.data) / "s4lt.db"
    init_db(db_path)
    conn = get_connection(db_path)

    try:
        try:
            result = switch_profile(conn, name, mods_path)
        except ProfileNotFoundError:
            console.print(f"[red]Profile '{name}' not found.[/red]")
            return

        console.print(f"[green]Loaded profile '{name}'.[/green]")
        console.print(f"  Enabled: {result.enabled}, Disabled: {result.disabled}")
    finally:
        conn.close()


def run_profile_delete(name: str) -> None:
    """Delete a saved profile."""
    from s4lt.organize.profiles import delete_profile

    settings = get_settings()
    db_path = Path(settings.paths.data) / "s4lt.db"
    init_db(db_path)
    conn = get_connection(db_path)

    try:
        try:
            delete_profile(conn, name)
            console.print(f"[green]Deleted profile '{name}'.[/green]")
        except ProfileNotFoundError:
            console.print(f"[red]Profile '{name}' not found.[/red]")
    finally:
        conn.close()
