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
from s4lt.core.package import Package
from s4lt.core.resource import Resource
from s4lt.core.index import IndexEntry

__all__ = [
    # Exceptions
    "DBPFError",
    "InvalidMagicError",
    "UnsupportedVersionError",
    "CorruptedIndexError",
    "CompressionError",
    "ResourceNotFoundError",
    # Types
    "get_type_name",
    "RESOURCE_TYPES",
    # Main API
    "Package",
    "Resource",
    "IndexEntry",
]
