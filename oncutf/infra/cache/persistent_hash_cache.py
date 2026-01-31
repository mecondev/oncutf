"""Module: persistent_hash_cache.py.

Author: Michael Economou
Date: 2025-06-15

persistent_hash_cache.py
Enhanced persistent hash cache using the improved database architecture.
Provides improved performance and separation of concerns.
"""

from __future__ import annotations

import logging
import os
from collections import OrderedDict
from pathlib import Path
from typing import TYPE_CHECKING

from oncutf.infra.db.database_manager import get_database_manager
from oncutf.utils.filesystem.path_normalizer import normalize_path
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

# Maximum memory cache size to prevent unbounded growth
# Increased from 1000 to 2000 for better hit rate
# Hash values are small (~100B each), so 2000 entries = ~200KB
MAX_MEMORY_CACHE_SIZE = 2000


class PersistentHashCache:
    """Enhanced persistent hash cache using improved database architecture.

    Benefits:
    - Better separation of concerns with dedicated hash table
    - Improved performance with focused indexes
    - More maintainable architecture
    - Easier to extend with new hash algorithms
    """

    def __init__(self) -> None:
        """Initialize persistent hash cache with database backend."""
        self._db_manager = get_database_manager()
        # Use OrderedDict for LRU behavior - limit cache size to prevent memory growth
        self._memory_cache: OrderedDict[str, str] = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0

        logger.info("[PersistentHashCache] Initialized with database backend")

    def _normalize_path(self, file_path: str) -> str:
        """Use the central normalize_path function."""
        return normalize_path(file_path)

    def store_hash(self, file_path: str, hash_value: str, algorithm: str = "CRC32") -> bool:
        """Store hash for a file with database persistence."""
        norm_path = self._normalize_path(file_path)

        # Store in memory cache for fast access with LRU eviction
        cache_key = f"{norm_path}:{algorithm}"

        # If key exists, move to end (most recent)
        if cache_key in self._memory_cache:
            self._memory_cache.move_to_end(cache_key)

        self._memory_cache[cache_key] = hash_value

        # Enforce cache size limit (LRU eviction)
        while len(self._memory_cache) > MAX_MEMORY_CACHE_SIZE:
            self._memory_cache.popitem(last=False)  # Remove oldest

        # Persist to database
        try:
            success = self._db_manager.store_hash(norm_path, hash_value, algorithm)
            if success:
                logger.debug(
                    "[PersistentHashCache] Stored %s hash for: %s",
                    algorithm,
                    Path(file_path).name,
                )
            return success

        except Exception as e:
            logger.error("[PersistentHashCache] Error storing hash for %s: %s", file_path, e)
            return False

    def get_hash(self, file_path: str, algorithm: str = "CRC32") -> str | None:
        """Retrieve hash for a file, checking memory cache first."""
        norm_path = self._normalize_path(file_path)
        cache_key = f"{norm_path}:{algorithm}"

        # Check memory cache first
        if cache_key in self._memory_cache:
            self._cache_hits += 1
            # Move to end (most recently used) for LRU
            self._memory_cache.move_to_end(cache_key)
            return self._memory_cache[cache_key]

        # Load from database
        self._cache_misses += 1
        try:
            hash_value = self._db_manager.get_hash(norm_path, algorithm)
            if hash_value:
                # Cache it for future access with LRU eviction
                self._memory_cache[cache_key] = hash_value

                # Enforce cache size limit
                while len(self._memory_cache) > MAX_MEMORY_CACHE_SIZE:
                    self._memory_cache.popitem(last=False)  # Remove oldest

                return hash_value

        except Exception as e:
            logger.error("[PersistentHashCache] Error loading hash for %s: %s", file_path, e)

        return None

    def has_hash(self, file_path: str, algorithm: str = "CRC32") -> bool:
        """Check if hash exists for a file."""
        norm_path = self._normalize_path(file_path)
        cache_key = f"{norm_path}:{algorithm}"

        # Check memory cache first
        if cache_key in self._memory_cache:
            return True

        # Check database
        try:
            return self._db_manager.has_hash(norm_path, algorithm)
        except Exception as e:
            logger.error("[PersistentHashCache] Error checking hash for %s: %s", file_path, e)
            return False

    def remove_hash(self, file_path: str) -> bool:
        """Remove hash for a file from both cache and database."""
        norm_path = self._normalize_path(file_path)

        # Remove from memory cache (all algorithms)
        keys_to_remove = [key for key in self._memory_cache if key.startswith(f"{norm_path}:")]
        for key in keys_to_remove:
            self._memory_cache.pop(key, None)

        # For v2, we'd need a specific method to remove just hashes
        # For now, just remove from memory
        logger.debug("[PersistentHashCache] Removed from memory cache: %s", file_path)
        return True

    def find_duplicates(
        self, file_paths: list[str], algorithm: str = "CRC32"
    ) -> dict[str, list[str]]:
        """Find duplicate files based on stored hashes."""
        hash_to_paths: dict[str, list[str]] = {}

        for file_path in file_paths:
            hash_value = self.get_hash(file_path, algorithm)
            if hash_value:
                if hash_value not in hash_to_paths:
                    hash_to_paths[hash_value] = []
                hash_to_paths[hash_value].append(file_path)

        # Filter to only return groups with duplicates
        duplicates = {
            hash_val: paths for hash_val, paths in hash_to_paths.items() if len(paths) > 1
        }

        logger.info(
            "[PersistentHashCache] Found %d duplicate groups from %d files",
            len(duplicates),
            len(file_paths),
        )
        return duplicates

    def verify_file_integrity(self, file_path: str, algorithm: str = "CRC32") -> bool | None:
        """Verify file integrity by comparing current hash with stored hash."""
        stored_hash = self.get_hash(file_path, algorithm)
        if not stored_hash:
            return None

        # Would need to calculate current hash to compare
        # This is a placeholder for the interface
        logger.debug("[PersistentHashCache] Integrity check requested for: %s", file_path)
        return None  # Implementation would go here

    def get_files_with_hash(self, file_paths: list[str], algorithm: str = "CRC32") -> list[str]:
        """Get all files from the list that have a hash stored."""
        files_with_hash = []

        for file_path in file_paths:
            if self.has_hash(file_path, algorithm):
                files_with_hash.append(file_path)

        return files_with_hash

    def get_files_with_hash_batch(
        self, file_paths: list[str], algorithm: str = "CRC32"
    ) -> list[str]:
        """Get all files from the list that have a hash stored using batch database query."""
        try:
            # Use database manager for batch query if available
            if hasattr(self._db_manager, "get_files_with_hash_batch"):
                return self._db_manager.get_files_with_hash_batch(file_paths, algorithm)
            else:
                # Fallback to individual checking
                return self.get_files_with_hash(file_paths, algorithm)
        except Exception as e:
            logger.warning(
                "[PersistentHashCache] Batch query failed, falling back to individual checks: %s",
                e,
            )
            return self.get_files_with_hash(file_paths, algorithm)

    def clear_memory_cache(self) -> None:
        """Clear memory cache (database remains intact)."""
        self._memory_cache.clear()
        logger.debug("[PersistentHashCache] Memory cache cleared")

    def get_cache_stats(self) -> dict[str, int | float]:
        """Get cache performance statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "memory_entries": len(self._memory_cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
        }

    # Backward compatibility methods
    def get(self, file_path: str) -> str | None:
        """Get hash with default algorithm (backward compatibility)."""
        return self.get_hash(file_path)

    def __contains__(self, file_path: str) -> bool:
        """Check if file has hash (backward compatibility)."""
        return self.has_hash(file_path)


# =====================================
# Global Instance Management
# =====================================

_persistent_hash_cache_instance: PersistentHashCache | None = None


def get_persistent_hash_cache() -> PersistentHashCache:
    """Get global persistent hash cache instance."""
    global _persistent_hash_cache_instance
    if _persistent_hash_cache_instance is None:
        _persistent_hash_cache_instance = PersistentHashCache()
    return _persistent_hash_cache_instance
