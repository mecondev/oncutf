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

from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)
logger.debug("[DEBUG] [PersistentMetadataCache] Module imported", extra={"dev_only": True})

try:
    from oncutf.core.database_manager import get_database_manager

    logger.debug(
        "[DEBUG] [PersistentMetadataCache] Successfully imported get_database_manager",
        extra={"dev_only": True},
    )
except Exception as e:
    logger.error("[DEBUG] [PersistentMetadataCache] Error importing get_database_manager: %s", e)
    raise

try:
    from oncutf.utils.path_normalizer import normalize_path

    logger.debug(
        "[DEBUG] [PersistentMetadataCache] Successfully imported normalize_path",
        extra={"dev_only": True},
    )
except Exception as e:
    logger.error("[DEBUG] [PersistentMetadataCache] Error importing normalize_path: %s", e)
    raise


class MetadataEntry:
    """
    Enhanced metadata entry with database persistence support.
    Maintains compatibility with existing MetadataEntry interface.
    """

    def __init__(
        self,
        data: dict,
        is_extended: bool = False,
        timestamp: float | None = None,
        modified: bool = False,
    ):
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
        logger.debug("[DEBUG] [PersistentMetadataCache] __init__ CALLED", extra={"dev_only": True})
        try:
            self._db_manager = get_database_manager()
            logger.debug(
                "[DEBUG] [PersistentMetadataCache] Database manager: %s",
                self._db_manager,
                extra={"dev_only": True},
            )
        except Exception as e:
            logger.error("[DEBUG] [PersistentMetadataCache] Error getting database manager: %s", e)
            raise
        self._memory_cache: dict[str, MetadataEntry] = {}  # Hot cache for performance
        self._cache_hits = 0
        self._cache_misses = 0

        logger.info("[PersistentMetadataCache] Initialized with database backend")

    def _normalize_path(self, file_path: str) -> str:
        """Use the central normalize_path function."""
        return normalize_path(file_path)

    def set(
        self, file_path: str, metadata: dict, is_extended: bool = False, modified: bool = False
    ) -> None:
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
            clean_metadata.pop("__extended__", None)
            clean_metadata.pop("__modified__", None)

            self._db_manager.store_metadata(
                file_path=norm_path,
                metadata=clean_metadata,
                is_extended=is_extended,
                is_modified=modified,
            )

            logger.debug("[PersistentMetadataCache] Stored metadata for: %s", file_path)

        except Exception as e:
            logger.error(
                "[PersistentMetadataCache] Error persisting metadata for %s: %s",
                file_path,
                e,
            )

    def get(self, file_path: str) -> dict:
        """Get metadata for file."""
        norm_path = self._normalize_path(file_path)
        try:
            metadata = self._db_manager.get_metadata(norm_path)
            metadata_keys = len(metadata) if metadata else 0
            logger.debug(
                "[DEBUG] [PersistentMetadataCache] get(%s) -> %d keys",
                file_path,
                metadata_keys,
                extra={"dev_only": True},
            )
            return metadata or {}
        except Exception as e:
            logger.error(
                "[PersistentMetadataCache] Error getting metadata for %s: %s",
                file_path,
                e,
            )
            return {}

    def get_entry(self, path: str):
        """Get the MetadataEntry for a file if available."""
        norm_path = self._normalize_path(path)

        in_memory = norm_path in self._memory_cache

        logger.debug(
            "[PersistentMetadataCache] get_entry: file_path='%s' -> norm_path='%s', in_memory=%s",
            path,
            norm_path,
            in_memory,
            extra={"dev_only": True}
        )

        # Check memory cache first
        if norm_path in self._memory_cache:
            self._cache_hits += 1
            logger.debug(
                "[PersistentMetadataCache] Cache HIT for: %s",
                norm_path,
                extra={"dev_only": True}
            )
            return self._memory_cache[norm_path]

        # Load from database
        self._cache_misses += 1
        try:
            metadata = self._db_manager.get_metadata(norm_path)
            if metadata:
                # Create entry and cache it
                is_extended = metadata.pop("__extended__", False)
                is_modified = metadata.pop("__modified__", False)

                entry = MetadataEntry(metadata, is_extended=is_extended, modified=is_modified)
                self._memory_cache[norm_path] = entry

                return entry

        except Exception as e:
            logger.error(
                "[PersistentMetadataCache] Error loading metadata entry for %s: %s",
                path,
                e,
            )

        return None

    def get_entries_batch(self, file_paths: list[str]) -> dict[str, MetadataEntry | None]:
        """
        Get metadata entries for multiple files in a single batch operation.

        Args:
            file_paths: List of file paths to get entries for

        Returns:
            dict: Mapping of normalized path -> MetadataEntry (or None if not found)
        """
        if not file_paths:
            return {}

        # Normalize all paths
        norm_paths = [self._normalize_path(path) for path in file_paths]
        result = {}
        paths_to_query = []

        # Check memory cache first
        for norm_path in norm_paths:
            if norm_path in self._memory_cache:
                self._cache_hits += 1
                result[norm_path] = self._memory_cache[norm_path]
            else:
                paths_to_query.append(norm_path)

        # Batch query database for remaining paths
        if paths_to_query:
            self._cache_misses += len(paths_to_query)
            try:
                # Use batch query method from database manager
                batch_metadata = self._db_manager.get_metadata_batch(paths_to_query)

                for path in paths_to_query:
                    metadata = batch_metadata.get(path)
                    if metadata:
                        # Create entry and cache it
                        is_extended = metadata.pop("__extended__", False)
                        is_modified = metadata.pop("__modified__", False)

                        entry = MetadataEntry(
                            metadata, is_extended=is_extended, modified=is_modified
                        )
                        self._memory_cache[path] = entry
                        result[path] = entry
                    else:
                        result[path] = None

            except Exception as e:
                logger.error("[PersistentMetadataCache] Error in batch metadata query: %s", e)
                # Fallback: set all remaining paths to None
                for path in paths_to_query:
                    if path not in result:
                        result[path] = None

        return result

    def has(self, file_path: str) -> bool:
        """Check if metadata exists for file."""
        norm_path = self._normalize_path(file_path)
        try:
            result = self._db_manager.has_metadata(norm_path)
            logger.debug(
                "[DEBUG] [PersistentMetadataCache] has(%s) -> %s",
                file_path,
                result,
                extra={"dev_only": True},
            )
            return result
        except Exception as e:
            logger.error(
                "[PersistentMetadataCache] Error checking metadata for %s: %s",
                file_path,
                e,
            )
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
        logger.debug("[PersistentMetadataCache] Removed from memory cache: %s", file_path)
        return True

    def get_cache_stats(self) -> dict:
        """Get cache performance statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "memory_entries": len(self._memory_cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
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
    logger.debug(
        "[DEBUG] [PersistentMetadataCache] get_persistent_metadata_cache CALLED",
        extra={"dev_only": True},
    )
    logger.debug(
        "[DEBUG] [PersistentMetadataCache] Current instance: %s",
        _persistent_metadata_cache_instance,
        extra={"dev_only": True},
    )
    if _persistent_metadata_cache_instance is None:
        logger.debug(
            "[DEBUG] [PersistentMetadataCache] Creating new instance", extra={"dev_only": True}
        )
        try:
            _persistent_metadata_cache_instance = PersistentMetadataCache()
            logger.debug(
                "[DEBUG] [PersistentMetadataCache] Successfully created instance: %s",
                _persistent_metadata_cache_instance,
                extra={"dev_only": True},
            )
        except Exception as e:
            logger.error("[DEBUG] [PersistentMetadataCache] Error creating instance: %s", e)
            # Create a dummy cache to avoid returning None
            logger.warning("[DEBUG] [PersistentMetadataCache] Creating dummy cache due to error")
            _persistent_metadata_cache_instance = DummyMetadataCache()
    else:
        logger.debug(
            "[DEBUG] [PersistentMetadataCache] Using existing instance", extra={"dev_only": True}
        )
    return _persistent_metadata_cache_instance


class DummyMetadataCache:
    """Dummy cache for fallback when database is not available."""

    def __init__(self):
        logger.warning("[DEBUG] [PersistentMetadataCache] DummyMetadataCache initialized")
        self._memory_cache = {}

    def has(self, _file_path: str) -> bool:
        return False

    def get(self, _file_path: str) -> dict:
        return {}

    def set(self, _file_path: str, _metadata: dict, **kwargs) -> None:
        pass

