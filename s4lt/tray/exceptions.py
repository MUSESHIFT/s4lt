"""Tray parsing exceptions."""


class TrayError(Exception):
    """Base exception for tray operations."""


class TrayItemNotFoundError(TrayError):
    """Tray item files not found or incomplete."""


class TrayParseError(TrayError):
    """Failed to parse tray file."""


class ThumbnailError(TrayError):
    """Failed to extract or process thumbnail."""
