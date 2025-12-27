"""Resource class for lazy extraction from DBPF packages."""

from typing import BinaryIO

from s4lt.core.index import IndexEntry
from s4lt.core.types import get_type_name
from s4lt.core.compression import decompress


class Resource:
    """A single resource in a DBPF package.

    Resources are lazily extracted - data is only read and
    decompressed when extract() is called.
    """

    def __init__(self, entry: IndexEntry, file: BinaryIO):
        """Create a Resource.

        Args:
            entry: Index entry with resource metadata
            file: Open file handle to read data from
        """
        self._entry = entry
        self._file = file
        self._cached_data: bytes | None = None

    @property
    def type_id(self) -> int:
        """Resource type ID."""
        return self._entry.type_id

    @property
    def type_name(self) -> str:
        """Human-readable type name."""
        return get_type_name(self._entry.type_id)

    @property
    def group_id(self) -> int:
        """Resource group ID."""
        return self._entry.group_id

    @property
    def instance_id(self) -> int:
        """Resource instance ID (64-bit)."""
        return self._entry.instance_id

    @property
    def is_compressed(self) -> bool:
        """True if resource data is compressed."""
        return self._entry.is_compressed

    @property
    def compressed_size(self) -> int:
        """Size of data on disk (compressed)."""
        return self._entry.compressed_size

    @property
    def uncompressed_size(self) -> int:
        """Size of data when decompressed."""
        return self._entry.uncompressed_size

    @property
    def compression_type(self) -> int:
        """Compression type code."""
        return self._entry.compression_type

    @property
    def offset(self) -> int:
        """File offset where data begins."""
        return self._entry.offset

    def extract(self) -> bytes:
        """Extract and decompress resource data.

        Returns:
            Decompressed resource data

        Note:
            Result is cached after first extraction.
        """
        if self._cached_data is not None:
            return self._cached_data

        # Seek to resource offset and read compressed data
        self._file.seek(self._entry.offset)
        compressed_data = self._file.read(self._entry.compressed_size)

        # Decompress
        self._cached_data = decompress(
            compressed_data,
            self._entry.compression_type,
            self._entry.uncompressed_size,
        )

        return self._cached_data

    def __str__(self) -> str:
        """Human-readable representation."""
        compressed = " (compressed)" if self.is_compressed else ""
        return (
            f"<Resource {self.type_name} "
            f"G:{self.group_id:08X} "
            f"I:{self.instance_id:016X} "
            f"{self.uncompressed_size} bytes{compressed}>"
        )

    def __repr__(self) -> str:
        return self.__str__()
