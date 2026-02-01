"""Metadata cache interaction behavior for MetadataTreeView.

This behavior handles all interactions with the persistent metadata cache,
including reading, updating, and removing cached metadata values.
Extracted from MetadataCacheMixin as part of composition-based refactoring.

Author: Michael Economou
Date: December 28, 2025
Updated: January 1, 2026 - Removed MetadataCacheHelper dependency
"""

from typing import Any, Protocol

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget

from oncutf.utils.filesystem.file_status_helpers import (
    get_metadata_cache_entry,
    get_metadata_for_file,
    get_metadata_value,
    set_metadata_value,
)
from oncutf.utils.filesystem.path_utils import paths_equal
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class CacheableWidget(Protocol):
    """Protocol defining the interface required for metadata cache behavior.

    This protocol specifies what methods a widget must provide to use
    MetadataCacheBehavior for cache interaction.
    """

    # From MetadataTreeView
    modified_items: dict[str, Any]
    modified_items_per_file: dict[str, dict[str, Any]]
    _current_file_path: str | None

    def _get_current_selection(self) -> list[Any]:
        """Get the currently selected file items.

        Returns:
            list[Any]: List of selected FileItem objects

        """
        ...

    def _get_parent_with_file_table(self) -> QWidget | None:
        """Find the parent window that has file_table_view attribute.

        Returns:
            QWidget | None: Parent window if found

        """
        ...


class MetadataCacheBehavior:
    """Behavior for metadata cache interaction in tree views.

    This behavior encapsulates all logic related to the persistent metadata cache:
    - Getting/setting metadata values in cache
    - Updating file item metadata attributes
    - Icon status updates based on modification state
    - Lazy loading fallback methods

    The behavior delegates to helper methods on the host widget for access to
    cache helper, selection state, and parent window references.
    """

    def __init__(self, widget: CacheableWidget) -> None:
        """Initialize the metadata cache behavior.

        Args:
            widget: The host widget that provides cache access and selection

        """
        self._widget = widget

    # =====================================
    # Cache Access Methods
    # =====================================

    def get_metadata_cache(self) -> dict[str, Any] | None:
        """Get metadata cache via parent traversal.

        Returns:
            dict | None: Metadata cache dictionary if found, None otherwise

        """
        parent_window = self._widget._get_parent_with_file_table()
        if parent_window and hasattr(parent_window, "metadata_cache"):
            return parent_window.metadata_cache

        return None

    def get_original_value_from_cache(self, key_path: str) -> Any | None:
        """Get the original value of a metadata field from the cache.

        This should be called before resetting to get the original value.

        Args:
            key_path: Metadata key path (e.g., "EXIF/DateTimeOriginal")

        Returns:
            Any | None: Original value if found, None otherwise

        """
        selected_files = self._widget._get_current_selection()
        if not selected_files:
            return None

        file_item = selected_files[0]
        return get_metadata_value(file_item.full_path, key_path)

    def get_original_metadata_value(self, key_path: str) -> Any | None:
        """Get the ORIGINAL metadata value (not staged) for comparison.

        Used by smart_mark_modified to check against actual original values.

        Args:
            key_path: Metadata key path (e.g., "EXIF/DateTimeOriginal")

        Returns:
            Any | None: Original metadata value if found, None otherwise

        """
        selected_files = self._widget._get_current_selection()
        if not selected_files:
            return None

        file_item = selected_files[0]

        # Get original metadata entry (not staged version)
        metadata_entry = get_metadata_cache_entry(file_item.full_path)
        if not metadata_entry or not hasattr(metadata_entry, "data"):
            return None

        # Extract value from original metadata dict
        return self._get_value_from_metadata_dict(metadata_entry.data, key_path)

    def _get_value_from_metadata_dict(self, metadata: dict[str, Any], key_path: str) -> Any | None:
        """Extract a value from metadata dictionary using key path.

        Args:
            metadata: Metadata dictionary (flat or nested)
            key_path: Key path (simple or nested with /)

        Returns:
            Any | None: Value if found, None otherwise

        """
        parts = key_path.split("/")

        if len(parts) == 1:
            # Top-level key
            return metadata.get(parts[0])
        if len(parts) == 2:
            # Nested key (group/key)
            group, key = parts
            if group in metadata and isinstance(metadata[group], dict):
                return metadata[group].get(key)

        return None

    # =====================================
    # Cache Update Methods
    # =====================================

    def update_metadata_in_cache(self, key_path: str, new_value: str) -> None:
        """Update the metadata value in the cache to persist changes.

        Args:
            key_path: Metadata key path
            new_value: New value to store

        """
        selected_files = self._widget._get_current_selection()
        if not selected_files:
            return

        file_item = selected_files[0]

        # Update cache entry
        set_metadata_value(file_item.full_path, key_path, new_value)

        # Mark cache entry as modified
        cache_entry = get_metadata_cache_entry(file_item.full_path)
        if cache_entry:
            cache_entry.modified = True

        # Update file item status
        file_item.metadata_status = "modified"

        logger.debug(
            "Updated %s in cache for %s",
            key_path,
            file_item.filename,
        )

    def set_metadata_in_cache(self, key_path: str, new_value: str) -> None:
        """Set metadata value in cache (similar to update, but used in specific contexts).

        Args:
            key_path: Metadata key path
            new_value: New value to store

        """
        selected_files = self._widget._get_current_selection()
        if not selected_files:
            return

        file_item = selected_files[0]

        # Set value in cache
        set_metadata_value(file_item.full_path, key_path, new_value)

        logger.debug(
            "Set %s in cache for %s",
            key_path,
            file_item.filename,
        )

    def set_metadata_in_file_item(self, key_path: str, new_value: str) -> None:
        """Set metadata value directly in file_item.metadata dict.

        Used for direct updates bypassing cache helper.

        Args:
            key_path: Metadata key path
            new_value: New value to store

        """
        selected_files = self._widget._get_current_selection()
        if not selected_files:
            return

        file_item = selected_files[0]
        if not hasattr(file_item, "metadata") or file_item.metadata is None:
            file_item.metadata = {}

        parts = key_path.split("/")

        if len(parts) == 1:
            # Top-level key
            file_item.metadata[parts[0]] = new_value
        elif len(parts) == 2:
            # Nested key (group/key)
            group, key = parts
            if group not in file_item.metadata:
                file_item.metadata[group] = {}
            if not isinstance(file_item.metadata[group], dict):
                file_item.metadata[group] = {}
            file_item.metadata[group][key] = new_value

        logger.debug(
            "Set %s in file_item.metadata for %s",
            key_path,
            file_item.filename,
        )

    def reset_metadata_in_cache(self, key_path: str) -> None:
        """Reset the metadata value in the cache to its original state.

        Args:
            key_path: Metadata key path to reset

        """
        selected_files = self._widget._get_current_selection()
        if not selected_files:
            return

        file_item = selected_files[0]

        # Get the original value from file item metadata
        original_value = None
        if hasattr(file_item, "metadata") and file_item.metadata:
            original_value = self._get_value_from_metadata_dict(file_item.metadata, key_path)

        # Update cache with original value or remove if no original
        if original_value is not None:
            set_metadata_value(file_item.full_path, key_path, original_value)
        else:
            # Remove from cache if no original value
            cache_entry = get_metadata_cache_entry(file_item.full_path)
            if cache_entry and hasattr(cache_entry, "data") and key_path in cache_entry.data:
                del cache_entry.data[key_path]

        # Update file icon status based on remaining modified items
        if not hasattr(self._widget, "modified_items") or not self._widget.modified_items:
            file_item.metadata_status = "loaded"
            cache_entry = get_metadata_cache_entry(file_item.full_path)
            if cache_entry:
                cache_entry.modified = False
        else:
            file_item.metadata_status = "modified"

        # Trigger UI update
        self.update_file_icon_status()

    def remove_metadata_from_cache(self, key_path: str) -> None:
        """Remove a metadata key from the cache.

        Args:
            key_path: Metadata key path to remove

        """
        selected_files = self._widget._get_current_selection()
        if not selected_files:
            return

        file_item = selected_files[0]

        # Remove from cache entry
        cache_entry = get_metadata_cache_entry(file_item.full_path)
        if cache_entry and hasattr(cache_entry, "data") and key_path in cache_entry.data:
            del cache_entry.data[key_path]

        logger.debug(
            "Removed %s from cache for %s",
            key_path,
            file_item.filename,
        )

    def remove_metadata_from_file_item(self, key_path: str) -> None:
        """Remove a metadata key from file_item.metadata dict.

        Args:
            key_path: Metadata key path to remove

        """
        selected_files = self._widget._get_current_selection()
        if not selected_files:
            return

        file_item = selected_files[0]
        if not hasattr(file_item, "metadata") or file_item.metadata is None:
            return

        parts = key_path.split("/")

        if len(parts) == 1:
            # Top-level key
            if parts[0] in file_item.metadata:
                del file_item.metadata[parts[0]]
        elif len(parts) == 2:
            # Nested key (group/key)
            group, key = parts
            if (
                group in file_item.metadata
                and isinstance(file_item.metadata[group], dict)
                and key in file_item.metadata[group]
            ):
                del file_item.metadata[group][key]

    # =====================================
    # Icon Status Updates
    # =====================================

    def update_file_icon_status(self) -> None:
        """Update the file icon in the file table to reflect modified status.

        Checks staging manager for modifications and updates file model icons.
        """
        selected_files = self._widget._get_current_selection()
        if not selected_files:
            return

        # Get parent window and file model
        parent_window = self._widget._get_parent_with_file_table()
        if not parent_window:
            return

        file_model = parent_window.file_model
        if not file_model:
            return

        # Get metadata service
        from oncutf.core.metadata.metadata_service import get_metadata_service

        metadata_service = get_metadata_service()

        # For each selected file, update its icon
        updated_rows = []
        for file_item in selected_files:
            # Check if this specific file has modified items
            file_path = file_item.full_path

            # Check if this file has modifications
            has_modifications = metadata_service.has_staged_changes(file_path)

            # Update icon based on whether we have modified items
            if has_modifications:
                # Set modified icon
                file_item.metadata_status = "modified"
            else:
                # Set normal loaded icon
                file_item.metadata_status = "loaded"

            # Find the row for this file item and mark for update
            for row, model_file in enumerate(file_model.files):
                if paths_equal(model_file.full_path, file_path):
                    updated_rows.append(row)
                    break

        # Emit dataChanged for all updated rows to refresh their icons
        for row in updated_rows:
            if 0 <= row < len(file_model.files):
                # Emit dataChanged specifically for the icon column (column 0)
                icon_index = file_model.index(row, 0)
                file_model.dataChanged.emit(icon_index, icon_index, [Qt.DecorationRole])

    # =====================================
    # Lazy Loading Methods
    # =====================================

    def try_lazy_metadata_loading(
        self, file_item: Any, _context: str = ""
    ) -> dict[str, Any] | None:
        """Try to load metadata using simple fallback loading (lazy manager removed).

        Args:
            file_item: FileItem to load metadata for
            _context: Context string for logging (unused but kept for API compat)

        Returns:
            dict | None: Metadata if available, None if not cached

        """
        # Since LazyMetadataManager was removed, use direct fallback loading
        return self.fallback_metadata_loading(file_item)

    def fallback_metadata_loading(self, file_item: Any) -> dict[str, Any] | None:
        """Fallback metadata loading method.

        Attempts to load metadata from cache.

        Args:
            file_item: FileItem to load metadata for

        Returns:
            dict | None: Metadata dictionary if found, None otherwise

        """
        try:
            metadata = get_metadata_for_file(file_item.full_path)
            if metadata:
                logger.debug(
                    "Loaded metadata via cache for %s",
                    file_item.filename,
                )
                return metadata

            logger.debug(
                "No metadata found for %s",
                file_item.filename,
            )
            return None

        except Exception:
            logger.exception("Error in fallback metadata loading")
            return None
