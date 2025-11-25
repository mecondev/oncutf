"""
Module: metadata_cache_helper.py

Author: Michael Economou
Date: 2025-06-20

utils/metadata_cache_helper.py
Unified metadata cache access helper to eliminate duplicate patterns.
Provides consistent interface for metadata cache operations across the application.
"""

from typing import Any

from utils.logger_factory import get_cached_logger
from utils.path_normalizer import normalize_path

logger = get_cached_logger(__name__)


class MetadataCacheHelper:
    """
    Unified helper for metadata cache access operations.

    Eliminates duplicate patterns and provides consistent interface
    for getting/setting metadata across the application.
    """

    def __init__(self, metadata_cache=None, parent_window=None):
        """
        Initialize with a metadata cache instance.

        Args:
            metadata_cache: The metadata cache instance to use
            parent_window: Optional parent window for accessing context/managers
        """
        self.metadata_cache = metadata_cache
        self.parent_window = parent_window

    def get_metadata_for_file(
        self, file_item, fallback_to_file_item: bool = True
    ) -> dict[str, Any]:
        """
        Unified metadata retrieval for a file with path normalization.

        Args:
            file_item: FileItem object with full_path attribute
            fallback_to_file_item: Whether to fallback to file_item.metadata if cache is empty

        Returns:
            dict: Metadata dictionary (empty dict if no metadata found)
        """
        if not file_item or not hasattr(file_item, "full_path"):
            return {}

        try:
            # Normalize path for consistent cache access
            normalized_path = normalize_path(file_item.full_path)

            # Try cache first
            if self.metadata_cache:
                # Try get_entry() method first (preferred)
                if hasattr(self.metadata_cache, "get_entry"):
                    cache_entry = self.metadata_cache.get_entry(normalized_path)
                    if cache_entry and hasattr(cache_entry, "data"):
                        # Return data even if it's an empty dict (valid metadata state)
                        return cache_entry.data

                # Fallback to get() method
                if hasattr(self.metadata_cache, "get"):
                    metadata = self.metadata_cache.get(normalized_path)
                    if metadata is not None:  # Allow empty dict
                        return metadata

            # Fallback to file item metadata
            if fallback_to_file_item and hasattr(file_item, "metadata") and file_item.metadata:
                return file_item.metadata

            return {}

        except Exception as e:
            logger.error(
                f"[MetadataCacheHelper] Error getting metadata for {getattr(file_item, 'filename', 'unknown')}: {e}"
            )
            return {}

    def get_cache_entry_for_file(self, file_item):
        """
        Get cache entry object for a file with path normalization.

        Args:
            file_item: FileItem object with full_path attribute

        Returns:
            Cache entry object or None
        """
        if not file_item or not hasattr(file_item, "full_path"):
            return None

        try:
            # Normalize path for consistent cache access
            normalized_path = normalize_path(file_item.full_path)

            if self.metadata_cache and hasattr(self.metadata_cache, "get_entry"):
                return self.metadata_cache.get_entry(normalized_path)
            return None

        except Exception as e:
            logger.error(
                f"[MetadataCacheHelper] Error getting cache entry for {getattr(file_item, 'filename', 'unknown')}: {e}"
            )
            return None

    def set_metadata_for_file(
        self, file_item, metadata: dict[str, Any], is_extended: bool = False, modified: bool = False
    ):
        """
        Unified metadata storage for a file with path normalization.

        Args:
            file_item: FileItem object with full_path attribute
            metadata: Metadata dictionary to store
            is_extended: Whether this is extended metadata
            modified: Whether the metadata has been modified
        """
        if not file_item or not hasattr(file_item, "full_path"):
            return

        try:
            # Normalize path for consistent cache access
            normalized_path = normalize_path(file_item.full_path)

            # Update cache if available (use 'set' method, not 'set_entry')
            if self.metadata_cache and hasattr(self.metadata_cache, "set"):
                self.metadata_cache.set(
                    normalized_path, metadata, is_extended=is_extended, modified=modified
                )

            # Also update file item
            file_item.metadata = metadata

        except Exception as e:
            logger.error(
                f"[MetadataCacheHelper] Error setting metadata for {getattr(file_item, 'filename', 'unknown')}: {e}"
            )

    def has_metadata(self, file_item, extended: bool = None) -> bool:
        """
        Check if a file has metadata with path normalization.

        Args:
            file_item: FileItem object to check
            extended: If specified, check for specific type (True=extended, False=basic, None=any)

        Returns:
            bool: True if file has the requested metadata type
        """
        try:
            cache_entry = self.get_cache_entry_for_file(file_item)

            if cache_entry and hasattr(cache_entry, "data") and cache_entry.data:
                # Filter out internal markers
                real_metadata = {
                    k: v for k, v in cache_entry.data.items() if not k.startswith("__")
                }

                if not real_metadata:
                    return False

                # Check specific type if requested
                if extended is not None:
                    if hasattr(cache_entry, "is_extended"):
                        return cache_entry.is_extended == extended
                    else:
                        # Fallback to marker checking
                        has_extended_marker = "__extended__" in cache_entry.data
                        return has_extended_marker == extended

                return True  # Has some metadata

            # Fallback to file item metadata
            if hasattr(file_item, "metadata") and file_item.metadata:
                real_metadata = {
                    k: v for k, v in file_item.metadata.items() if not k.startswith("__")
                }

                if not real_metadata:
                    return False

                # Check specific type if requested
                if extended is not None:
                    has_extended_marker = "__extended__" in file_item.metadata
                    return has_extended_marker == extended

                return True  # Has some metadata

            return False

        except Exception as e:
            logger.error(
                f"[MetadataCacheHelper] Error checking metadata for {getattr(file_item, 'filename', 'unknown')}: {e}"
            )
            return False

    def get_metadata_value(self, file_item, key_path: str, default: Any = None) -> Any:
        """
        Get a specific metadata value by key path with path normalization.

        Args:
            file_item: FileItem object
            key_path: Key path (e.g., "EXIF/ImageWidth" or "Title")
            default: Default value if not found

        Returns:
            The metadata value or default
        """
        metadata = self.get_metadata_for_file(file_item)

        if not metadata:
            return default

        # Handle nested keys (e.g., "EXIF/ImageWidth")
        if "/" in key_path:
            parts = key_path.split("/")
            value = metadata
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            return value
        else:
            # Simple key
            return metadata.get(key_path, default)

    def set_metadata_value(self, file_item, key_path: str, new_value: Any) -> bool:
        """
        Set a specific metadata value by key path with path normalization.

        Args:
            file_item: FileItem object
            key_path: Key path (e.g., "EXIF/ImageWidth" or "Title")
            new_value: New value to set

        Returns:
            bool: True if value was set successfully
        """
        try:
            # Stage change if possible
            if self.parent_window and hasattr(self.parent_window, 'context'):
                try:
                    staging_manager = self.parent_window.context.get_manager('metadata_staging')
                    staging_manager.stage_change(file_item.full_path, key_path, str(new_value))
                except KeyError:
                    pass

            # Get current metadata
            metadata = self.get_metadata_for_file(file_item, fallback_to_file_item=True)
            if metadata is None or not metadata:
                # If no metadata in cache, this is a problem - we shouldn't edit metadata that doesn't exist
                logger.warning(
                    f"[MetadataCacheHelper] Cannot set {key_path} - no metadata found in cache for {getattr(file_item, 'filename', 'unknown')}. "
                    "Metadata must be loaded before editing.",
                    extra={"dev_only": False},
                )
                return False

            # Special handling for Rotation - always use "Rotation" (capitalized)
            if key_path.lower() == "rotation":
                # Clean up any existing rotation entries (case-insensitive)
                keys_to_remove = [k for k in metadata if k.lower() == "rotation"]
                for k in keys_to_remove:
                    del metadata[k]

                # Also remove from any groups
                for _group_key, group_data in list(metadata.items()):
                    if isinstance(group_data, dict):
                        rotation_keys = [k for k in group_data if k.lower() == "rotation"]
                        for k in rotation_keys:
                            del group_data[k]

                # Set as top-level with correct capitalization
                metadata["Rotation"] = new_value
            # Handle nested keys (e.g., "EXIF/ImageWidth")
            elif "/" in key_path:
                parts = key_path.split("/")
                current = metadata

                # Navigate to parent container
                for part in parts[:-1]:
                    if part not in current or not isinstance(current[part], dict):
                        current[part] = {}
                    current = current[part]

                # Set the final value
                current[parts[-1]] = new_value
            else:
                # Simple key
                metadata[key_path] = new_value

            # Update the metadata in cache and file item
            self.set_metadata_for_file(file_item, metadata, modified=True)

            return True

        except Exception as e:
            logger.error(
                f"[MetadataCacheHelper] Error setting metadata value for {getattr(file_item, 'filename', 'unknown')}: {e}"
            )
            return False

    def is_metadata_modified(self, file_item) -> bool:
        """
        Check if metadata for a file has been modified with path normalization.

        Args:
            file_item: FileItem object to check

        Returns:
            bool: True if metadata has been modified
        """
        try:
            cache_entry = self.get_cache_entry_for_file(file_item)

            if cache_entry and hasattr(cache_entry, "modified"):
                return cache_entry.modified

            return False

        except Exception as e:
            logger.error(
                f"[MetadataCacheHelper] Error checking modification status for {getattr(file_item, 'filename', 'unknown')}: {e}"
            )
            return False


def get_metadata_cache_helper(parent_window=None, metadata_cache=None) -> MetadataCacheHelper:
    """
    Factory function to create MetadataCacheHelper with automatic cache detection.

    Args:
        parent_window: Parent window with metadata_cache attribute
        metadata_cache: Direct metadata cache instance

    Returns:
        MetadataCacheHelper instance
    """
    if metadata_cache:
        cache = metadata_cache
    elif parent_window and hasattr(parent_window, "metadata_cache"):
        cache = parent_window.metadata_cache
    else:
        cache = None

    return MetadataCacheHelper(cache, parent_window)
