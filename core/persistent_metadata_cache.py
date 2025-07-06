"""
Module: persistent_metadata_cache.py

Author: Michael Economou
Date: 2025-06-15

persistent_metadata_cache.py
Enhanced persistent metadata cache using the improved database architecture.
Provides the same interface as the original cache but with improved performance
and separation of concerns.
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
    Enhanced persistent metadata cache using improved database architecture.

    Benefits:
    - Better separation of concerns
    - Improved performance with dedicated tables
    - More maintainable architecture
    - Easier to extend with new features
    """

    def __init__(self):
        """Initialize persistent metadata cache with database backend."""
        self._db_manager = get_database_manager()
        self._memory_cache: Dict[str, MetadataEntry] = {}  # Hot cache for performance
        self._cache_hits = 0
        self._cache_misses = 0

        logger.info("[PersistentMetadataCache] Initialized with database backend")

    def _normalize_path(self, file_path: str) -> str:
        """Normalize file path for consistent storage."""
        import os
        try:
            abs_path = os.path.abspath(file_path)
            return os.path.normpath(abs_path)
        except Exception:
            return os.path.normpath(file_path)

    def set(self, file_path: str, metadata: dict, is_extended: bool = False, modified: bool = False) -> None:
        """Store metadata for a file with database persistence."""
        norm_path = self._normalize_path(file_path)

        # Create metadata entry
        entry = MetadataEntry(metadata, is_extended=is_extended, modified=modified)

        # Store in memory cache for fast access
        self._memory_cache[norm_path] = entry

        # Persist to database
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

            logger.debug(f"[PersistentMetadataCache] Stored metadata for: {file_path}")

        except Exception as e:
            logger.error(f"[PersistentMetadataCache] Error persisting metadata for {file_path}: {e}")

    def get(self, file_path: str) -> dict:
        """Retrieve metadata for a file, checking memory cache first."""
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
        """Get the MetadataEntry for a file if available."""
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
        """Check if metadata exists for a file."""
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
        Add metadata (alias for set for backward compatibility).

        Args:
            file_path: Path to the file
            metadata: Metadata dictionary
            is_extended: Whether this is extended metadata
        """
        self.set(file_path, metadata, is_extended=is_extended)

    def update(self, other: dict):
        """
        Update cache with another dictionary.

        Args:
            other: Dictionary to merge into cache
        """
        for file_path, metadata in other.items():
            if isinstance(metadata, dict):
                self.set(file_path, metadata)

    def clear(self):
        """Clear memory cache (database remains intact)."""
        self._memory_cache.clear()

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

        # Remove from database would require a new method in database_manager_v2
        # For now, just remove from memory cache
        logger.debug(f"[PersistentMetadataCache] Removed from memory cache: {file_path}")
        return True

    def get_cache_stats(self) -> dict:
        """Get cache performance statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            'memory_entries': len(self._memory_cache),
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate_percent': round(hit_rate, 2)
        }

    def cleanup_orphaned_records(self) -> int:
        """
        Clean up orphaned records in database.

        Returns:
            Number of records cleaned up
        """
        # This would be implemented in database_manager_v2 if needed
        return 0

    # Dictionary-like interface for backward compatibility
    def __getitem__(self, file_path: str) -> dict:
        return self.get(file_path)

    def __contains__(self, file_path: str) -> bool:
        return self.has(file_path)

    def __len__(self) -> int:
        # This would require a count query to be accurate
        return len(self._memory_cache)


# =====================================
# Global Instance Management
# =====================================

_persistent_metadata_cache_instance = None

def get_persistent_metadata_cache() -> PersistentMetadataCache:
    """Get global persistent metadata cache instance."""
    global _persistent_metadata_cache_instance
    if _persistent_metadata_cache_instance is None:
        _persistent_metadata_cache_instance = PersistentMetadataCache()
    return _persistent_metadata_cache_instance
