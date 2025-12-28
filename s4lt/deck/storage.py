"""SD card storage management."""

import shutil
from dataclasses import dataclass
from pathlib import Path

from s4lt.deck.detection import get_deck_user

MEDIA_BASE = Path("/run/media")


@dataclass
class RemovableDrive:
    """Information about a removable drive."""

    name: str
    path: Path
    total_bytes: int
    free_bytes: int

    @property
    def total_gb(self) -> float:
        """Total size in GB."""
        return self.total_bytes / 1_000_000_000

    @property
    def free_gb(self) -> float:
        """Free space in GB."""
        return self.free_bytes / 1_000_000_000


def list_removable_drives() -> list[RemovableDrive]:
    """List all mounted removable drives.

    Looks for drives at /run/media/<user>/.
    """
    user = get_deck_user()
    media_path = MEDIA_BASE / user

    if not media_path.exists():
        return []

    drives = []
    for path in media_path.iterdir():
        if path.is_dir():
            try:
                usage = shutil.disk_usage(path)
                drives.append(RemovableDrive(
                    name=path.name,
                    path=path,
                    total_bytes=usage.total,
                    free_bytes=usage.free,
                ))
            except OSError:
                continue

    return drives


def get_sd_card_path() -> Path | None:
    """Get path to first available SD card.

    Returns None if no SD card is mounted.
    """
    drives = list_removable_drives()
    if drives:
        return drives[0].path
    return None
