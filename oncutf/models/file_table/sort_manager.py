"""oncutf.models.file_table.sort_manager.

Sorting logic for file table model.

This module provides the SortManager class that handles file sorting by various
columns including metadata fields with proper type conversion and special cases.

Author: Michael Economou
Date: 2026-01-01
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class SortManager:
    """Manages file sorting logic for file table display.

    Responsibilities:
        - Sort files by different column types (filename, size, metadata, etc.)
        - Handle numeric vs string sorting appropriately
        - Extract and convert metadata values for sorting
        - Provide sort keys for complex fields
    """

    def __init__(self, parent_window: Any = None, get_hash_value_func: Any = None) -> None:
        """Initialize the SortManager.

        Args:
            parent_window: Reference to parent MainWindow (for metadata cache access)
            get_hash_value_func: Function to get hash value for a file path

        """
        self.parent_window = parent_window
        self._get_hash_value = get_hash_value_func

    def sort_files(
        self,
        files: list["FileItem"],
        column_key: str,
        reverse: bool = False,
    ) -> list["FileItem"]:
        """Sort files by the specified column.

        Args:
            files: List of FileItem objects to sort
            column_key: Column key to sort by
            reverse: True for descending order

        Returns:
            Sorted list of FileItem objects

        """
        if not files:
            return files

        # Sort based on column key
        if column_key == "filename":
            return sorted(files, key=lambda f: f.filename.lower(), reverse=reverse)
        if column_key == "file_size":
            return sorted(
                files,
                key=lambda f: f.size if hasattr(f, "size") else 0,
                reverse=reverse,
            )
        if column_key == "type":
            return sorted(files, key=lambda f: f.extension.lower(), reverse=reverse)
        if column_key == "modified":
            return sorted(files, key=lambda f: f.modified, reverse=reverse)
        if column_key == "path":
            return sorted(files, key=lambda f: f.full_path.lower(), reverse=reverse)
        if column_key == "file_hash":
            if self._get_hash_value:
                return sorted(
                    files,
                    key=lambda f: self._get_hash_value(f.full_path),
                    reverse=reverse,
                )
            return files
        if column_key == "color":
            # Sort by color: "none" first, then alphabetically by hex value
            return sorted(
                files,
                key=lambda f: (f.color != "none", f.color.lower()),
                reverse=reverse,
            )
        # For metadata columns, sort by the metadata value
        return sorted(
            files,
            key=lambda f: self.get_metadata_sort_key(f, column_key),
            reverse=reverse,
        )

    def get_metadata_sort_key(self, file: "FileItem", column_key: str) -> Any:
        """Get sort key for a file based on metadata column.

        Args:
            file: FileItem to get sort key for
            column_key: Metadata column key

        Returns:
            Sort key value (string, int, or float)

        """
        if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
            entry = self.parent_window.metadata_cache.get_entry(file.full_path)
            if entry and hasattr(entry, "data") and entry.data:
                # Map column keys to metadata keys (using actual EXIF/QuickTime keys)
                # Use centralized metadata field mapper for sorting
                from oncutf.core.metadata.field_mapper import MetadataFieldMapper

                # Get possible metadata keys for this column
                possible_keys = MetadataFieldMapper.get_metadata_keys_for_field(column_key)

                # Find the first available key in the metadata
                found_value = None
                for key in possible_keys:
                    if key in entry.data:
                        found_value = entry.data[key]
                        break

                if found_value is not None:
                    # Special handling for image size (sort by width)
                    if column_key == "image_size":
                        try:
                            # Extract width from "widthxheight" format
                            if "close" in str(found_value):
                                width = str(found_value).split("close")[0]
                                return int(width)
                            return int(found_value)
                        except (ValueError, TypeError):
                            return 0
                    # For numeric values, try to convert to int/float for proper sorting
                    elif column_key in [
                        "iso",
                        "video_fps",
                        "video_avg_bitrate",
                        "rotation",
                    ]:
                        try:
                            # Extract numeric part from strings like "100" or "100.0"
                            numeric_str = str(found_value).split()[0]  # Take first word
                            if "." in numeric_str:
                                return float(numeric_str)
                            return int(numeric_str)
                        except (ValueError, TypeError):
                            return 0
                    else:
                        return str(found_value).lower()  # String sorting (case-insensitive)

        # Return appropriate default value based on column type
        if column_key in [
            "iso",
            "video_fps",
            "video_avg_bitrate",
            "rotation",
            "image_size",
        ]:
            return 0  # Default numeric value for numeric columns
        return ""  # Default string value for text columns
