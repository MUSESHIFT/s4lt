"""Organization-specific exceptions."""


class OrganizeError(Exception):
    """Base exception for organization operations."""
    pass


class ProfileNotFoundError(OrganizeError):
    """Profile does not exist."""
    pass


class ProfileExistsError(OrganizeError):
    """Profile already exists."""
    pass


class ModNotFoundError(OrganizeError):
    """Mod file not found."""
    pass
