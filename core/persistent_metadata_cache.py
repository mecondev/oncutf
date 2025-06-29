"""
persistent_metadata_cache.py

Author: Michael Economou
Date: 2025-01-27

Persistent metadata cache that bridges the existing MetadataCache interface
with the new DatabaseManager backend. Provides backward compatibility while
adding database persistence.

Features:
- Drop-in replacement for existing MetadataCache
- Automatic database persistence of metadata
- Seamless migration from memory-only to persistent storage
- Maintains existing API for compatibility
"""

import time
from typing import Dict, Optional

from core.database_manager import get_database_manager
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataEntry:
    """
    Enhanced metadata entry with database persistence support.
    Maintains compatibility with existing MetadataEntry interface.
    """

    def __init__(self, data: dict, is_extended: bool = False, timestamp: Optional[float] = None, modified: bool = False):
        self.data = data
        self.is_extended = is_extended
        self.timestamp = timestamp or time.time()
        self.modified = modified

    def to_dict(self) -> dict:
        """Returns a copy of the raw metadata dictionary."""
        return self.data.copy()

    def __repr__(self):
        return f"<MetadataEntry(extended={self.is_extended}, keys={len(self.data)}, modified={self.modified})>"


class PersistentMetadataCache:
    """
    Persistent metadata cache that stores data in SQLite database.

    Provides the same interface as the original MetadataCache but with
    automatic database persistence and enhanced features.
    """

    def __init__(self):
        """Initialize persistent metadata cache with database backend."""
        self._db_manager = get_database_manager()
        self._memory_cache: Dict[str, MetadataEntry] = {}  # Hot cache for performance
        self._cache_hits = 0
        self._cache_misses = 0

        logger.info("[PersistentMetadataCache] Initialized with database backend")

    def _normalize_path(self, file_path: str) -> str:
        """
        Normalize file path for consistent storage.

        Converts to absolute path and normalizes to ensure consistent
        storage and retrieval regardless of how the path was specified.
        """
        import os
        try:
            # Convert to absolute path first, then normalize
            abs_path = os.path.abspath(file_path)
            return os.path.normpath(abs_path)
        except Exception:
            # Fallback to basic normalization if abspath fails
            return os.path.normpath(file_path)

    def set(self, file_path: str, metadata: dict, is_extended: bool = False, modified: bool = False) -> None:
        """
        Store metadata for a file with database persistence.

        Args:
            file_path: Path to the file
            metadata: Metadata dictionary
            is_extended: Whether this is extended metadata
            modified: Whether metadata has been modified by user
        """
        norm_path = self._normalize_path(file_path)

        # Create metadata entry
        entry = MetadataEntry(metadata, is_extended=is_extended, modified=modified)

        # Store in memory cache for fast access
        self._memory_cache[norm_path] = entry

        # Persist to database asynchronously
        try:
            # Clean metadata for database storage (remove internal flags)
            clean_metadata = metadata.copy()
            clean_metadata.pop('__extended__', None)
            clean_metadata.pop('__modified__', None)

            self._db_manager.store_metadata(
                file_path=norm_path,
                metadata=clean_metadata,
                is_extended=is_extended,
                is_modified=modified
            )

            # Update modified flag in database if needed
            if modified:
                self._db_manager.update_metadata_modified_flag(norm_path, True)

            logger.debug(f"[PersistentMetadataCache] Stored metadata for: {file_path}")

        except Exception as e:
            logger.error(f"[PersistentMetadataCache] Error persisting metadata for {file_path}: {e}")

    def get(self, file_path: str) -> dict:
        """
        Retrieve metadata for a file, checking memory cache first.

        Args:
            file_path: Path to the file

        Returns:
            Metadata dictionary or empty dict if not found
        """
        norm_path = self._normalize_path(file_path)

        # Check memory cache first
        if norm_path in self._memory_cache:
            self._cache_hits += 1
            return self._memory_cache[norm_path].to_dict()

        # Load from database
        self._cache_misses += 1
        try:
            metadata = self._db_manager.get_metadata(norm_path)
            if metadata:
                # Create entry and cache it
                is_extended = metadata.pop('__extended__', False)
                is_modified = metadata.pop('__modified__', False)

                entry = MetadataEntry(metadata, is_extended=is_extended, modified=is_modified)
                self._memory_cache[norm_path] = entry

                return entry.to_dict()

        except Exception as e:
            logger.error(f"[PersistentMetadataCache] Error loading metadata for {file_path}: {e}")

        return {}

    def get_entry(self, file_path: str) -> Optional[MetadataEntry]:
        """
        Get the MetadataEntry for a file if available.

        Args:
            file_path: Path to the file

        Returns:
            MetadataEntry or None if not found
        """
        norm_path = self._normalize_path(file_path)

        # Check memory cache first
        if norm_path in self._memory_cache:
            self._cache_hits += 1
            return self._memory_cache[norm_path]

        # Load from database
        self._cache_misses += 1
        try:
            metadata = self._db_manager.get_metadata(norm_path)
            if metadata:
                # Create entry and cache it
                is_extended = metadata.pop('__extended__', False)
                is_modified = metadata.pop('__modified__', False)

                entry = MetadataEntry(metadata, is_extended=is_extended, modified=is_modified)
                self._memory_cache[norm_path] = entry

                return entry

        except Exception as e:
            logger.error(f"[PersistentMetadataCache] Error loading metadata entry for {file_path}: {e}")

        return None

    def has(self, file_path: str) -> bool:
        """
        Check if metadata exists for a file.

        Args:
            file_path: Path to the file

        Returns:
            True if metadata exists
        """
        norm_path = self._normalize_path(file_path)

        # Check memory cache first
        if norm_path in self._memory_cache:
            return True

        # Check database
        try:
            return self._db_manager.has_metadata(norm_path)
        except Exception as e:
            logger.error(f"[PersistentMetadataCache] Error checking metadata for {file_path}: {e}")
            return False

    def add(self, file_path: str, metadata: dict, is_extended: bool = False):
        """
        Add new metadata entry, raises error if path already exists.

        Args:
            file_path: Path to the file
            metadata: Metadata dictionary
            is_extended: Whether this is extended metadata
        """
        norm_path = self._normalize_path(file_path)

        if self.has(norm_path):
            raise KeyError(f"Metadata for '{file_path}' already exists.")

        self.set(norm_path, metadata, is_extended=is_extended)

    def update(self, other: dict):
        """
        Merge another dict into this cache.

        Args:
            other: Dictionary to merge
        """
        for file_path, value in other.items():
            if isinstance(value, MetadataEntry):
                self.set(file_path, value.data, is_extended=value.is_extended, modified=value.modified)
            else:
                self.set(file_path, value)

    def clear(self):
        """Clear the memory cache (database remains intact)."""
        self._memory_cache.clear()
        logger.info("[PersistentMetadataCache] Memory cache cleared")

    def remove(self, file_path: str) -> bool:
        """
        Remove metadata for a file from both cache and database.

        Args:
            file_path: Path to the file

        Returns:
            True if removed successfully
        """
        norm_path = self._normalize_path(file_path)

        # Remove from memory cache
        self._memory_cache.pop(norm_path, None)

        # Remove from database
        try:
            return self._db_manager.remove_file(norm_path)
        except Exception as e:
            logger.error(f"[PersistentMetadataCache] Error removing metadata for {file_path}: {e}")
            return False

    def get_cache_stats(self) -> dict:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            'memory_cache_size': len(self._memory_cache),
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate_percent': round(hit_rate, 2),
            'database_stats': self._db_manager.get_database_stats()
        }

    def cleanup_orphaned_records(self) -> int:
        """
        Clean up database records for files that no longer exist.

        Returns:
            Number of records cleaned up
        """
        try:
            cleaned_count = self._db_manager.cleanup_orphaned_records()

            # Also clean memory cache
            orphaned_paths = []
            for path in self._memory_cache:
                import os
                if not os.path.exists(path):
                    orphaned_paths.append(path)

            for path in orphaned_paths:
                self._memory_cache.pop(path, None)

            if orphaned_paths:
                logger.info(f"[PersistentMetadataCache] Cleaned {len(orphaned_paths)} orphaned entries from memory cache")

            return cleaned_count

        except Exception as e:
            logger.error(f"[PersistentMetadataCache] Error during cleanup: {e}")
            return 0

    def __getitem__(self, file_path: str) -> dict:
        """Dictionary-style access to metadata."""
        return self.get(file_path)

    def __contains__(self, file_path: str) -> bool:
        """Support for 'in' operator."""
        return self.has(file_path)

    def __len__(self) -> int:
        """Return number of cached entries."""
        return len(self._memory_cache)


# Global instance for easy migration
_persistent_cache: Optional[PersistentMetadataCache] = None


def get_persistent_metadata_cache() -> PersistentMetadataCache:
    """Get global PersistentMetadataCache instance."""
    global _persistent_cache
    if _persistent_cache is None:
        _persistent_cache = PersistentMetadataCache()
    return _persistent_cache
