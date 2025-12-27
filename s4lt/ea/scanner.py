"""EA content scanner."""

from pathlib import Path
from typing import Callable

from s4lt.core import Package
from s4lt.ea.database import EADatabase


# Pack folder prefixes
PACK_PREFIXES = ["EP", "GP", "SP", "FP"]


def discover_ea_packages(game_path: Path) -> list[Path]:
    """Discover all EA .package files in game folder.

    Scans:
    - Data/Client/*.package
    - Data/Simulation/**/*.package
    - EP*/Data/**/*.package (expansions)
    - GP*/Data/**/*.package (game packs)
    - SP*/Data/**/*.package (stuff packs)
    - FP*/Data/**/*.package (free packs)
    """
    packages = []

    # Base game Data folder
    data_dir = game_path / "Data"
    if data_dir.is_dir():
        packages.extend(data_dir.rglob("*.package"))

    # DLC folders (EP01, GP05, etc.)
    for item in game_path.iterdir():
        if item.is_dir() and any(item.name.startswith(p) for p in PACK_PREFIXES):
            dlc_data = item / "Data"
            if dlc_data.is_dir():
                packages.extend(dlc_data.rglob("*.package"))

    return sorted(packages)


def get_pack_name(package_path: Path, game_path: Path) -> str:
    """Determine pack name from package path."""
    try:
        relative = package_path.relative_to(game_path)
        parts = relative.parts

        # Check if in DLC folder
        if parts and any(parts[0].startswith(p) for p in PACK_PREFIXES):
            return parts[0]  # EP01, GP05, etc.

        return "BaseGame"
    except ValueError:
        return "Unknown"


def scan_ea_content(
    game_path: Path,
    db: EADatabase,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> tuple[int, int]:
    """Scan all EA packages and index their resources.

    Args:
        game_path: Path to game install folder
        db: EA database instance
        progress_callback: Optional callback(package_name, current, total)

    Returns:
        Tuple of (package_count, resource_count)
    """
    packages = discover_ea_packages(game_path)
    total_packages = len(packages)
    total_resources = 0

    for i, package_path in enumerate(packages):
        if progress_callback:
            progress_callback(package_path.name, i + 1, total_packages)

        try:
            pack_name = get_pack_name(package_path, game_path)

            with Package(package_path) as pkg:
                batch = []
                for entry in pkg.entries:
                    batch.append((
                        entry.instance_id,
                        entry.type_id,
                        entry.group_id,
                        package_path.name,
                        pack_name,
                    ))

                if batch:
                    db.insert_batch(batch)
                    total_resources += len(batch)

        except Exception:
            # Skip corrupt/unreadable packages
            continue

    db.save_scan_info(str(game_path), total_packages, total_resources)

    return total_packages, total_resources
