"""Module: metadata_cache_service.py

Author: Michael Economou
Date: 2025-12-20
Updated: 2026-01-01

Metadata cache service - handles all cache-related operations.
Extracted from unified_metadata_manager.py for better separation of concerns.

Responsibilities:
- Check if metadata/hash exists in cache
- Get metadata/hash from cache
- Direct cache access via file_status_helpers
"""

from __future__ import annotations

from typing import Any

from oncutf.models.file_item import FileItem
from oncutf.utils.filesystem.file_status_helpers import (
    get_hash_for_file,
    get_metadata_cache_entry,
    get_metadata_for_file,
    has_hash,
    has_metadata,
    is_metadata_extended,
    is_metadata_modified,
    set_metadata_for_file,
)
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataCacheService:
    """Service for metadata cache operations.

    Responsibilities:
    - Check if metadata/hash exists in cache
    - Get metadata/hash from cache
    - All operations delegate to file_status_helpers
    """

    def __init__(self, parent_window: Any = None) -> None:
        """Initialize cache service with parent window reference."""
        self.parent_window = parent_window

    def check_cached_metadata(self, file_item: FileItem) -> dict[str, Any] | None:
        """Check if metadata exists in cache without loading.

        Args:
            file_item: The file to check

        Returns:
            Metadata dict if cached, None if not available

        """
        try:
            return get_metadata_for_file(file_item.full_path)
        except Exception:
            logger.warning(
                "[MetadataCacheService] Error checking cache for %s",
                file_item.filename,
                exc_info=True,
            )
            return None

    def check_cached_hash(self, file_item: FileItem) -> str | None:
        """Check if hash exists in cache without loading.

        Args:
            file_item: The file to check

        Returns:
            Hash string if cached, None if not available

        """
        try:
            return get_hash_for_file(file_item.full_path)
        except Exception:
            logger.warning(
                "[MetadataCacheService] Error checking hash cache for %s",
                file_item.filename,
                exc_info=True,
            )
            return None

    def has_cached_metadata(self, file_path: str) -> bool:
        """Check if metadata exists in cache for a file path.

        Args:
            file_path: Path to check

        Returns:
            bool: True if metadata exists in cache

        """
        return has_metadata(file_path)

    def has_cached_hash(self, file_path: str) -> bool:
        """Check if hash exists in cache for a file path.

        Args:
            file_path: Path to check

        Returns:
            bool: True if hash exists in cache

        """
        return has_hash(file_path)

    def get_cache_entry(self, file_path: str) -> Any:
        """Get cache entry for a file path.

        Args:
            file_path: Path to check

        Returns:
            Cache entry or None

        """
        return get_metadata_cache_entry(file_path)

    def is_extended(self, file_path: str) -> bool:
        """Check if metadata is extended for a file path."""
        return is_metadata_extended(file_path)

    def is_modified(self, file_path: str) -> bool:
        """Check if metadata is modified for a file path."""
        return is_metadata_modified(file_path)

    def set_metadata(
        self,
        file_path: str,
        metadata: dict[str, Any],
        is_extended: bool = False,
        modified: bool = False,
    ) -> None:
        """Set metadata for a file path."""
        set_metadata_for_file(file_path, metadata, is_extended, modified)
