"""High-level TrayItem class for working with tray entries."""

from pathlib import Path

from s4lt.tray.scanner import TrayItemType
from s4lt.tray.trayitem import parse_trayitem, TrayItemMeta
from s4lt.tray.thumbnails import extract_thumbnail
from s4lt.tray.exceptions import TrayItemNotFoundError, TrayParseError


# Extensions that contain thumbnail images
THUMBNAIL_EXTENSIONS = {".hhi", ".sgi", ".bpi", ".midi"}


class TrayItem:
    """A saved household, lot, or room from the Tray folder.

    Provides high-level access to tray item metadata, thumbnails,
    and associated files.
    """

    def __init__(
        self,
        item_id: str,
        tray_path: Path,
        files: list[Path],
        item_type: TrayItemType,
        meta: TrayItemMeta | None = None,
    ):
        """Create a TrayItem.

        Args:
            item_id: The hex ID of this tray item
            tray_path: Path to the Tray folder
            files: List of all files belonging to this item
            item_type: Type of item (household, lot, room)
            meta: Parsed metadata (lazy loaded if not provided)
        """
        self._id = item_id
        self._tray_path = tray_path
        self._files = files
        self._item_type = item_type
        self._meta = meta
        self._cached_meta: TrayItemMeta | None = None

    @classmethod
    def from_path(cls, tray_path: Path, item_id: str) -> "TrayItem":
        """Create TrayItem by discovering files for an ID.

        Args:
            tray_path: Path to the Tray folder
            item_id: The hex ID to look up

        Returns:
            TrayItem instance

        Raises:
            TrayItemNotFoundError: If no .trayitem file found
        """
        trayitem_path = tray_path / f"{item_id}.trayitem"
        if not trayitem_path.exists():
            raise TrayItemNotFoundError(f"No trayitem file for ID {item_id}")

        # Discover all related files
        files = [trayitem_path]

        # Add other extensions
        all_extensions = {".householdbinary", ".hhi", ".sgi", ".blueprint", ".bpi", ".room", ".midi"}
        for ext in all_extensions:
            files.extend(tray_path.glob(f"{item_id}{ext}"))
            files.extend(tray_path.glob(f"{item_id}!*{ext}"))
            files.extend(tray_path.glob(f"{item_id}_*{ext}"))

        files = list(set(files))

        # Determine type from files
        extensions = {f.suffix.lower() for f in files}

        if ".householdbinary" in extensions:
            item_type = TrayItemType.HOUSEHOLD
        elif ".blueprint" in extensions:
            item_type = TrayItemType.LOT
        elif ".room" in extensions:
            item_type = TrayItemType.ROOM
        else:
            item_type = TrayItemType.UNKNOWN

        return cls(
            item_id=item_id,
            tray_path=tray_path,
            files=files,
            item_type=item_type,
        )

    @property
    def id(self) -> str:
        """The hex ID of this tray item."""
        return self._id

    @property
    def item_type(self) -> TrayItemType:
        """Type of tray item."""
        return self._item_type

    @property
    def files(self) -> list[Path]:
        """All files belonging to this tray item."""
        return self._files

    @property
    def trayitem_path(self) -> Path:
        """Path to the .trayitem file."""
        return self._tray_path / f"{self._id}.trayitem"

    @property
    def name(self) -> str:
        """Name of the tray item (parsed from metadata)."""
        meta = self._get_meta()
        return meta.name if meta else self._id

    def _get_meta(self) -> TrayItemMeta | None:
        """Get or load metadata."""
        if self._meta is not None:
            return self._meta

        if self._cached_meta is not None:
            return self._cached_meta

        try:
            self._cached_meta = parse_trayitem(self.trayitem_path)
            return self._cached_meta
        except TrayParseError:
            return None

    def list_thumbnails(self) -> list[Path]:
        """List all thumbnail files for this item."""
        return [f for f in self._files if f.suffix.lower() in THUMBNAIL_EXTENSIONS]

    def get_primary_thumbnail(self) -> tuple[bytes, str] | tuple[None, None]:
        """Get the primary thumbnail for this item.

        Returns:
            Tuple of (image_data, format) or (None, None) if unavailable
        """
        thumbs = self.list_thumbnails()
        if not thumbs:
            return None, None

        # Prefer .hhi for households, .bpi for lots
        for preferred_ext in [".hhi", ".bpi", ".sgi", ".midi"]:
            for thumb in thumbs:
                if thumb.suffix.lower() == preferred_ext:
                    try:
                        return extract_thumbnail(thumb)
                    except Exception:
                        continue

        # Try first available
        try:
            return extract_thumbnail(thumbs[0])
        except Exception:
            return None, None

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"<TrayItem {self.item_type.value}: {self.name}>"

    def __repr__(self) -> str:
        return self.__str__()
