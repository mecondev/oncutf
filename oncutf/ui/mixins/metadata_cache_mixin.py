"""Metadata cache interaction mixin for MetadataTreeView.

This mixin handles all interactions with the persistent metadata cache,
including reading, updating, and removing cached metadata values.
Extracted from MetadataTreeView as part of decomposition effort.
"""

from typing import Any

from PyQt5.QtCore import Qt

from oncutf.utils.filesystem.path_utils import paths_equal
from oncutf.utils.logging.logger_helper import get_logger

logger = get_logger(__name__)


class MetadataCacheMixin:
    """Mixin providing cache interaction methods for metadata tree views.

    This mixin encapsulates all logic related to the persistent metadata cache:
    - Getting/setting metadata values in cache
    - Updating file item metadata attributes
    - Icon status updates based on modification state
    - Lazy loading fallback methods

    Requirements:
        - Must be mixed with a QTreeView subclass
        - Host class must provide: _get_current_selection(), _get_cache_helper(),
          _get_parent_with_file_table(), _get_value_from_metadata_dict()
        - Host class should have: _direct_loader, _cache_helper, _current_file_path
    """

    # =====================================
    # Cache Access Methods
    # =====================================

    def _get_metadata_cache(self):
        """Get metadata cache via parent traversal.

        Returns:
            dict | None: Metadata cache dictionary if found, None otherwise

        """
        parent_window = self._get_parent_with_file_table()
        if parent_window and hasattr(parent_window, "metadata_cache"):
            return parent_window.metadata_cache

        return None

    def _get_original_value_from_cache(self, key_path: str) -> Any | None:
        """Get the original value of a metadata field from the cache.
        This should be called before resetting to get the original value.

        Args:
            key_path: Metadata key path (e.g., "EXIF/DateTimeOriginal")

        Returns:
            Any | None: Original value if found, None otherwise

        """
        selected_files = self._get_current_selection()
        if not selected_files:
            return None

        file_item = selected_files[0]
        cache_helper = self._get_cache_helper()
        if not cache_helper:
            return None

        # Use cache helper for unified access
        return cache_helper.get_metadata_value(file_item, key_path)

    def _get_original_metadata_value(self, key_path: str) -> Any | None:
        """Get the ORIGINAL metadata value (not staged) for comparison.
        Used by smart_mark_modified to check against actual original values.

        Args:
            key_path: Metadata key path (e.g., "EXIF/DateTimeOriginal")

        Returns:
            Any | None: Original metadata value if found, None otherwise

        """
        selected_files = self._get_current_selection()
        if not selected_files:
            return None

        file_item = selected_files[0]
        cache_helper = self._get_cache_helper()
        if not cache_helper:
            return None

        # Get original metadata entry (not staged version)
        metadata_entry = cache_helper.get_cache_entry_for_file(file_item)
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
        elif len(parts) == 2:
            # Nested key (group/key)
            group, key = parts
            if group in metadata and isinstance(metadata[group], dict):
                return metadata[group].get(key)

        return None

    # =====================================
    # Cache Update Methods
    # =====================================

    def _update_metadata_in_cache(self, key_path: str, new_value: str) -> None:
        """Update the metadata value in the cache to persist changes.

        Args:
            key_path: Metadata key path
            new_value: New value to store

        """
        selected_files = self._get_current_selection()
        if not selected_files:
            return

        file_item = selected_files[0]
        cache_helper = self._get_cache_helper()
        if not cache_helper:
            return

        # Update cache entry
        cache_helper.set_metadata_value(file_item, key_path, new_value)

        # Mark cache entry as modified
        cache_entry = cache_helper.get_cache_entry_for_file(file_item)
        if cache_entry:
            cache_entry.modified = True

        # Update file item status
        file_item.metadata_status = "modified"

        logger.debug(
            "[MetadataCacheMixin] Updated %s in cache for %s",
            key_path,
            file_item.filename,
            extra={"dev_only": True},
        )

    def _set_metadata_in_cache(self, key_path: str, new_value: str) -> None:
        """Set metadata value in cache (similar to update, but used in specific contexts).

        Args:
            key_path: Metadata key path
            new_value: New value to store

        """
        selected_files = self._get_current_selection()
        if not selected_files:
            return

        file_item = selected_files[0]
        cache_helper = self._get_cache_helper()
        if not cache_helper:
            return

        # Set value in cache
        cache_helper.set_metadata_value(file_item, key_path, new_value)

        logger.debug(
            "[MetadataCacheMixin] Set %s in cache for %s",
            key_path,
            file_item.filename,
            extra={"dev_only": True},
        )

    def _set_metadata_in_file_item(self, key_path: str, new_value: str) -> None:
        """Set metadata value directly in file_item.metadata dict.
        Used for direct updates bypassing cache helper.

        Args:
            key_path: Metadata key path
            new_value: New value to store

        """
        selected_files = self._get_current_selection()
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
            "[MetadataCacheMixin] Set %s in file_item.metadata for %s",
            key_path,
            file_item.filename,
            extra={"dev_only": True},
        )

    def _reset_metadata_in_cache(self, key_path: str) -> None:
        """Reset the metadata value in the cache to its original state.

        Args:
            key_path: Metadata key path to reset

        """
        selected_files = self._get_current_selection()
        if not selected_files:
            return

        file_item = selected_files[0]
        cache_helper = self._get_cache_helper()
        if not cache_helper:
            return

        # Get the original value from file item metadata
        original_value = None
        if hasattr(file_item, "metadata") and file_item.metadata:
            original_value = self._get_value_from_metadata_dict(file_item.metadata, key_path)

        # Update cache with original value or remove if no original
        if original_value is not None:
            cache_helper.set_metadata_value(file_item, key_path, original_value)
        else:
            # Remove from cache if no original value
            cache_entry = cache_helper.get_cache_entry_for_file(file_item)
            if cache_entry and hasattr(cache_entry, "data") and key_path in cache_entry.data:
                del cache_entry.data[key_path]

        # Update file icon status based on remaining modified items
        if not hasattr(self, "modified_items") or not self.modified_items:
            file_item.metadata_status = "loaded"
            cache_entry = cache_helper.get_cache_entry_for_file(file_item)
            if cache_entry:
                cache_entry.modified = False
        else:
            file_item.metadata_status = "modified"

        # Trigger UI update
        self._update_file_icon_status()

    def _remove_metadata_from_cache(self, key_path: str) -> None:
        """Remove a metadata key from the cache.

        Args:
            key_path: Metadata key path to remove

        """
        selected_files = self._get_current_selection()
        if not selected_files:
            return

        file_item = selected_files[0]
        cache_helper = self._get_cache_helper()
        if not cache_helper:
            return

        # Remove from cache entry
        cache_entry = cache_helper.get_cache_entry_for_file(file_item)
        if cache_entry and hasattr(cache_entry, "data") and key_path in cache_entry.data:
            del cache_entry.data[key_path]

        logger.debug(
            "[MetadataCacheMixin] Removed %s from cache for %s",
            key_path,
            file_item.filename,
            extra={"dev_only": True},
        )

    def _remove_metadata_from_file_item(self, key_path: str) -> None:
        """Remove a metadata key from file_item.metadata dict.

        Args:
            key_path: Metadata key path to remove

        """
        selected_files = self._get_current_selection()
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
            if group in file_item.metadata and isinstance(file_item.metadata[group], dict):
                if key in file_item.metadata[group]:
                    del file_item.metadata[group][key]

    # =====================================
    # Icon Status Updates
    # =====================================

    def _update_file_icon_status(self) -> None:
        """Update the file icon in the file table to reflect modified status.
        Checks staging manager for modifications and updates file model icons.
        """
        selected_files = self._get_current_selection()
        if not selected_files:
            return

        # Get parent window and file model
        parent_window = self._get_parent_with_file_table()
        if not parent_window:
            return

        file_model = parent_window.file_model
        if not file_model:
            return

        # Get staging manager
        from oncutf.core.metadata import get_metadata_staging_manager

        staging_manager = get_metadata_staging_manager()

        # For each selected file, update its icon
        updated_rows = []
        for file_item in selected_files:
            # Check if this specific file has modified items
            file_path = file_item.full_path

            # Check if this file has modifications
            has_modifications = False

            if staging_manager:
                has_modifications = staging_manager.has_staged_changes(file_path)

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

    def _try_lazy_metadata_loading(
        self, file_item: Any, _context: str = ""
    ) -> dict[str, Any] | None:
        """Try to load metadata using simple fallback loading (lazy manager removed).

        Args:
            file_item: FileItem to load metadata for
            context: Context string for logging (unused but kept for API compat)

        Returns:
            dict | None: Metadata if available, None if not cached

        """
        # Since LazyMetadataManager was removed, use direct fallback loading
        return self._fallback_metadata_loading(file_item)

    def _fallback_metadata_loading(self, file_item: Any) -> dict[str, Any] | None:
        """Fallback metadata loading method.
        Attempts to load metadata from cache helper.

        Args:
            file_item: FileItem to load metadata for

        Returns:
            dict | None: Metadata dictionary if found, None otherwise

        """
        try:
            if hasattr(self, "_cache_helper") and self._cache_helper:
                metadata = self._cache_helper.get_metadata_for_file(file_item)
                if metadata:
                    logger.debug(
                        "[MetadataCacheMixin] Loaded metadata via cache helper for %s",
                        file_item.filename,
                        extra={"dev_only": True},
                    )
                    return metadata

            logger.debug(
                "[MetadataCacheMixin] No metadata found for %s",
                file_item.filename,
                extra={"dev_only": True},
            )
            return None

        except Exception as e:
            logger.exception("[MetadataCacheMixin] Error in fallback metadata loading: %s", e)
            return None
