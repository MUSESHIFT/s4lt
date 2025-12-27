"""Enable/disable mod toggle operations."""

from pathlib import Path

from s4lt.organize.exceptions import ModNotFoundError


def is_enabled(mod_path: Path) -> bool:
    """Check if a mod is enabled (not .disabled).

    Args:
        mod_path: Path to the mod file

    Returns:
        True if enabled (.package), False if disabled (.disabled)
    """
    return mod_path.suffix == ".package"


def disable_mod(mod_path: Path) -> bool:
    """Disable a mod by renaming .package to .package.disabled.

    Args:
        mod_path: Path to the mod file

    Returns:
        True if mod was disabled, False if already disabled

    Raises:
        ModNotFoundError: If mod file doesn't exist
    """
    if not mod_path.exists():
        raise ModNotFoundError(f"Mod not found: {mod_path}")

    if mod_path.suffix != ".package":
        return False  # Already disabled or not a package

    new_path = mod_path.with_suffix(".package.disabled")
    mod_path.rename(new_path)
    return True


def enable_mod(mod_path: Path) -> bool:
    """Enable a mod by renaming .package.disabled to .package.

    Args:
        mod_path: Path to the disabled mod file

    Returns:
        True if mod was enabled, False if already enabled

    Raises:
        ModNotFoundError: If mod file doesn't exist
    """
    if not mod_path.exists():
        raise ModNotFoundError(f"Mod not found: {mod_path}")

    if mod_path.suffix != ".disabled":
        return False  # Already enabled

    # Remove .disabled suffix (which includes .package)
    new_path = mod_path.with_suffix("")  # .package.disabled -> .package
    mod_path.rename(new_path)
    return True
