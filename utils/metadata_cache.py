"""
Module: metadata_cache.py

Author: Michael Economou
Updated: 2025-05-23

This module defines an in-memory metadata cache system used by the oncutf application.
It stores metadata per file path, wraps each record in a MetadataEntry structure,
and avoids redundant metadata reads. Includes normalized path management and support
for cache querying by extended state.
"""

import os
import time
from typing import Dict, Optional

# Setup Logger
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataEntry:
    """
    Structured container for metadata.

    Attributes:
        data (dict): Raw metadata dictionary
        is_extended (bool): Whether extended metadata (via -ee) was used
        timestamp (float): UNIX timestamp when this entry was stored
    """

    def __init__(self, data: dict, is_extended: bool = False, timestamp: Optional[float] = None):
        self.data = data
        self.is_extended = is_extended
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> dict:
        """Returns a copy of the raw metadata dictionary."""
        return self.data.copy()

    def __repr__(self):
        return f"<MetadataEntry(extended={self.is_extended}, keys={len(self.data)})>"


class MetadataCache:
    """
    An in-memory cache for storing metadata entries by normalized file path.
    Each entry is a MetadataEntry object.
    """

    def __init__(self):
        self._cache: Dict[str, MetadataEntry] = {}

    def _normalize_path(self, file_path: str) -> str:
        """Returns a normalized absolute version of the path."""
        return os.path.abspath(os.path.normpath(file_path))

    def set(self, file_path: str, metadata: dict, is_extended: bool = False):
        """
        Sets or replaces metadata for a file.
        If previous entry is already marked as extended, retain that flag.
        """
        norm_path = self._normalize_path(file_path)
        prev = self._cache.get(norm_path)
        prev_extended = False

        if isinstance(prev, MetadataEntry):
            prev_extended = prev.is_extended
            # Only preserve the extended flag if it was previously true
            is_extended = is_extended or prev.is_extended

        # Check if metadata itself has the __extended__ flag
        metadata_has_extended_flag = isinstance(metadata, dict) and metadata.get("__extended__") is True

        # Final extended status
        final_extended = is_extended or metadata_has_extended_flag

        # More detailed logging
        logger.debug(f"[Cache] SET: {file_path}", extra={"dev_only": True})
        logger.debug(f"[Cache] Previous entry extended: {prev_extended}", extra={"dev_only": True})
        logger.debug(f"[Cache] Input is_extended parameter: {is_extended}", extra={"dev_only": True})
        logger.debug(f"[Cache] Metadata has __extended__ flag: {metadata_has_extended_flag}", extra={"dev_only": True})
        logger.debug(f"[Cache] Final extended status: {final_extended}", extra={"dev_only": True})

        self._cache[norm_path] = MetadataEntry(metadata, is_extended=final_extended)

    def add(self, file_path: str, metadata: dict, is_extended: bool = False):
        """Adds new metadata entry, raises error if path already exists."""
        norm_path = self._normalize_path(file_path)
        if norm_path in self._cache:
            raise KeyError(f"Metadata for '{file_path}' already exists.")
        self._cache[norm_path] = MetadataEntry(metadata, is_extended=is_extended)

    def get(self, file_path: str) -> dict:
        """Returns the raw metadata dict or empty dict if not found."""
        norm_path = self._normalize_path(file_path)
        entry = self._cache.get(norm_path)
        return entry.to_dict() if entry else {}

    def get_entry(self, file_path: str) -> Optional[MetadataEntry]:
        """Returns the MetadataEntry for a file if available."""
        norm_path = self._normalize_path(file_path)
        return self._cache.get(norm_path)

    def __getitem__(self, file_path: str) -> dict:
        return self.get(file_path)

    def has(self, file_path: str) -> bool:
        """Returns True if metadata exists for the file."""
        norm_path = self._normalize_path(file_path)
        return norm_path in self._cache

    def clear(self):
        """Clears the entire metadata cache."""
        self._cache.clear()

    def update(self, other: dict):
        """Merges another dict into this cache, wrapping in MetadataEntry if needed."""
        for k, v in other.items():
            norm_path = self._normalize_path(k)
            if isinstance(v, MetadataEntry):
                self._cache[norm_path] = v
            else:
                self._cache[norm_path] = MetadataEntry(v)

    def retain_only(self, paths: list[str]) -> None:
        """
        Keeps only the metadata entries for the given list of file paths.
        All other entries are removed.
        """
        norm_paths = {self._normalize_path(p) for p in paths}
        self._cache = {
            path: meta for path, meta in self._cache.items() if path in norm_paths
        }

    def is_extended(self, file_path: str) -> bool:
        """
        Returns True if the metadata entry for the given file path is marked as extended.

        Args:
            file_path (str): The full path to the file.

        Returns:
            bool: True if the metadata has __extended__ flag set to True.
        """
        entry = self.get_entry(file_path)
        return isinstance(entry, MetadataEntry) and entry.is_extended


# Global singleton
metadata_cache = MetadataCache()
