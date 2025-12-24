"""Module: metadata_cache_service.py

Author: Michael Economou (refactored)
Date: 2025-12-20
Updated: 2025-12-21

Metadata cache service - handles all cache-related operations.
Extracted from unified_metadata_manager.py for better separation of concerns.

Responsibilities:
- Check if metadata/hash exists in cache
- Get metadata/hash from cache
- Initialize and manage MetadataCacheHelper
"""

from __future__ import annotations

from typing import Any

from oncutf.models.file_item import FileItem
from oncutf.utils.file_status_helpers import (
    get_hash_for_file,
    get_metadata_for_file,
    has_hash,
    has_metadata,
)
from oncutf.utils.logger_factory import get_cached_logger
from oncutf.utils.metadata_cache_helper import MetadataCacheHelper

logger = get_cached_logger(__name__)


class MetadataCacheService:
    """Service for metadata cache operations.

    Responsibilities:
    - Check if metadata/hash exists in cache
    - Get metadata/hash from cache
    - Initialize cache helper
    """

    def __init__(self, parent_window: Any = None) -> None:
        """Initialize cache service with parent window reference."""
        self.parent_window = parent_window
        self._cache_helper: MetadataCacheHelper | None = None

    def initialize_cache_helper(self) -> None:
        """Initialize the cache helper if parent window is available."""
        if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
            self._cache_helper = MetadataCacheHelper(
                self.parent_window.metadata_cache, self.parent_window
            )
            logger.debug(
                "[MetadataCacheService] Cache helper initialized", extra={"dev_only": True}
            )

    def get_cache_helper(self) -> MetadataCacheHelper | None:
        """Get the MetadataCacheHelper instance, initializing if needed."""
        if self._cache_helper is None:
            self.initialize_cache_helper()
        return self._cache_helper

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
