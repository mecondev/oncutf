"""Cached-only hash service for rename operations.

Author: Michael Economou
Date: December 19, 2025

This service returns ONLY cached hashes - it never computes them.
Used by rename modules to avoid expensive hash computations during preview.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from oncutf.infra.cache.persistent_hash_cache import PersistentHashCache

logger = get_cached_logger(__name__)


class CachedHashService:
    """Hash service that returns only cached hashes.

    Implements HashServiceProtocol but never computes hashes.
    Returns empty string if hash is not in cache.

    This is used by rename modules to ensure no expensive hash computation
    happens during preview generation.
    """

    def __init__(self) -> None:
        """Initialize the cached hash service."""
        self._cache_manager: PersistentHashCache | None = None

    def _get_cache_manager(self) -> PersistentHashCache:
        """Lazy load the hash cache manager."""
        if self._cache_manager is None:
            from oncutf.infra.cache.persistent_hash_cache import (
                get_persistent_hash_cache,
            )

            self._cache_manager = get_persistent_hash_cache()
        return self._cache_manager

    def compute_hash(
        self,
        path: Path,
        algorithm: str = "crc32",
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> str:
        """Get cached hash (never computes).

        Args:
            path: Path to the file.
            algorithm: Hash algorithm (crc32, md5, sha256, sha1).
            progress_callback: Ignored (never computes).

        Returns:
            Cached hash or empty string if not in cache.

        """
        try:
            cache = self._get_cache_manager()
            cached_value = cache.get_hash(str(path), algorithm.upper())
            if cached_value:
                logger.debug(
                    "Cache hit for %s (%s)",
                    path.name,
                    algorithm,
                    extra={"dev_only": True},
                )
                return cached_value

            logger.debug(
                "Cache miss for %s (%s) - returning empty",
                path.name,
                algorithm,
                extra={"dev_only": True},
            )
        except Exception as e:
            logger.warning("Error getting cached hash for %s: %s", path, e)
            return ""
        else:
            return ""

    def compute_hashes_batch(
        self,
        paths: list[Path],
        algorithm: str = "crc32",
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[Path, str]:
        """Get cached hashes for multiple files (never computes).

        Args:
            paths: List of file paths.
            algorithm: Hash algorithm.
            progress_callback: Ignored (never computes).

        Returns:
            Dict mapping paths to cached hashes (empty string if not cached).

        """
        results = {}
        for path in paths:
            results[path] = self.compute_hash(path, algorithm)
        return results
