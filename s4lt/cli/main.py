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


if __name__ == "__main__":
    cli()
