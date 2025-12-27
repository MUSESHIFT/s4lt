"""EA content indexing exceptions."""


class EAError(Exception):
    """Base exception for EA operations."""


class GameNotFoundError(EAError):
    """Game install folder not found."""


class EAIndexError(EAError):
    """Error indexing EA content."""
