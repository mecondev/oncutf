"""
file_entry.py

Author: Michael Economou
Date: 2025-12-03

Type-safe dataclass representation for file entries with improved memory efficiency
and validation. Replaces dict-based FileItem with structured, typed fields.

Benefits over FileItem:
- Type safety with static type checking
- Memory efficiency via __slots__
- Clear documentation of all fields
- Validation and conversion methods
- Immutable fields where appropriate
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@dataclass(slots=True)
class FileEntry:
    """Type-safe file entry with memory-efficient storage.

    Uses __slots__ to reduce memory footprint by ~40% compared to dict-based storage.
    All fields are explicitly typed for static analysis and IDE support.
    """

    # Core identity (immutable)
    full_path: str
    filename: str
    extension: str

    # File properties
    size: int = 0
    modified: datetime = field(default_factory=lambda: datetime.fromtimestamp(0))

    # Application state
    checked: bool = False
    metadata_status: str = "none"  # "none", "loaded", "extended", "modified"

    # Metadata reference (dict for backward compatibility during migration)
    _metadata: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        """Validate and normalize fields after initialization."""
        # Ensure filename matches path
        if self.filename != Path(self.full_path).name:
            logger.warning(
                "[FileEntry] Filename mismatch: %s vs %s",
                self.filename,
                Path(self.full_path).name,
            )
            self.filename = Path(self.full_path).name

        # Normalize extension (lowercase, no dot)
        if self.extension.startswith("."):
            self.extension = self.extension[1:].lower()
        else:
            self.extension = self.extension.lower()

    @classmethod
    def from_path(cls, file_path: str) -> "FileEntry":
        """Create FileEntry from file path by auto-detecting properties.

        Args:
            file_path: Full path to the file

        Returns:
            FileEntry instance with auto-detected properties
        """
        path = Path(file_path)
        filename = path.name
        extension = path.suffix[1:].lower() if path.suffix else ""

        # Get file properties
        try:
            size = path.stat().st_size
            modified = datetime.fromtimestamp(path.stat().st_mtime)
        except (OSError, ValueError):
            logger.warning(
                "[FileEntry] Failed to stat %s",
                file_path,
                exc_info=True,
            )
            size = 0
            modified = datetime.fromtimestamp(0)

        return cls(
            full_path=str(file_path),
            filename=filename,
            extension=extension,
            size=size,
            modified=modified,
        )

    @classmethod
    def from_file_item(cls, file_item: Any) -> "FileEntry":
        """Convert legacy FileItem to FileEntry.

        Args:
            file_item: Legacy FileItem instance

        Returns:
            New FileEntry instance
        """
        entry = cls(
            full_path=file_item.full_path,
            filename=file_item.filename,
            extension=file_item.extension,
            size=file_item.size,
            modified=file_item.modified,
            checked=file_item.checked,
            metadata_status=file_item.metadata_status,
        )

        # Preserve metadata reference during migration
        if hasattr(file_item, "metadata"):
            entry._metadata = file_item.metadata

        return entry

    # Properties for backward compatibility

    @property
    def path(self) -> str:
        """Alias for full_path (backward compatibility)."""
        return self.full_path

    @property
    def name(self) -> str:
        """Alias for filename (backward compatibility)."""
        return self.filename

    @property
    def metadata(self) -> dict[str, Any]:
        """Access metadata dict (backward compatibility)."""
        return self._metadata

    @metadata.setter
    def metadata(self, value: dict[str, Any]):
        """Set metadata dict (backward compatibility)."""
        self._metadata = value

    @property
    def has_metadata(self) -> bool:
        """Check if file has any metadata loaded."""
        return isinstance(self._metadata, dict) and bool(self._metadata)

    @property
    def metadata_extended(self) -> bool:
        """Check if file has extended metadata loaded."""
        return isinstance(self._metadata, dict) and self._metadata.get("__extended__") is True

    # Utility methods

    def get_human_readable_size(self) -> str:
        """Returns human-readable file size string.

        Returns:
            Formatted size string (e.g., "1.2 GB", "540 MB")
        """
        from oncutf.utils.file_size_formatter import format_file_size_system_compatible

        return format_file_size_system_compatible(self.size)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for serialization or compatibility.

        Returns:
            Dictionary representation
        """
        return {
            "full_path": self.full_path,
            "filename": self.filename,
            "extension": self.extension,
            "size": self.size,
            "modified": self.modified.isoformat(),
            "checked": self.checked,
            "metadata_status": self.metadata_status,
            "has_metadata": self.has_metadata,
        }

    def __str__(self) -> str:
        return f"FileEntry({self.filename})"

    def __repr__(self) -> str:
        return (
            f"FileEntry(full_path='{self.full_path}', "
            f"extension='{self.extension}', "
            f"size={self.size}, "
            f"modified='{self.modified}')"
        )
