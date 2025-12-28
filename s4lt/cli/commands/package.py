"""Package command implementations."""

import json
from pathlib import Path

from rich.table import Table
from rich.syntax import Syntax

from s4lt.cli.output import console
from s4lt.core import Package, get_type_name


def run_view(package_path: str, type_filter: str | None, json_output: bool) -> None:
    """View package contents."""
    try:
        with Package.open(package_path) as pkg:
            resources = list(pkg.resources)

            if type_filter:
                resources = [r for r in resources if r.type_name == type_filter]

            if json_output:
                data = [
                    {
                        "type": r.type_name,
                        "type_id": f"0x{r.type_id:08X}",
                        "group": f"0x{r.group_id:08X}",
                        "instance": f"0x{r.instance_id:016X}",
                        "size": r.uncompressed_size,
                        "compressed": r.is_compressed,
                    }
                    for r in resources
                ]
                console.print(json.dumps(data, indent=2))
            else:
                table = Table(title=f"{Path(package_path).name} ({len(resources)} resources)")
                table.add_column("Type")
                table.add_column("Group")
                table.add_column("Instance")
                table.add_column("Size")
                table.add_column("Z", justify="center")

                for r in resources:
                    table.add_row(
                        r.type_name,
                        f"0x{r.group_id:08X}",
                        f"0x{r.instance_id:016X}",
                        f"{r.uncompressed_size:,}",
                        "✓" if r.is_compressed else "",
                    )

                console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


def run_extract(
    package_path: str,
    tgi: str | None,
    type_filter: str | None,
    output_dir: str | None,
    all_resources: bool,
) -> None:
    """Extract resources from package."""
    from s4lt.editor.split import extract_all

    output = Path(output_dir) if output_dir else Path(".")
    output.mkdir(parents=True, exist_ok=True)

    if all_resources:
        created = extract_all(package_path, str(output))
        console.print(f"[green]Extracted {len(created)} resources to {output}[/green]")
        return

    with Package.open(package_path) as pkg:
        resources = list(pkg.resources)

        if tgi:
            # Extract specific resource
            parts = tgi.split(":")
            type_id = int(parts[0], 16)
            group_id = int(parts[1], 16)
            instance_id = int(parts[2], 16)

            for r in resources:
                if r.type_id == type_id and r.group_id == group_id and r.instance_id == instance_id:
                    filename = f"{r.type_name}_{instance_id:016X}.bin"
                    (output / filename).write_bytes(r.extract())
                    console.print(f"[green]Extracted to {output / filename}[/green]")
                    return

            console.print("[red]Resource not found[/red]")

        elif type_filter:
            # Extract all of a type
            count = 0
            for r in resources:
                if r.type_name == type_filter:
                    filename = f"{r.type_name}_{r.instance_id:016X}.bin"
                    (output / filename).write_bytes(r.extract())
                    count += 1

            console.print(f"[green]Extracted {count} resources to {output}[/green]")


def run_edit(package_path: str) -> None:
    """Open package in web editor."""
    import webbrowser
    from urllib.parse import quote

    # Start server if not running
    console.print(f"[cyan]Opening {package_path} in browser...[/cyan]")

    encoded = quote(str(Path(package_path).resolve()), safe="")
    url = f"http://127.0.0.1:8000/package/{encoded}"

    console.print(f"[dim]URL: {url}[/dim]")
    console.print("[yellow]Make sure the web server is running: s4lt serve[/yellow]")

    webbrowser.open(url)


def run_merge(output_path: str, input_paths: list[str]) -> None:
    """Merge packages."""
    from s4lt.editor.merge import find_conflicts, merge_packages

    console.print(f"[cyan]Merging {len(input_paths)} packages...[/cyan]")

    # Check for conflicts
    conflicts = find_conflicts(input_paths)

    if conflicts:
        console.print(f"[yellow]Found {len(conflicts)} conflicts (last file wins):[/yellow]")
        for c in conflicts[:10]:
            console.print(f"  0x{c.type_id:08X}:0x{c.group_id:08X}:0x{c.instance_id:016X}")
        if len(conflicts) > 10:
            console.print(f"  ... and {len(conflicts) - 10} more")

    merge_packages(input_paths, output_path)
    console.print(f"[green]Merged to {output_path}[/green]")


def run_split(
    package_path: str,
    output_dir: str | None,
    by_type: bool,
    by_group: bool,
    extract_all_flag: bool,
) -> None:
    """Split package."""
    from s4lt.editor.split import split_by_type, split_by_group, extract_all

    output = Path(output_dir) if output_dir else Path(".")
    output.mkdir(parents=True, exist_ok=True)

    if extract_all_flag:
        created = extract_all(package_path, str(output))
        console.print(f"[green]Extracted {len(created)} files to {output}[/green]")
    elif by_group:
        created = split_by_group(package_path, str(output))
        console.print(f"[green]Created {len(created)} packages in {output}[/green]")
    else:  # by_type is default
        created = split_by_type(package_path, str(output))
        console.print(f"[green]Created {len(created)} packages in {output}[/green]")
