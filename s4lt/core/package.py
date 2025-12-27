"""Package class - main API for reading and writing DBPF packages."""

from pathlib import Path
from typing import BinaryIO, Iterator

from s4lt.core.header import parse_header, DBPFHeader
from s4lt.core.index import parse_index, IndexEntry
from s4lt.core.resource import Resource
from s4lt.core.writer import write_package


class Package:
    """A Sims 4 .package file.

    Usage:
        with Package.open("mod.package") as pkg:
            for resource in pkg.resources:
                print(resource)
                data = resource.extract()
    """

    def __init__(self, file: BinaryIO, header: DBPFHeader, resources: list[Resource], path: Path | None = None):
        """Create a Package. Use Package.open() instead."""
        self._file = file
        self._header = header
        self._resources = resources
        self._path = path
        self._modified = False
        self._pending_resources: list[dict] = []  # New resources to add
        self._removed_tgis: set[tuple] = set()     # TGIs to remove

    @classmethod
    def open(cls, path: str | Path) -> "Package":
        """Open a DBPF package file.

        Args:
            path: Path to .package file

        Returns:
            Package instance

        Raises:
            InvalidMagicError: If file is not a valid DBPF
            UnsupportedVersionError: If DBPF version is not 2.x
            FileNotFoundError: If file doesn't exist
        """
        path = Path(path)
        file = open(path, "rb")

        try:
            # Parse header
            header = parse_header(file)

            # Seek to index and parse
            file.seek(header.index_position)
            entries = parse_index(file, header.entry_count)

            # Create Resource objects
            resources = [Resource(entry, file) for entry in entries]

            return cls(file, header, resources, Path(path))

        except Exception:
            file.close()
            raise

    @property
    def version(self) -> tuple[int, int]:
        """DBPF version as (major, minor)."""
        return self._header.version

    @property
    def resources(self) -> list[Resource]:
        """List of all resources in the package."""
        return self._resources

    def find_by_type(self, type_id: int) -> list[Resource]:
        """Find all resources with a specific type ID.

        Args:
            type_id: The type ID to search for

        Returns:
            List of matching resources
        """
        return [r for r in self._resources if r.type_id == type_id]

    def find_by_instance(self, instance_id: int) -> Resource | None:
        """Find a resource by instance ID.

        Args:
            instance_id: The 64-bit instance ID

        Returns:
            Matching resource or None
        """
        for r in self._resources:
            if r.instance_id == instance_id:
                return r
        return None

    def close(self) -> None:
        """Close the underlying file handle."""
        if self._file:
            self._file.close()
            self._file = None

    def __enter__(self) -> "Package":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __iter__(self) -> Iterator[Resource]:
        return iter(self._resources)

    def __len__(self) -> int:
        return len(self._resources) + len(self._pending_resources)

    def __str__(self) -> str:
        return f"<Package v{self.version[0]}.{self.version[1]} with {len(self)} resources>"

    def __repr__(self) -> str:
        return self.__str__()

    def mark_modified(self) -> None:
        """Mark package as modified (will create backup on save)."""
        self._modified = True

    def add_resource(
        self,
        type_id: int,
        group_id: int,
        instance_id: int,
        data: bytes,
        compress: bool = True,
    ) -> None:
        """Add a new resource to the package.

        Args:
            type_id: Resource type ID
            group_id: Resource group ID
            instance_id: Resource instance ID (64-bit)
            data: Uncompressed resource data
            compress: Whether to compress the data
        """
        self._pending_resources.append({
            "type_id": type_id,
            "group_id": group_id,
            "instance_id": instance_id,
            "data": data,
            "compress": compress,
        })
        self._modified = True

    def remove_resource(self, type_id: int, group_id: int, instance_id: int) -> None:
        """Remove a resource by TGI."""
        self._removed_tgis.add((type_id, group_id, instance_id))
        self._modified = True

    def update_resource(self, type_id: int, group_id: int, instance_id: int, data: bytes) -> None:
        """Update an existing resource's data."""
        self.remove_resource(type_id, group_id, instance_id)
        self.add_resource(type_id, group_id, instance_id, data)

    def save(self, path: Path | None = None) -> None:
        """Save package to disk.

        Args:
            path: Output path (defaults to original path)
        """
        if path is None:
            path = self._path
        if path is None:
            raise ValueError("No path specified for save")

        # Collect all resources
        all_resources = []

        # Add existing resources (not removed)
        for res in self._resources:
            tgi = (res.type_id, res.group_id, res.instance_id)
            if tgi not in self._removed_tgis:
                all_resources.append({
                    "type_id": res.type_id,
                    "group_id": res.group_id,
                    "instance_id": res.instance_id,
                    "data": res.extract(),
                    "compress": res.is_compressed,
                })

        # Add pending resources
        all_resources.extend(self._pending_resources)

        # Write
        write_package(path, all_resources, create_backup=self._modified)

        # Clear pending state
        self._pending_resources = []
        self._removed_tgis = set()
        self._modified = False
