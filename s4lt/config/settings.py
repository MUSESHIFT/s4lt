"""User settings management."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".config" / "s4lt"
CONFIG_FILE = CONFIG_DIR / "config.toml"
DATA_DIR = Path.home() / ".local" / "share" / "s4lt"
DB_PATH = DATA_DIR / "s4lt.db"


@dataclass
class Settings:
    """User settings."""

    mods_path: Path | None = None
    tray_path: Path | None = None
    include_subfolders: bool = True
    ignore_patterns: list[str] = field(
        default_factory=lambda: ["__MACOSX", ".DS_Store", "*.disabled"]
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for saving."""
        return {
            "paths": {
                "mods": str(self.mods_path) if self.mods_path else None,
                "tray": str(self.tray_path) if self.tray_path else None,
            },
            "scan": {
                "include_subfolders": self.include_subfolders,
                "ignore_patterns": self.ignore_patterns,
            },
        }


def get_settings() -> Settings:
    """Load settings from config file."""
    if not CONFIG_FILE.exists():
        return Settings()

    try:
        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)

        paths_data = data.get("paths", {})
        mods_path = None
        if mods_str := paths_data.get("mods"):
            mods_path = Path(mods_str)

        tray_path = None
        if tray_str := paths_data.get("tray"):
            tray_path = Path(tray_str)

        scan = data.get("scan", {})

        return Settings(
            mods_path=mods_path,
            tray_path=tray_path,
            include_subfolders=scan.get("include_subfolders", True),
            ignore_patterns=scan.get("ignore_patterns", Settings().ignore_patterns),
        )
    except Exception:
        return Settings()


def save_settings(settings: Settings) -> None:
    """Save settings to config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Build TOML manually (no tomllib write support)
    lines = []
    lines.append("[paths]")
    if settings.mods_path:
        lines.append(f'mods = "{settings.mods_path}"')
    if settings.tray_path:
        lines.append(f'tray = "{settings.tray_path}"')
    lines.append("")
    lines.append("[scan]")
    lines.append(f"include_subfolders = {'true' if settings.include_subfolders else 'false'}")
    patterns = ", ".join(f'"{p}"' for p in settings.ignore_patterns)
    lines.append(f"ignore_patterns = [{patterns}]")

    CONFIG_FILE.write_text("\n".join(lines) + "\n")
