"""Handler for metadata tree cache management.

This module handles cache-related operations for the metadata tree view,
including direct loader management.

Author: Michael Economou
Date: 2025-12-24
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_tree.view import MetadataTreeView

logger = get_cached_logger(__name__)


class MetadataTreeCacheHandler:
    """Handles cache management for metadata tree view."""

    def __init__(self, view: MetadataTreeView):
        """Initialize the cache handler.

        Args:
            view: The metadata tree view instance

        """
        self._view = view

    def initialize_direct_loader(self) -> None:
        """Initialize the direct metadata loader."""
        try:
            from oncutf.core.metadata.metadata_service import get_metadata_service

            metadata_service = get_metadata_service()
            self._view._direct_loader = metadata_service.unified_manager
            logger.debug(
                "[MetadataTreeView] UnifiedMetadataManager initialized via MetadataService",
                extra={"dev_only": True},
            )
        except Exception as e:
            logger.exception(
                "[MetadataTreeView] Failed to initialize UnifiedMetadataManager"
            )
            self._view._direct_loader = None

    def get_direct_loader(self):
        """Get the UnifiedMetadataManager instance, initializing if needed."""
        if self._view._direct_loader is None:
            self.initialize_direct_loader()
        return self._view._direct_loader
