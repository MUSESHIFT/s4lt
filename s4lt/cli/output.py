"""CLI output formatting helpers."""

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel

console = Console()


def format_size(bytes: int) -> str:
    """Format bytes as human-readable size."""
    if bytes < 1024:
        return f"{bytes} B"
    elif bytes < 1024 * 1024:
        return f"{bytes / 1024:.1f} KB"
    elif bytes < 1024 * 1024 * 1024:
        return f"{bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes / (1024 * 1024 * 1024):.1f} GB"


def format_path(path: str, max_len: int = 60) -> str:
    """Format path, truncating if too long."""
    if len(path) <= max_len:
        return path

    # Keep filename, truncate middle
    parts = path.split("/")
    filename = parts[-1]

    if len(filename) >= max_len - 4:
        return "..." + filename[-(max_len - 3):]

    available = max_len - len(filename) - 4  # 4 for ".../"
    prefix = path[:available]
    return f"{prefix}.../{filename}"


def create_progress() -> Progress:
    """Create a Rich progress bar for scanning."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    )


def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"[green]✓[/green] {message}")


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def print_error(message: str) -> None:
    """Print error message."""
    console.print(f"[red]✗[/red] {message}")


def print_info(message: str) -> None:
    """Print info message."""
    console.print(f"[blue]ℹ[/blue] {message}")
