"""S4LT Core - DBPF parsing library."""

from s4lt.core.exceptions import (
    DBPFError,
    InvalidMagicError,
    UnsupportedVersionError,
    CorruptedIndexError,
    CompressionError,
    ResourceNotFoundError,
)
from s4lt.core.types import get_type_name, RESOURCE_TYPES

__all__ = [
    "DBPFError",
    "InvalidMagicError",
    "UnsupportedVersionError",
    "CorruptedIndexError",
    "CompressionError",
    "ResourceNotFoundError",
    "get_type_name",
    "RESOURCE_TYPES",
]
