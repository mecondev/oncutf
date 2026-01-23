"""Metadata cache implementation.

Canonical metadata caching for the application.
Consolidates caching logic from various locations.

Author: Michael Economou
Date: 2026-01-22
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataCache:
    """In-memory metadata cache with TTL support.

    This is a canonical implementation that consolidates various caching
    approaches used throughout the application.

    Features:
    - TTL-based expiration
    - File modification time tracking
    - Thread-safe operations (via dict atomicity)
    - Memory-efficient storage
    """

    def __init__(self, ttl_seconds: float = 300.0) -> None:
        """Initialize metadata cache.

        Args:
            ttl_seconds: Time-to-live for cache entries (default 5 minutes)

        """
        self._cache: dict[str, tuple[dict[str, Any], float, float]] = {}
        # Key -> (metadata, timestamp, mtime)
        self._ttl = ttl_seconds

    def get(self, path: Path) -> dict[str, Any] | None:
        """Get cached metadata for a file.

        Args:
            path: File path

        Returns:
            Cached metadata or None if not found/expired/stale

        """
        key = str(path)

        if key not in self._cache:
            return None

        metadata, cache_time, cached_mtime = self._cache[key]

        # Check TTL
        if time.time() - cache_time > self._ttl:
            logger.debug("Cache expired for %s", path, extra={"dev_only": True})
            del self._cache[key]
            return None

        # Check file modification time
        try:
            current_mtime = path.stat().st_mtime
            if current_mtime != cached_mtime:
                logger.debug("File modified, cache stale for %s", path, extra={"dev_only": True})
                del self._cache[key]
                return None
        except OSError:
            # File no longer exists or not accessible
            logger.debug("File not accessible, removing from cache: %s", path, extra={"dev_only": True})
            del self._cache[key]
            return None

        return metadata

    def set(self, path: Path, metadata: dict[str, Any]) -> None:
        """Store metadata in cache.

        Args:
            path: File path
            metadata: Metadata to cache

        """
        key = str(path)

        try:
            mtime = path.stat().st_mtime
        except OSError:
            logger.warning("Cannot stat file for caching: %s", path)
            mtime = 0.0

        self._cache[key] = (metadata, time.time(), mtime)
        logger.debug("Cached metadata for %s", path, extra={"dev_only": True})

    def invalidate(self, path: Path) -> None:
        """Invalidate cache entry for a file.

        Args:
            path: File path to invalidate

        """
        key = str(path)
        if key in self._cache:
            del self._cache[key]
            logger.debug("Invalidated cache for %s", path, extra={"dev_only": True})

    def clear(self) -> None:
        """Clear all cached data."""
        count = len(self._cache)
        self._cache.clear()
        logger.debug("Cleared %d cache entries", count, extra={"dev_only": True})

    def size(self) -> int:
        """Get number of cached entries.

        Returns:
            Number of entries in cache

        """
        return len(self._cache)

    def cleanup_expired(self) -> int:
        """Remove expired entries from cache.

        Returns:
            Number of entries removed

        """
        current_time = time.time()
        expired_keys = [
            key for key, (_, cache_time, _) in self._cache.items()
            if current_time - cache_time > self._ttl
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug("Cleaned up %d expired cache entries", len(expired_keys))

        return len(expired_keys)


# Global instance (singleton pattern)
_metadata_cache: MetadataCache | None = None


def get_metadata_cache() -> MetadataCache:
    """Get the global metadata cache instance.

    Returns:
        Singleton MetadataCache instance

    """
    global _metadata_cache
    if _metadata_cache is None:
        _metadata_cache = MetadataCache()
    return _metadata_cache


def set_metadata_cache(cache: MetadataCache) -> None:
    """Set a custom metadata cache (useful for testing).

    Args:
        cache: Custom MetadataCache instance

    """
    global _metadata_cache
    _metadata_cache = cache
