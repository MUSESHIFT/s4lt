"""S4LT CLI main entry point."""

import click

from s4lt.cli.output import console


@click.group()
@click.version_option(package_name="s4lt")
def cli():
    """S4LT: Sims 4 Linux Toolkit.

    Native Linux tools for Sims 4 mod management.
    """
    pass


@cli.command()
@click.option("--full", is_flag=True, help="Force full rescan")
@click.option("--stats", is_flag=True, help="Show stats only, don't update")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def scan(full: bool, stats: bool, json_output: bool):
    """Scan and index the Mods folder."""
    from s4lt.cli.commands.scan import run_scan
    run_scan(full=full, stats_only=stats, json_output=json_output)


@cli.command()
@click.option("--high", is_flag=True, help="Show only high severity conflicts")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def conflicts(high: bool, json_output: bool):
    """Show mod conflicts."""
    from s4lt.cli.commands.conflicts import run_conflicts
    run_conflicts(high_only=high, json_output=json_output)


@cli.command()
@click.option("--exact", is_flag=True, help="Show only exact duplicates")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def duplicates(exact: bool, json_output: bool):
    """Find duplicate mods."""
    from s4lt.cli.commands.duplicates import run_duplicates
    run_duplicates(exact_only=exact, json_output=json_output)


@cli.command()
@click.argument("package")
def info(package: str):
    """Show package details."""
    from s4lt.cli.commands.info import run_info
    run_info(package)


@cli.group()
def tray():
    """Manage tray items (saved Sims, lots, rooms)."""
    pass


@tray.command("list")
@click.option("--type", "item_type", type=click.Choice(["household", "lot", "room"]),
              help="Filter by item type")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def tray_list(item_type: str | None, json_output: bool):
    """List all tray items."""
    from s4lt.cli.commands.tray import run_tray_list
    run_tray_list(item_type=item_type, json_output=json_output)


@tray.command("export")
@click.argument("name_or_id")
@click.option("--output", "-o", "output_dir", help="Output directory")
@click.option("--no-thumb", is_flag=True, help="Don't export thumbnail")
def tray_export(name_or_id: str, output_dir: str | None, no_thumb: bool):
    """Export a tray item to a directory."""
    from s4lt.cli.commands.tray import run_tray_export
    run_tray_export(name_or_id, output_dir, include_thumb=not no_thumb)


@tray.command("info")
@click.argument("name_or_id")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def tray_info(name_or_id: str, json_output: bool):
    """Show details about a tray item."""
    from s4lt.cli.commands.tray import run_tray_info
    run_tray_info(name_or_id, json_output=json_output)


@tray.command("cc")
@click.argument("name_or_id")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed info")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def tray_cc(name_or_id: str, verbose: bool, json_output: bool):
    """Show CC usage for a tray item."""
    from s4lt.cli.commands.tray import run_tray_cc
    run_tray_cc(name_or_id, verbose=verbose, json_output=json_output)


@cli.group()
def ea():
    """Manage EA content index (base game)."""
    pass


@ea.command("scan")
@click.option("--path", "game_path", help="Path to game folder")
def ea_scan(game_path: str | None):
    """Scan and index base game content."""
    from s4lt.cli.commands.ea import run_ea_scan
    run_ea_scan(game_path_arg=game_path)


@ea.command("status")
def ea_status():
    """Show EA index status."""
    from s4lt.cli.commands.ea import run_ea_status
    run_ea_status()


@cli.command()
@click.option("--by-type", is_flag=True, help="Sort by mod category")
@click.option("--by-creator", is_flag=True, help="Sort by creator name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def organize(by_type: bool, by_creator: bool, yes: bool):
    """Auto-sort mods into subfolders."""
    from s4lt.cli.commands.organize import run_organize
    run_organize(by_type=by_type, by_creator=by_creator, yes=yes)


@cli.command()
@click.argument("pattern", required=False)
def enable(pattern: str | None):
    """Enable disabled mods (remove .disabled suffix)."""
    from s4lt.cli.commands.toggle import run_enable
    run_enable(pattern=pattern)


@cli.command()
@click.argument("pattern", required=False)
def disable(pattern: str | None):
    """Disable mods (add .disabled suffix)."""
    from s4lt.cli.commands.toggle import run_disable
    run_disable(pattern=pattern)


@cli.command()
def vanilla():
    """Toggle vanilla mode (disable/restore all mods)."""
    from s4lt.cli.commands.toggle import run_vanilla
    run_vanilla()


@cli.group()
def profile():
    """Manage mod profiles."""
    pass


@profile.command("list")
def profile_list():
    """List saved profiles."""
    from s4lt.cli.commands.profile import run_profile_list
    run_profile_list()


@profile.command("save")
@click.argument("name")
def profile_save(name: str):
    """Save current mod state as a profile."""
    from s4lt.cli.commands.profile import run_profile_save
    run_profile_save(name)


@profile.command("load")
@click.argument("name")
def profile_load(name: str):
    """Load a saved profile."""
    from s4lt.cli.commands.profile import run_profile_load
    run_profile_load(name)


@profile.command("delete")
@click.argument("name")
def profile_delete(name: str):
    """Delete a saved profile."""
    from s4lt.cli.commands.profile import run_profile_delete
    run_profile_delete(name)


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Auto-reload on changes")
def serve(host: str, port: int, reload: bool):
    """Start the web UI server."""
    from s4lt.cli.commands.serve import run_serve
    run_serve(host=host, port=port, reload=reload)


@cli.group()
def package():
    """View, edit, merge, and split .package files."""
    pass


@package.command("view")
@click.argument("file")
@click.option("--type", "type_filter", help="Filter by resource type")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def package_view(file: str, type_filter: str | None, json_output: bool):
    """View package contents."""
    from s4lt.cli.commands.package import run_view
    run_view(file, type_filter, json_output)


@package.command("extract")
@click.argument("file")
@click.argument("tgi", required=False)
@click.option("--type", "type_filter", help="Extract all of type")
@click.option("--output", "-o", "output_dir", help="Output directory")
@click.option("--all", "all_resources", is_flag=True, help="Extract all resources")
def package_extract(file: str, tgi: str | None, type_filter: str | None, output_dir: str | None, all_resources: bool):
    """Extract resources from package."""
    from s4lt.cli.commands.package import run_extract
    run_extract(file, tgi, type_filter, output_dir, all_resources)


@package.command("edit")
@click.argument("file")
def package_edit(file: str):
    """Open package in web editor."""
    from s4lt.cli.commands.package import run_edit
    run_edit(file)


@package.command("merge")
@click.argument("output")
@click.argument("inputs", nargs=-1, required=True)
def package_merge(output: str, inputs: tuple[str, ...]):
    """Merge multiple packages into one."""
    from s4lt.cli.commands.package import run_merge
    run_merge(output, list(inputs))


@package.command("split")
@click.argument("file")
@click.option("--output", "-o", "output_dir", help="Output directory")
@click.option("--by-type", is_flag=True, default=True, help="Split by resource type")
@click.option("--by-group", is_flag=True, help="Split by group ID")
@click.option("--extract-all", is_flag=True, help="Extract as individual files")
def package_split(file: str, output_dir: str | None, by_type: bool, by_group: bool, extract_all: bool):
    """Split package into multiple files."""
    from s4lt.cli.commands.package import run_split
    run_split(file, output_dir, by_type, by_group, extract_all)


@cli.group()
def steam():
    """Steam Deck integration."""
    pass


@steam.command()
def install():
    """Add S4LT to Steam library."""
    from s4lt.cli.commands.steam import install as steam_install
    steam_install.callback()


@steam.command()
def uninstall():
    """Remove S4LT from Steam library."""
    from s4lt.cli.commands.steam import uninstall as steam_uninstall
    steam_uninstall.callback()


if __name__ == "__main__":
    cli()
