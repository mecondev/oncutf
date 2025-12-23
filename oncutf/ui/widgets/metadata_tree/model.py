"""
Module: model.py

Author: Michael Economou
Date: 2025-12-23

Pure data structures for the metadata tree widget.

This module contains dataclasses and type definitions that represent
the data layer of the metadata tree. These classes have NO Qt dependencies
and can be used for testing, serialization, or non-GUI contexts.

Design principles:
- Immutable where possible (frozen dataclasses)
- No side effects
- No external dependencies beyond stdlib
- Type-safe with full annotations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(Enum):
    """Type of node in the metadata tree."""

    GROUP = "group"  # Category/group node (e.g., "EXIF", "IPTC")
    FIELD = "field"  # Leaf node with actual value
    ROOT = "root"  # Root node (invisible)


class FieldStatus(Enum):
    """Status of a metadata field."""

    NORMAL = "normal"  # Unmodified field
    MODIFIED = "modified"  # User has changed the value (staged)
    EXTENDED = "extended"  # Only available in extended metadata
    INVALID = "invalid"  # Value failed validation


@dataclass
class TreeNodeData:
    """
    Data for a single node in the metadata tree.

    This is a pure data structure that can represent any node
    in the tree hierarchy without Qt dependencies.

    Attributes:
        key: The metadata key or group name (e.g., "Title", "EXIF")
        display_key: Human-readable key for display (may differ from key)
        value: The metadata value (empty string for group nodes)
        node_type: Whether this is a group, field, or root node
        status: Current status of the field (normal, modified, etc.)
        original_value: Original value before any modifications
        children: Child nodes (for group nodes)
        tooltip: Optional tooltip text
        editable: Whether the field can be edited
        key_path: Full path to this node (e.g., "EXIF/DateTimeOriginal")
    """

    key: str
    value: str = ""
    display_key: str = ""
    node_type: NodeType = NodeType.FIELD
    status: FieldStatus = FieldStatus.NORMAL
    original_value: str | None = None
    children: list[TreeNodeData] = field(default_factory=list)
    tooltip: str = ""
    editable: bool = True
    key_path: str = ""

    def __post_init__(self) -> None:
        """Set defaults after initialization."""
        if not self.display_key:
            self.display_key = self.key
        if not self.key_path:
            self.key_path = self.key
        if self.original_value is None:
            self.original_value = self.value

    @property
    def is_group(self) -> bool:
        """Check if this is a group node."""
        return self.node_type == NodeType.GROUP

    @property
    def is_modified(self) -> bool:
        """Check if this field has been modified."""
        return self.status == FieldStatus.MODIFIED

    @property
    def is_extended(self) -> bool:
        """Check if this is an extended-only field."""
        return self.status == FieldStatus.EXTENDED

    @property
    def has_children(self) -> bool:
        """Check if this node has children."""
        return len(self.children) > 0

    def add_child(self, child: TreeNodeData) -> None:
        """Add a child node to this node."""
        self.children.append(child)

    def find_child(self, key: str) -> TreeNodeData | None:
        """Find a direct child by key."""
        for child in self.children:
            if child.key == key:
                return child
        return None

    def find_by_path(self, key_path: str) -> TreeNodeData | None:
        """
        Find a node by its full key path.

        Args:
            key_path: Path like "EXIF/DateTimeOriginal"

        Returns:
            The node if found, None otherwise
        """
        parts = key_path.split("/")
        current = self

        for part in parts:
            found = current.find_child(part)
            if found is None:
                return None
            current = found

        return current

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "key": self.key,
            "value": self.value,
            "display_key": self.display_key,
            "node_type": self.node_type.value,
            "status": self.status.value,
            "original_value": self.original_value,
            "children": [child.to_dict() for child in self.children],
            "tooltip": self.tooltip,
            "editable": self.editable,
            "key_path": self.key_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TreeNodeData:
        """Create from dictionary."""
        children = [cls.from_dict(c) for c in data.get("children", [])]
        return cls(
            key=data["key"],
            value=data.get("value", ""),
            display_key=data.get("display_key", ""),
            node_type=NodeType(data.get("node_type", "field")),
            status=FieldStatus(data.get("status", "normal")),
            original_value=data.get("original_value"),
            children=children,
            tooltip=data.get("tooltip", ""),
            editable=data.get("editable", True),
            key_path=data.get("key_path", ""),
        )


@dataclass
class MetadataDisplayState:
    """
    Current display state of the metadata tree.

    Tracks the current file, modifications, scroll position,
    and other UI state without coupling to Qt.

    Attributes:
        file_path: Path to the currently displayed file
        modified_keys: Set of key paths that have been modified
        extended_keys: Set of key paths that are extended-only
        scroll_position: Vertical scroll position in pixels
        expanded_groups: Set of group names that are expanded
        search_filter: Current search/filter text
        is_placeholder: Whether showing placeholder (no file selected)
    """

    file_path: str | None = None
    modified_keys: set[str] = field(default_factory=set)
    extended_keys: set[str] = field(default_factory=set)
    scroll_position: int = 0
    expanded_groups: set[str] = field(default_factory=set)
    search_filter: str = ""
    is_placeholder: bool = True
    is_extended_metadata: bool = False  # Whether metadata was loaded in extended mode

    @property
    def has_file(self) -> bool:
        """Check if a file is currently loaded."""
        return self.file_path is not None

    @property
    def has_modifications(self) -> bool:
        """Check if there are any modifications."""
        return len(self.modified_keys) > 0

    @property
    def modification_count(self) -> int:
        """Get the number of modified fields."""
        return len(self.modified_keys)

    def clear(self) -> None:
        """Clear all state."""
        self.file_path = None
        self.modified_keys.clear()
        self.extended_keys.clear()
        self.scroll_position = 0
        self.expanded_groups.clear()
        self.search_filter = ""
        self.is_placeholder = True

    def set_file(self, file_path: str) -> None:
        """Set the current file and reset placeholder mode."""
        self.file_path = file_path
        self.is_placeholder = False


@dataclass(frozen=True)
class MetadataFieldInfo:
    """
    Information about a metadata field for validation and display.

    Immutable configuration for a specific metadata field type.

    Attributes:
        key: The canonical key name
        display_name: Human-readable name
        group: Which group this field belongs to
        editable: Whether the field can be edited
        max_length: Maximum allowed length (0 = unlimited)
        allowed_chars: Regex pattern for allowed characters
        tooltip: Help text for this field
    """

    key: str
    display_name: str
    group: str = "Other"
    editable: bool = True
    max_length: int = 0
    allowed_chars: str = ""
    tooltip: str = ""


# Common metadata groups for organization
METADATA_GROUPS = {
    "EXIF": "Camera and exposure information",
    "IPTC": "International Press Telecommunications Council metadata",
    "XMP": "Extensible Metadata Platform",
    "File": "File system information",
    "Composite": "Calculated/derived values",
    "QuickTime": "Video container metadata",
    "Other": "Miscellaneous metadata",
}

# Fields that are typically read-only
READ_ONLY_FIELDS = frozenset({
    "FileSize",
    "FileModifyDate",
    "FileAccessDate",
    "FileInodeChangeDate",
    "FilePermissions",
    "FileType",
    "FileTypeExtension",
    "MIMEType",
    "ImageWidth",
    "ImageHeight",
    "BitDepth",
    "ColorType",
})

# Fields that support extended metadata only
EXTENDED_ONLY_PATTERNS = frozenset({
    "accelerometer",
    "gyro",
    "pitch",
    "roll",
    "yaw",
    "segment",
    "embedded",
    "extended",
})
