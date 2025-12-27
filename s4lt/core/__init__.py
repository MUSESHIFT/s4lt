"""S4LT Core - DBPF parsing library."""

from s4lt.core.exceptions import (
    DBPFError,
    InvalidMagicError,
    UnsupportedVersionError,
    CorruptedIndexError,
    CompressionError,
    ResourceNotFoundError,
)

__all__ = [
    "DBPFError",
    "InvalidMagicError",
    "UnsupportedVersionError",
    "CorruptedIndexError",
    "CompressionError",
    "ResourceNotFoundError",
]
