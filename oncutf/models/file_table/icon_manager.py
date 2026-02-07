"""oncutf.models.file_table.icon_manager.

Icon and tooltip management for file table model.

This module provides the IconManager class that handles status icon creation,
tooltip generation, and hash/metadata status checks for file table display.

Author: Michael Economou
Date: 2026-01-01
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap

from oncutf.ui.helpers.icons_loader import load_metadata_icons
from oncutf.utils.filesystem.file_status_helpers import get_hash_for_file, has_hash
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class IconManager:
    """Manages status icons and tooltips for file table display.

    Responsibilities:
        - Create combined metadata/hash status icons
        - Generate color swatch icons
        - Build unified tooltips with status information
        - Cache tooltips to avoid repeated lookups
    """

    def __init__(self, parent_window: Any = None):
        """Initialize the IconManager.

        Args:
            parent_window: Reference to parent MainWindow (for metadata cache access)

        """
        self.parent_window = parent_window
        self.metadata_icons = load_metadata_icons()
        self._tooltip_cache: dict[str, str] = {}  # full_path -> tooltip

    def has_hash_cached(self, file_path: str) -> bool:
        """Check if a file has a hash stored in the persistent cache.

        Args:
            file_path: Full path to the file

        Returns:
            bool: True if file has a cached hash, False otherwise

        """
        return has_hash(file_path)

    def get_hash_value(self, file_path: str) -> str:
        """Get the hash value for a file from the persistent cache.

        Args:
            file_path: Full path to the file

        Returns:
            str: Hash value if found, empty string otherwise

        """
        hash_value = get_hash_for_file(file_path)
        return hash_value or ""

    def get_unified_tooltip(self, file: "FileItem") -> str:
        """Get unified tooltip for all columns showing metadata and hash status.

        Uses tooltip cache to avoid repeated get_entry() calls on hover events.
        Cache is invalidated when metadata/hash changes.
        """
        # Check cache first
        cached_tooltip = self._tooltip_cache.get(file.full_path)
        if cached_tooltip is not None:
            return cached_tooltip

        tooltip_parts = []

        # Add metadata status
        if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
            entry = self.parent_window.metadata_cache.get_entry(file.full_path)
            if entry and hasattr(entry, "data") and entry.data:
                field_count = len(entry.data)
                # Check the is_extended property of the MetadataEntry object
                if hasattr(entry, "is_extended") and entry.is_extended:
                    tooltip_parts.append(f"{field_count} extended metadata")
                else:
                    tooltip_parts.append(f"{field_count} metadata")
            else:
                tooltip_parts.append("no metadata")

        # Add hash status
        if self.has_hash_cached(file.full_path):
            hash_value = self.get_hash_value(file.full_path)
            if hash_value:
                # Show full hash value
                tooltip_parts.append(f"hash {hash_value}")
            else:
                tooltip_parts.append("hash available")
        else:
            tooltip_parts.append("no hash")

        tooltip = "\n".join(tooltip_parts)

        # Cache the result
        self._tooltip_cache[file.full_path] = tooltip

        return tooltip

    def create_combined_icon(self, metadata_status: str, hash_status: str) -> QIcon:
        """Create a combined icon showing metadata status (left) and hash status (right).
        Always shows both icons - uses grayout color for missing states.

        Args:
            metadata_status: Status of metadata ('loaded', 'extended', 'modified', 'invalid', 'none')
            hash_status: Status of hash ('tag' for available, 'none' for not available)

        Returns:
            QIcon: Combined icon with metadata and hash status

        """
        # Use hardcoded width for status column (column 0)
        combined_width = 50  # Fixed width for status column
        combined_height = 16
        combined_pixmap = QPixmap(combined_width, combined_height)
        combined_pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(combined_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get metadata icon
        metadata_icon = self.metadata_icons.get(metadata_status)
        if metadata_icon:
            # Draw metadata icon on the left (2px from left edge)
            painter.drawPixmap(2, 0, metadata_icon)

        # Get hash icon
        hash_icon = self.metadata_icons.get(hash_status)
        if hash_icon:
            # Draw hash icon on the right (32px from left = 50-16-2 for 2px right margin)
            painter.drawPixmap(32, 0, hash_icon)

        painter.end()
        return QIcon(combined_pixmap)

    def create_color_icon(self, hex_color: str) -> QIcon:
        """Create a color swatch icon for the color column.

        Args:
            hex_color: Hex color string (e.g., "#ff0000")

        Returns:
            QIcon with colored rectangle swatch

        """
        # Create 22x30 pixmap for color swatch (fits 24px row height)
        width = 18
        height = 16
        pixmap = QPixmap(width + 2, height)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw filled rounded rectangle
        color = QColor(hex_color)
        painter.setBrush(color)
        painter.setPen(QColor(0, 0, 0, 50))  # Light border for visibility
        painter.drawRoundedRect(2, 2, width - 2, height - 2, 2, 2)
        painter.end()

        return QIcon(pixmap)

    def clear_tooltip_cache(self) -> None:
        """Clear the tooltip cache."""
        self._tooltip_cache.clear()

    def invalidate_tooltip(self, file_path: str) -> None:
        """Invalidate tooltip cache for a specific file.

        Args:
            file_path: Full path to the file

        """
        self._tooltip_cache.pop(file_path, None)
