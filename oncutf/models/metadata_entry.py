"""
metadata_entry.py

Author: Michael Economou
Date: 2025-12-03

Type-safe dataclass for metadata entries with improved structure and validation.
Replaces dict-based metadata storage with strongly-typed, memory-efficient dataclass.

Benefits:
- Type safety for metadata operations
- Clear separation of fast vs extended metadata
- Automatic timestamp tracking
- Memory efficiency via __slots__
- Built-in validation
"""

import time
from dataclasses import dataclass, field
from typing import Any

from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@dataclass(slots=True)
class MetadataEntry:
    """Type-safe metadata entry with database persistence support.

    Uses __slots__ for memory efficiency. Tracks metadata type (fast/extended),
    modification state, and timestamps automatically.
    """

    # Core data
    data: dict[str, Any]

    # Metadata type
    is_extended: bool = False

    # State tracking
    modified: bool = False
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        """Validate metadata after initialization."""
        # Ensure data is a dict
        if not isinstance(self.data, dict):
            logger.warning(
                "[MetadataEntry] Invalid data type: %s, converting to dict",
                type(self.data),
            )
            self.data = {}

        # Clean internal markers from data if present
        self._clean_internal_markers()

    def _clean_internal_markers(self):
        """Remove internal markers like __extended__, __modified__ from data."""
        markers = ["__extended__", "__modified__"]
        for marker in markers:
            self.data.pop(marker, None)

    @classmethod
    def create_fast(cls, metadata: dict[str, Any]) -> "MetadataEntry":
        """Create fast metadata entry.

        Args:
            metadata: Fast metadata dict

        Returns:
            MetadataEntry with is_extended=False
        """
        return cls(data=metadata, is_extended=False)

    @classmethod
    def create_extended(cls, metadata: dict[str, Any]) -> "MetadataEntry":
        """Create extended metadata entry.

        Args:
            metadata: Extended metadata dict

        Returns:
            MetadataEntry with is_extended=True
        """
        return cls(data=metadata, is_extended=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MetadataEntry":
        """Create from dict (backward compatibility).

        Args:
            data: Dictionary with 'data', 'is_extended', 'modified', 'timestamp' keys

        Returns:
            New MetadataEntry instance
        """
        return cls(
            data=data.get("data", {}),
            is_extended=data.get("is_extended", False),
            modified=data.get("modified", False),
            timestamp=data.get("timestamp", time.time()),
        )

    # Query methods

    def has_field(self, field_key: str) -> bool:
        """Check if metadata contains a specific field.

        Args:
            field_key: Field key to check (can be nested like "EXIF/DateTimeOriginal")

        Returns:
            True if field exists
        """
        if "/" in field_key:
            # Nested field (group/key)
            parts = field_key.split("/", 1)
            group, key = parts[0], parts[1]

            return (
                group in self.data
                and isinstance(self.data[group], dict)
                and key in self.data[group]
            )
        else:
            # Top-level field
            return field_key in self.data

    def get_field(self, field_key: str, default: Any = None) -> Any:
        """Get metadata field value.

        Args:
            field_key: Field key (can be nested like "EXIF/DateTimeOriginal")
            default: Default value if field not found

        Returns:
            Field value or default
        """
        if "/" in field_key:
            # Nested field
            parts = field_key.split("/", 1)
            group, key = parts[0], parts[1]

            if group in self.data and isinstance(self.data[group], dict):
                return self.data[group].get(key, default)
            return default
        else:
            # Top-level field
            return self.data.get(field_key, default)

    def set_field(self, field_key: str, value: Any) -> None:
        """Set metadata field value and mark as modified.

        Args:
            field_key: Field key (can be nested like "EXIF/DateTimeOriginal")
            value: New value
        """
        if "/" in field_key:
            # Nested field
            parts = field_key.split("/", 1)
            group, key = parts[0], parts[1]

            if group not in self.data:
                self.data[group] = {}
            elif not isinstance(self.data[group], dict):
                logger.warning(
                    "[MetadataEntry] Group %s is not a dict, replacing with new dict",
                    group,
                )
                self.data[group] = {}

            self.data[group][key] = value
        else:
            # Top-level field
            self.data[field_key] = value

        # Mark as modified
        self.modified = True
        self.timestamp = time.time()

    def remove_field(self, field_key: str) -> bool:
        """Remove metadata field.

        Args:
            field_key: Field key to remove

        Returns:
            True if field was removed
        """
        removed = False

        if "/" in field_key:
            # Nested field
            parts = field_key.split("/", 1)
            group, key = parts[0], parts[1]

            if group in self.data and isinstance(self.data[group], dict):
                if key in self.data[group]:
                    del self.data[group][key]
                    removed = True
        # Top-level field
        elif field_key in self.data:
            del self.data[field_key]
            removed = True

        if removed:
            self.modified = True
            self.timestamp = time.time()

        return removed

    # Properties

    @property
    def field_count(self) -> int:
        """Get total number of metadata fields (including nested)."""
        count = 0
        for value in self.data.values():
            if isinstance(value, dict):
                count += len(value)
            else:
                count += 1
        return count

    @property
    def is_empty(self) -> bool:
        """Check if metadata is empty (no real fields)."""
        # Filter out internal markers
        real_fields = {k: v for k, v in self.data.items() if not k.startswith("__")}
        return len(real_fields) == 0

    @property
    def age_seconds(self) -> float:
        """Get age of metadata entry in seconds."""
        return time.time() - self.timestamp

    # Serialization

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for serialization.

        Returns:
            Dictionary with all fields
        """
        return {
            "data": self.data.copy(),
            "is_extended": self.is_extended,
            "modified": self.modified,
            "timestamp": self.timestamp,
            "field_count": self.field_count,
            "age_seconds": self.age_seconds,
        }

    def to_database_dict(self) -> dict[str, Any]:
        """Convert to dict for database storage (without internal fields).

        Returns:
            Clean metadata dict for database
        """
        clean_data = self.data.copy()

        # Remove all internal markers
        clean_data.pop("__extended__", None)
        clean_data.pop("__modified__", None)

        return clean_data

    def __repr__(self) -> str:
        return (
            f"<MetadataEntry("
            f"extended={self.is_extended}, "
            f"fields={self.field_count}, "
            f"modified={self.modified}, "
            f"age={self.age_seconds:.1f}s"
            f")>"
        )

    def __str__(self) -> str:
        return f"MetadataEntry({self.field_count} fields, extended={self.is_extended})"
