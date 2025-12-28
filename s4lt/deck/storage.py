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


@dataclass
class StorageSummary:
    """Storage usage summary."""

    internal_used_bytes: int
    internal_free_bytes: int
    sd_used_bytes: int
    sd_free_bytes: int
    symlink_count: int

    @property
    def internal_used_gb(self) -> float:
        return self.internal_used_bytes / 1_000_000_000

    @property
    def internal_free_gb(self) -> float:
        return self.internal_free_bytes / 1_000_000_000

    @property
    def sd_used_gb(self) -> float:
        return self.sd_used_bytes / 1_000_000_000

    @property
    def sd_free_gb(self) -> float:
        return self.sd_free_bytes / 1_000_000_000


def get_storage_summary(mods_path: Path, sd_path: Path | None) -> StorageSummary:
    """Calculate storage usage for mods.

    Args:
        mods_path: Path to Mods folder
        sd_path: Path to SD card mods folder (or None)

    Returns:
        StorageSummary with usage statistics
    """
    internal_used = 0
    sd_used = 0
    symlink_count = 0

    if mods_path.exists():
        for item in mods_path.rglob("*"):
            if item.is_symlink():
                symlink_count += 1
                # Symlinked files count toward SD storage
                target = item.resolve()
                if target.exists():
                    if target.is_file():
                        sd_used += target.stat().st_size
                    elif target.is_dir():
                        for f in target.rglob("*"):
                            if f.is_file():
                                sd_used += f.stat().st_size
            elif item.is_file():
                internal_used += item.stat().st_size

    # Get free space
    try:
        internal_usage = shutil.disk_usage(mods_path)
        internal_free = internal_usage.free
    except OSError:
        internal_free = 0

    sd_free = 0
    if sd_path and sd_path.exists():
        try:
            sd_usage = shutil.disk_usage(sd_path)
            sd_free = sd_usage.free
        except OSError:
            pass

    return StorageSummary(
        internal_used_bytes=internal_used,
        internal_free_bytes=internal_free,
        sd_used_bytes=sd_used,
        sd_free_bytes=sd_free,
        symlink_count=symlink_count,
    )
