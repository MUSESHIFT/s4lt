"""Edit session management for package editing."""

from pathlib import Path
from dataclasses import dataclass, field

from s4lt.core import Package, Resource


@dataclass
class PendingChange:
    """A pending change to a resource."""

    action: str  # "add", "update", "delete"
    type_id: int
    group_id: int
    instance_id: int
    data: bytes | None = None


@dataclass
class EditSession:
    """An editing session for a package file."""

    path: Path
    package: Package
    changes: list[PendingChange] = field(default_factory=list)

    @property
    def has_unsaved_changes(self) -> bool:
        """True if there are pending changes."""
        return len(self.changes) > 0

    @property
    def resources(self) -> list[Resource]:
        """Get all resources in the package."""
        return self.package.resources

    def add_resource(
        self,
        type_id: int,
        group_id: int,
        instance_id: int,
        data: bytes,
    ) -> None:
        """Add a new resource."""
        self.changes.append(PendingChange(
            action="add",
            type_id=type_id,
            group_id=group_id,
            instance_id=instance_id,
            data=data,
        ))

    def update_resource(
        self,
        type_id: int,
        group_id: int,
        instance_id: int,
        data: bytes,
    ) -> None:
        """Update an existing resource."""
        self.changes.append(PendingChange(
            action="update",
            type_id=type_id,
            group_id=group_id,
            instance_id=instance_id,
            data=data,
        ))

    def delete_resource(
        self,
        type_id: int,
        group_id: int,
        instance_id: int,
    ) -> None:
        """Delete a resource."""
        self.changes.append(PendingChange(
            action="delete",
            type_id=type_id,
            group_id=group_id,
            instance_id=instance_id,
        ))

    def save(self) -> None:
        """Apply all pending changes and save."""
        for change in self.changes:
            if change.action == "add":
                self.package.add_resource(
                    change.type_id,
                    change.group_id,
                    change.instance_id,
                    change.data,
                )
            elif change.action == "update":
                self.package.update_resource(
                    change.type_id,
                    change.group_id,
                    change.instance_id,
                    change.data,
                )
            elif change.action == "delete":
                self.package.remove_resource(
                    change.type_id,
                    change.group_id,
                    change.instance_id,
                )

        self.package.save()
        self.changes = []

    def discard_changes(self) -> None:
        """Discard all pending changes."""
        self.changes = []

    def close(self) -> None:
        """Close the session."""
        self.package.close()


# Session cache
_sessions: dict[str, EditSession] = {}


def get_session(path: str) -> EditSession:
    """Get or create an edit session for a package.

    Args:
        path: Path to package file

    Returns:
        EditSession instance
    """
    path_str = str(Path(path).resolve())

    if path_str not in _sessions:
        package = Package.open(path)
        _sessions[path_str] = EditSession(
            path=Path(path).resolve(),
            package=package,
        )

    return _sessions[path_str]


def close_session(path: str) -> None:
    """Close and remove a session."""
    path_str = str(Path(path).resolve())

    if path_str in _sessions:
        _sessions[path_str].close()
        del _sessions[path_str]


def list_sessions() -> list[str]:
    """List all open session paths."""
    return list(_sessions.keys())
