"""SD card storage management."""

import os
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


@dataclass
class MoveResult:
    """Result of a move operation."""

    success_count: int
    failed_paths: list[Path]
    bytes_moved: int

    @property
    def all_succeeded(self) -> bool:
        return len(self.failed_paths) == 0


def _get_size(path: Path) -> int:
    """Get total size of file or directory."""
    if path.is_file():
        return path.stat().st_size
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total


def move_to_sd(mod_paths: list[Path], sd_mods_path: Path) -> MoveResult:
    """Move mods to SD card and create symlinks.

    Args:
        mod_paths: List of files/folders to move
        sd_mods_path: Destination folder on SD card

    Returns:
        MoveResult with operation statistics
    """
    success_count = 0
    failed_paths = []
    bytes_moved = 0

    # Ensure destination exists
    sd_mods_path.mkdir(parents=True, exist_ok=True)

    for source in mod_paths:
        if not source.exists():
            failed_paths.append(source)
            continue

        size = _get_size(source)
        dest = sd_mods_path / source.name

        # Check available space
        try:
            usage = shutil.disk_usage(sd_mods_path)
            if usage.free < size:
                failed_paths.append(source)
                continue
        except OSError:
            failed_paths.append(source)
            continue

        try:
            # Move to SD card
            shutil.move(str(source), str(dest))

            # Create symlink in original location
            source.symlink_to(dest)

            success_count += 1
            bytes_moved += size
        except OSError:
            # Rollback if possible
            if dest.exists() and not source.exists():
                shutil.move(str(dest), str(source))
            failed_paths.append(source)

    return MoveResult(
        success_count=success_count,
        failed_paths=failed_paths,
        bytes_moved=bytes_moved,
    )


def move_to_internal(symlink_paths: list[Path], mods_path: Path) -> MoveResult:
    """Move mods back from SD card to internal storage.

    Args:
        symlink_paths: List of symlinks to resolve and move back
        mods_path: Internal Mods folder path

    Returns:
        MoveResult with operation statistics
    """
    success_count = 0
    failed_paths = []
    bytes_moved = 0

    for symlink in symlink_paths:
        if not symlink.is_symlink():
            failed_paths.append(symlink)
            continue

        # Resolve symlink to get SD location
        sd_path = symlink.resolve()
        if not sd_path.exists():
            failed_paths.append(symlink)
            continue

        size = _get_size(sd_path)

        # Check available space on internal
        try:
            usage = shutil.disk_usage(mods_path)
            if usage.free < size:
                failed_paths.append(symlink)
                continue
        except OSError:
            failed_paths.append(symlink)
            continue

        try:
            # Remove symlink
            symlink.unlink()

            # Move from SD to internal
            shutil.move(str(sd_path), str(symlink))

            success_count += 1
            bytes_moved += size
        except OSError:
            # Rollback: recreate symlink if it was deleted but move failed
            if not symlink.exists() and sd_path.exists():
                symlink.symlink_to(sd_path)
            failed_paths.append(symlink)

    return MoveResult(
        success_count=success_count,
        failed_paths=failed_paths,
        bytes_moved=bytes_moved,
    )


@dataclass
class SymlinkIssue:
    """A problem with a symlinked mod."""

    path: Path
    target: Path
    reason: str  # "target_missing", "permission_denied"


def check_symlink_health(mods_path: Path) -> list[SymlinkIssue]:
    """Check all symlinks in mods folder for issues.

    Args:
        mods_path: Path to Mods folder

    Returns:
        List of issues found (empty if all OK)
    """
    issues = []

    if not mods_path.exists():
        return issues

    for item in mods_path.iterdir():
        if not item.is_symlink():
            continue

        target = Path(os.readlink(item))
        if not target.is_absolute():
            target = item.parent / target

        if not target.exists():
            issues.append(SymlinkIssue(
                path=item,
                target=target,
                reason="target_missing",
            ))

    return issues
