"""Handler for metadata tree cache management.

This module handles cache-related operations for the metadata tree view,
including cache helper initialization and direct loader management.

Author: Michael Economou
Date: 2025-12-24
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.metadata.cache_helper import MetadataCacheHelper

if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_tree.view import MetadataTreeView

# Unified metadata manager integration
try:
    from oncutf.core.metadata import UnifiedMetadataManager
except ImportError:
    UnifiedMetadataManager = None

logger = get_cached_logger(__name__)


class MetadataTreeCacheHandler:
    """Handles cache management for metadata tree view."""

    def __init__(self, view: MetadataTreeView):
        """Initialize the cache handler.

        Args:
            view: The metadata tree view instance

        """
        self._view = view

    def initialize_cache_helper(self) -> None:
        """Initialize the metadata cache helper."""
        try:
            # Use the persistent cache instance from parent window if available
            parent_window = self._view._get_parent_with_file_table()
            cache_instance = None
            if parent_window and hasattr(parent_window, "metadata_cache"):
                cache_instance = parent_window.metadata_cache

            self._view._cache_helper = MetadataCacheHelper(cache_instance)
            logger.debug(
                "[MetadataTreeView] MetadataCacheHelper initialized (with persistent cache)",
                extra={"dev_only": True},
            )
        except Exception as e:
            logger.exception("[MetadataTreeView] Failed to initialize MetadataCacheHelper: %s", e)
            self._view._cache_helper = None

    def get_cache_helper(self) -> MetadataCacheHelper | None:
        """Get the MetadataCacheHelper instance, initializing if needed."""
        # Always check if we need to initialize or re-initialize (if cache backend is missing)
        if self._view._cache_helper is None or (
            self._view._cache_helper and self._view._cache_helper.metadata_cache is None
        ):
            self.initialize_cache_helper()
        return self._view._cache_helper

    def initialize_direct_loader(self) -> None:
        """Initialize the direct metadata loader."""
        try:
            if UnifiedMetadataManager is not None:
                self._view._direct_loader = UnifiedMetadataManager()
                logger.debug(
                    "[MetadataTreeView] UnifiedMetadataManager initialized",
                    extra={"dev_only": True},
                )
            else:
                logger.debug(
                    "[MetadataTreeView] UnifiedMetadataManager not available",
                    extra={"dev_only": True},
                )
                self._view._direct_loader = None
        except Exception as e:
            logger.exception(
                "[MetadataTreeView] Failed to initialize UnifiedMetadataManager: %s", e
            )
            self._view._direct_loader = None

    def get_direct_loader(self):
        """Get the UnifiedMetadataManager instance, initializing if needed."""
        if self._view._direct_loader is None:
            self.initialize_direct_loader()
        return self._view._direct_loader
