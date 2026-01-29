"""Cache service for metadata and hash operations.

Author: Michael Economou
Date: 2026-01-24

This service provides a clean interface to cache operations,
isolating UI widgets from direct cache dependencies.

Architecture:
- UI widgets → CacheService → Core cache implementations
- No direct imports of cache classes in UI layer
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.app.ports.infra_protocols import HashCacheProtocol, MetadataCacheProtocol


# Factory functions - registered during bootstrap
_hash_cache_factory: Any = None
_metadata_cache_factory: Any = None


def register_hash_cache_factory(factory: Any) -> None:
    """Register factory for creating hash cache instances."""
    global _hash_cache_factory
    _hash_cache_factory = factory


def register_metadata_cache_factory(factory: Any) -> None:
    """Register factory for creating metadata cache instances."""
    global _metadata_cache_factory
    _metadata_cache_factory = factory


class CacheService:
    """Service for accessing metadata and hash caches.

    This service wraps cache implementations and provides a clean
    interface for UI widgets to access cached data without
    directly importing cache classes.

    Usage:
        service = CacheService()
        metadata = service.get_metadata(file_path)
        has_hash = service.has_hash(file_path, "CRC32")
    """

    def __init__(self) -> None:
        """Initialize cache service."""
        self._metadata_cache: MetadataCacheProtocol | None = None
        self._hash_cache: HashCacheProtocol | None = None

    def _get_metadata_cache(self) -> MetadataCacheProtocol | None:
        """Get metadata cache instance (lazy loading via factory)."""
        if self._metadata_cache is None and _metadata_cache_factory is not None:
            self._metadata_cache = _metadata_cache_factory()
        return self._metadata_cache

    def _get_hash_cache(self) -> HashCacheProtocol | None:
        """Get hash cache instance (lazy loading via factory)."""
        if self._hash_cache is None and _hash_cache_factory is not None:
            self._hash_cache = _hash_cache_factory()
        return self._hash_cache

    def get_metadata_entry(self, file_path: str) -> dict[str, Any] | None:
        """Get metadata entry for a file.

        Args:
            file_path: Path to the file

        Returns:
            Metadata dictionary or None if not cached

        """
        cache = self._get_metadata_cache()
        if not cache:
            return None

        try:
            # Use the protocol's get_metadata method
            return cache.get_metadata(file_path)
        except Exception:
            return None

    def get_metadata_keys(self, file_path: str) -> set[str]:
        """Get set of metadata keys for a file.

        Args:
            file_path: Path to the file

        Returns:
            Set of metadata key names

        """
        entry = self.get_metadata_entry(file_path)
        if not entry or not isinstance(entry, dict):
            return set()

        # Extract keys from metadata entry
        if "metadata" in entry:
            return set(entry["metadata"].keys())
        return set()

    def has_hash(self, file_path: str, hash_type: str = "CRC32") -> bool:
        """Check if file has a cached hash.

        Args:
            file_path: Path to the file
            hash_type: Type of hash to check (default: CRC32)

        Returns:
            True if hash exists in cache

        """
        cache = self._get_hash_cache()
        if not cache:
            return False

        files_with_hash = cache.get_files_with_hash_batch([file_path], hash_type)
        return file_path in files_with_hash

    def get_files_with_hash_batch(
        self, file_paths: list[str], hash_type: str = "CRC32"
    ) -> set[str]:
        """Get set of files that have cached hashes.

        Args:
            file_paths: List of file paths to check
            hash_type: Type of hash to check (default: CRC32)

        Returns:
            Set of file paths that have cached hashes

        """
        cache = self._get_hash_cache()
        if not cache:
            return set()

        return cache.get_files_with_hash_batch(file_paths, hash_type)


# Singleton instance
_cache_service: CacheService | None = None


def get_cache_service() -> CacheService:
    """Get the global CacheService instance.

    Returns:
        Singleton CacheService instance

    """
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
