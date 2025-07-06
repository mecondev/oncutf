"""
Module: metadata_cache_helper.py

Author: Michael Economou
Date: 2025-06-20

utils/metadata_cache_helper.py
Unified metadata cache access helper to eliminate duplicate patterns.
Provides consistent interface for metadata cache operations across the application.
"""
from typing import Any, Dict

from utils.logger_factory import get_cached_logger
from utils.path_utils import normalize_path

logger = get_cached_logger(__name__)


class MetadataCacheHelper:
    """
    Unified helper for metadata cache access operations.

    Eliminates duplicate patterns and provides consistent interface
    for getting/setting metadata across the application.
    """

    def __init__(self, metadata_cache=None):
        """
        Initialize with a metadata cache instance.

        Args:
            metadata_cache: The metadata cache instance to use
        """
        self.metadata_cache = metadata_cache

    def get_metadata_for_file(self, file_item, fallback_to_file_item: bool = True) -> Dict[str, Any]:
        """
        Unified metadata retrieval for a file with path normalization.

        Args:
            file_item: FileItem object with full_path attribute
            fallback_to_file_item: Whether to fallback to file_item.metadata if cache is empty

        Returns:
            dict: Metadata dictionary (empty dict if no metadata found)
        """
        if not file_item or not hasattr(file_item, 'full_path'):
            return {}

        try:
            # Normalize path for consistent cache access
            normalized_path = normalize_path(file_item.full_path)

            # Try cache first
            if self.metadata_cache:
                # Try get_entry() method first (preferred)
                if hasattr(self.metadata_cache, 'get_entry'):
                    cache_entry = self.metadata_cache.get_entry(normalized_path)
                    if cache_entry and hasattr(cache_entry, 'data') and cache_entry.data:
                        return cache_entry.data

                # Fallback to get() method
                if hasattr(self.metadata_cache, 'get'):
                    metadata = self.metadata_cache.get(normalized_path)
                    if metadata:
                        return metadata

            # Fallback to file item metadata
            if fallback_to_file_item and hasattr(file_item, 'metadata') and file_item.metadata:
                return file_item.metadata

            return {}

        except Exception as e:
            logger.debug(f"[MetadataCacheHelper] Error getting metadata for {getattr(file_item, 'filename', 'unknown')}: {e}")
            return {}

    def get_cache_entry_for_file(self, file_item):
        """
        Get cache entry object for a file with path normalization.

        Args:
            file_item: FileItem object with full_path attribute

        Returns:
            Cache entry object or None
        """
        if not file_item or not hasattr(file_item, 'full_path'):
            return None

        try:
            # Normalize path for consistent cache access
            normalized_path = normalize_path(file_item.full_path)

            if self.metadata_cache and hasattr(self.metadata_cache, 'get_entry'):
                return self.metadata_cache.get_entry(normalized_path)
            return None

        except Exception as e:
            logger.debug(f"[MetadataCacheHelper] Error getting cache entry for {getattr(file_item, 'filename', 'unknown')}: {e}")
            return None

    def set_metadata_for_file(self, file_item, metadata: Dict[str, Any], is_extended: bool = False, modified: bool = False):
        """
        Unified metadata storage for a file with path normalization.

        Args:
            file_item: FileItem object with full_path attribute
            metadata: Metadata dictionary to store
            is_extended: Whether this is extended metadata
            modified: Whether the metadata has been modified
        """
        if not file_item or not hasattr(file_item, 'full_path'):
            return

        try:
            # Normalize path for consistent cache access
            normalized_path = normalize_path(file_item.full_path)

            # Update cache if available
            if self.metadata_cache and hasattr(self.metadata_cache, 'set_entry'):
                self.metadata_cache.set_entry(
                    normalized_path,
                    metadata,
                    is_extended=is_extended,
                    modified=modified
                )

            # Also update file item
            file_item.metadata = metadata

        except Exception as e:
            logger.error(f"[MetadataCacheHelper] Error setting metadata for {getattr(file_item, 'filename', 'unknown')}: {e}")

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

            if cache_entry and hasattr(cache_entry, 'data') and cache_entry.data:
                # Filter out internal markers
                real_metadata = {k: v for k, v in cache_entry.data.items() if not k.startswith('__')}

                if not real_metadata:
                    return False

                # Check specific type if requested
                if extended is not None:
                    if hasattr(cache_entry, 'is_extended'):
                        return cache_entry.is_extended == extended
                    else:
                        # Fallback to marker checking
                        has_extended_marker = '__extended__' in cache_entry.data
                        return has_extended_marker == extended

                return True  # Has some metadata

            # Fallback to file item metadata
            if hasattr(file_item, 'metadata') and file_item.metadata:
                real_metadata = {k: v for k, v in file_item.metadata.items() if not k.startswith('__')}

                if not real_metadata:
                    return False

                # Check specific type if requested
                if extended is not None:
                    has_extended_marker = '__extended__' in file_item.metadata
                    return has_extended_marker == extended

                return True  # Has some metadata

            return False

        except Exception as e:
            logger.debug(f"[MetadataCacheHelper] Error checking metadata for {getattr(file_item, 'filename', 'unknown')}: {e}")
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
        if '/' in key_path:
            parts = key_path.split('/')
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

            if cache_entry and hasattr(cache_entry, 'modified'):
                return cache_entry.modified

            return False

        except Exception as e:
            logger.debug(f"[MetadataCacheHelper] Error checking modification status for {getattr(file_item, 'filename', 'unknown')}: {e}")
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
    elif parent_window and hasattr(parent_window, 'metadata_cache'):
        cache = parent_window.metadata_cache
    else:
        cache = None

    return MetadataCacheHelper(cache)
