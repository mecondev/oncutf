"""oncutf.core.rename.query_managers.

Batch query and cache management utilities for the rename engine.

This module provides the BatchQueryManager for efficient batch queries of
hash and metadata availability, and SmartCacheManager for lightweight
in-memory caching of preview and validation results.

Author: Michael Economou
Date: 2026-01-01
"""

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

from oncutf.core.rename.data_classes import PreviewResult, ValidationResult
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class BatchQueryManager:
    """Batch helper to fetch availability information for sets of files.

    This manager centralizes queries that benefit from batch access patterns,
    such as checking whether CRC32 hashes or metadata exist for a list of
    files. The implementation uses the persistent caches defined elsewhere in
    the application to avoid expensive per-file operations.
    """

    def __init__(self):
        """Initialize the batch query manager with empty cache references."""
        self._hash_cache = None
        self._metadata_cache = None

    def get_hash_availability(self, files: list["FileItem"]) -> dict[str, bool]:
        """Return a mapping of file path -> whether a CRC32 hash exists.

        The function queries the persistent hash cache in batch and returns a
        dictionary mapping each file's absolute path to a boolean.
        """
        if not files:
            return {}

        try:
            from oncutf.core.cache.persistent_hash_cache import get_persistent_hash_cache

            hash_cache = get_persistent_hash_cache()

            file_paths = [f.full_path for f in files if f.full_path]
            files_with_hash = hash_cache.get_files_with_hash_batch(file_paths, "CRC32")

            # Convert to boolean dict
            result = {}
            for file in files:
                if file.full_path:
                    result[file.full_path] = file.full_path in files_with_hash

            return result

        except Exception:
            logger.exception("[BatchQueryManager] Error getting hash availability")
            return {}

    def get_metadata_availability(self, files: list["FileItem"]) -> dict[str, bool]:
        """Return a mapping of file path -> whether structured metadata is
        available for the file.

        The implementation reads the global application metadata cache via the
        application context and performs a lightweight presence check.
        """
        if not files:
            return {}

        try:
            # Get metadata cache
            from oncutf.core.application_context import get_app_context

            context = get_app_context()
            if not context or not hasattr(context, "_metadata_cache"):
                return {}

            metadata_cache = context._metadata_cache
            if not metadata_cache:
                return {}

            result = {}
            for file in files:
                if file.full_path:
                    # Check if file has metadata
                    has_metadata = self._file_has_metadata(file.full_path, metadata_cache)
                    logger.debug(
                        "[DEBUG] [UnifiedRenameEngine] get_metadata_availability: %s has_metadata=%s",
                        file.full_path,
                        has_metadata,
                        extra={"dev_only": True},
                    )
                    result[file.full_path] = has_metadata

            logger.debug(
                "[DEBUG] [UnifiedRenameEngine] get_metadata_availability result: %s",
                result,
                extra={"dev_only": True},
            )
            return result

        except Exception:
            logger.exception("[BatchQueryManager] Error getting metadata availability")
            return {}

    def _file_has_metadata(self, file_path: str, metadata_cache) -> bool:
        """Return True if the given file path has non-internal metadata.

        The method expects the metadata cache to expose an internal
        `_memory_cache` mapping where entries contain a `.data` attribute.
        Only non-internal keys (not starting with '_' and not path/filename)
        are considered metadata fields.
        """
        try:
            if hasattr(metadata_cache, "_memory_cache"):
                entry = metadata_cache._memory_cache.get(file_path)
                if entry and hasattr(entry, "data") and entry.data:
                    # Check if there are any non-internal metadata fields
                    metadata_fields = {
                        k
                        for k in entry.data
                        if not k.startswith("_") and k not in {"path", "filename"}
                    }
                    return len(metadata_fields) > 0
            return False
        except Exception:
            logger.debug(
                "[BatchQueryManager] Error checking metadata for %s",
                file_path,
                exc_info=True,
            )
            return False


class SmartCacheManager:
    """Lightweight in-memory caches for preview, validation and execution.

    The caches use a small time-to-live (TTL) to avoid recomputing results
    during rapid UI interactions while keeping memory usage minimal.
    """

    def __init__(self) -> None:
        """Initialize the cache manager with empty caches and 100ms TTL."""
        self._preview_cache: dict[str, tuple[PreviewResult, float]] = {}
        self._validation_cache: dict[str, tuple[ValidationResult, float]] = {}
        self._execution_cache: dict[str, tuple[Any, float]] = {}
        self._cache_ttl = 0.1  # 100ms TTL

    def get_cached_preview(self, key: str) -> PreviewResult | None:
        """Return a cached :class:`PreviewResult` for `key` or ``None``.

        Entries older than the TTL are automatically invalidated.
        """
        if key in self._preview_cache:
            result, timestamp = self._preview_cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return result
            else:
                del self._preview_cache[key]
        return None

    def cache_preview(self, key: str, result: PreviewResult) -> None:
        """Store a preview result in the cache under `key`."""
        self._preview_cache[key] = (result, time.time())

    def get_cached_validation(self, key: str) -> ValidationResult | None:
        """Return a cached :class:`ValidationResult` for `key` or ``None``.

        Entries older than the TTL are automatically invalidated.
        """
        if key in self._validation_cache:
            result, timestamp = self._validation_cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return result
            else:
                del self._validation_cache[key]
        return None

    def cache_validation(self, key: str, result: ValidationResult) -> None:
        """Cache validation result."""
        self._validation_cache[key] = (result, time.time())

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._preview_cache.clear()
        self._validation_cache.clear()
        self._execution_cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "preview_cache_size": len(self._preview_cache),
            "validation_cache_size": len(self._validation_cache),
            "execution_cache_size": len(self._execution_cache),
            "cache_ttl": self._cache_ttl,
            "total_cached_items": len(self._preview_cache)
            + len(self._validation_cache)
            + len(self._execution_cache),
        }
