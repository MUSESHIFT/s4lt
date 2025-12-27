"""DBPF parsing exceptions."""


class DBPFError(Exception):
    """Base exception for DBPF parsing errors."""


class InvalidMagicError(DBPFError):
    """File does not have valid DBPF magic bytes."""


class UnsupportedVersionError(DBPFError):
    """DBPF version is not supported (requires 2.x)."""


class CorruptedIndexError(DBPFError):
    """Index table is corrupted or malformed."""


class CompressionError(DBPFError):
    """Failed to decompress resource data."""


class ResourceNotFoundError(DBPFError):
    """Requested resource does not exist in package."""
