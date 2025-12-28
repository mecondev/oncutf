"""MetadataController — Orchestration layer for metadata operations.

Author: Michael Economou
Date: 2025-12-16

This module provides the controller for metadata loading, reloading,
configuration, and export operations. It coordinates between the UI layer
(MainWindow) and domain services (MetadataManager, ExifTool wrappers).

Architecture:
    - UI (MainWindow) → Controller → Services (Managers)
    - Controller is UI-agnostic and testable without Qt/GUI
    - All business logic stays in services; controller only orchestrates
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oncutf.core.application_context import ApplicationContext
    from oncutf.core.structured_metadata_manager import StructuredMetadataManager
    from oncutf.core.unified_metadata_manager import UnifiedMetadataManager
    from oncutf.models.file_item import FileItem

logger = logging.getLogger(__name__)


class MetadataController:
    """Controller for metadata operations.

    Responsibilities:
        - Coordinate metadata loading for selected files
        - Handle metadata reload requests
        - Configure metadata loading options (recursive tags, etc.)
        - Export metadata to various formats
        - Provide state queries (loading status, metadata availability)

    Dependencies:
        - UnifiedMetadataManager: Core metadata loading service
        - StructuredMetadataManager: Structured metadata access
        - ApplicationContext: Access to file store and settings
    """

    def __init__(
        self,
        unified_metadata_manager: UnifiedMetadataManager,
        structured_metadata_manager: StructuredMetadataManager,
        app_context: ApplicationContext,
    ) -> None:
        """Initialize MetadataController.

        Args:
            unified_metadata_manager: Manager for metadata loading operations
            structured_metadata_manager: Manager for structured metadata access
            app_context: Application context for file store and settings

        """
        self._unified_metadata_mgr = unified_metadata_manager
        self._structured_metadata_mgr = structured_metadata_manager
        self._app_context = app_context

        logger.info(
            "[MetadataController] Initialized with managers: UnifiedMetadata=%s, StructuredMetadata=%s",
            unified_metadata_manager.__class__.__name__,
            structured_metadata_manager.__class__.__name__,
        )

    # -------------------------------------------------------------------------
    # Metadata Loading
    # -------------------------------------------------------------------------

    def load_metadata(
        self,
        file_items: list[FileItem],
        use_extended: bool = False,
        source: str = "controller",
    ) -> dict[str, Any]:
        """Load metadata for given file items.

        This method orchestrates metadata loading by:
        1. Checking if files are provided
        2. Delegating to UnifiedMetadataManager for actual loading
        3. Returning result summary

        Args:
            file_items: List of FileItem objects to load metadata for
            use_extended: If True, load extended (all tags) metadata
            source: Source identifier for logging (e.g., "shortcut", "drag_drop")

        Returns:
            dict: {
                'success': bool,
                'loaded_count': int,
                'skipped_count': int,
                'errors': List[str]
            }

        """
        if not file_items:
            logger.debug("[MetadataController] No items provided for metadata loading")
            return {
                "success": False,
                "loaded_count": 0,
                "skipped_count": 0,
                "errors": ["No files provided"],
            }

        logger.info(
            "[MetadataController] Loading %s metadata for %d items (source=%s)",
            "extended" if use_extended else "fast",
            len(file_items),
            source,
        )

        try:
            # Delegate to UnifiedMetadataManager
            # Note: UnifiedMetadataManager.load_metadata_for_items() returns None
            # and handles all UI updates internally (progress dialogs, status bar, etc.)
            self._unified_metadata_mgr.load_metadata_for_items(
                file_items, use_extended=use_extended, source=source
            )

            # Since load_metadata_for_items() doesn't return status, we assume success
            # Actual errors are handled internally by the manager
            return {
                "success": True,
                "loaded_count": len(file_items),
                "skipped_count": 0,
                "errors": [],
            }

        except Exception as e:
            error_msg = f"Failed to load metadata: {e}"
            logger.exception("[MetadataController] %s", error_msg)
            return {
                "success": False,
                "loaded_count": 0,
                "skipped_count": 0,
                "errors": [error_msg],
            }

    def reload_metadata(
        self,
        file_items: list[FileItem] | None = None,
        use_extended: bool = False,
    ) -> dict[str, Any]:
        """Reload metadata for given files (or all if None).

        This is essentially the same as load_metadata but with force_reload semantics.
        The UnifiedMetadataManager will check cache and reload as needed.

        Args:
            file_items: Optional list of files to reload; if None, reload all loaded files
            use_extended: If True, reload with extended metadata

        Returns:
            dict: Result with success status and counts

        """
        if file_items is None:
            # Get all files from file store
            file_items = self._app_context.file_store.get_loaded_files()

        logger.info(
            "[MetadataController] reload_metadata for %d items (extended=%s)",
            len(file_items) if file_items else 0,
            use_extended,
        )

        # Reload is just load with force semantics
        return self.load_metadata(file_items, use_extended=use_extended, source="reload")

    # -------------------------------------------------------------------------
    # Metadata Configuration
    # -------------------------------------------------------------------------

    def determine_metadata_mode(self, modifier_state=None) -> tuple[bool, bool]:
        """Determine metadata mode based on keyboard modifiers.

        Returns (load_metadata, use_extended) based on modifier state:
        - Shift only: (True, False) - Load fast metadata
        - Ctrl+Shift: (True, True) - Load extended metadata
        - Otherwise: (False, False) - No metadata loading

        Args:
            modifier_state: Qt.KeyboardModifiers to use, or None for current state

        Returns:
            tuple: (load_metadata: bool, use_extended: bool)

        """
        result = self._unified_metadata_mgr.determine_metadata_mode(modifier_state)
        logger.debug(
            "[MetadataController] determine_metadata_mode: load=%s, extended=%s",
            result[0],
            result[1],
        )
        return result

    def should_use_extended_metadata(self, modifier_state=None) -> bool:
        """Check if extended metadata should be used (Ctrl+Shift both held).

        This is used in contexts where metadata WILL be loaded,
        and we only decide if it's fast or extended.

        Args:
            modifier_state: Qt.KeyboardModifiers to use, or None for current state

        Returns:
            bool: True if Ctrl+Shift are both held

        """
        result = self._unified_metadata_mgr.should_use_extended_metadata(modifier_state)
        logger.debug(
            "[MetadataController] should_use_extended_metadata: %s",
            result,
        )
        return result

    def restore_metadata_from_cache(self) -> dict[str, Any]:
        """Restore metadata from cache for all files in table.

        This delegates to TableManager which restores metadata from
        the persistent cache and updates the table display.

        Returns:
            dict: Result with success status

        """
        logger.info("[MetadataController] Restoring metadata from cache")

        try:
            # Get TableManager from ApplicationContext manager registry
            table_manager = self._app_context.get_manager("table")
            table_manager.restore_fileitem_metadata_from_cache()

            return {"success": True, "errors": []}

        except Exception as e:
            error_msg = f"Failed to restore metadata from cache: {e}"
            logger.exception("[MetadataController] %s", error_msg)
            return {"success": False, "errors": [error_msg]}

    # -------------------------------------------------------------------------
    # Metadata Export
    # -------------------------------------------------------------------------

    def export_metadata(
        self,
        file_items: list[FileItem],
        export_format: str,
        output_path: str,
    ) -> dict[str, Any]:
        """Export metadata to file.

        Args:
            file_items: List of files to export metadata from
            export_format: Format (csv, json, txt)
            output_path: Path to output file

        Returns:
            dict: {
                'success': bool,
                'exported_count': int,
                'output_path': str,
                'errors': List[str]
            }

        """
        logger.info(
            "[MetadataController] export_metadata: %d items to %s (%s)",
            len(file_items),
            output_path,
            export_format,
        )

        try:
            # Use MetadataExporter class
            from oncutf.utils.metadata.exporter import MetadataExporter

            exporter = MetadataExporter()
            success = exporter.export_files(
                files=file_items,
                output_dir=str(Path(output_path).parent),
                format_type=export_format,
            )

            result = {
                "success": success,
                "exported_count": len(file_items) if success else 0,
                "output_path": output_path,
                "errors": [] if success else ["Export failed"],
            }

            if result.get("success"):
                logger.info(
                    "[MetadataController] Successfully exported %d items to %s",
                    result.get("exported_count", 0),
                    output_path,
                )
            else:
                logger.warning(
                    "[MetadataController] Export failed: %s",
                    result.get("errors", []),
                )

            return result

        except Exception as e:
            error_msg = f"Failed to export metadata: {e}"
            logger.exception("[MetadataController] %s", error_msg)
            return {
                "success": False,
                "exported_count": 0,
                "output_path": output_path,
                "errors": [error_msg],
            }

    # -------------------------------------------------------------------------
    # State Queries
    # -------------------------------------------------------------------------

    def is_loading(self) -> bool:
        """Check if metadata loading is in progress.

        Returns:
            bool: True if loading

        """
        return self._unified_metadata_mgr.is_loading()

    def get_loaded_metadata_count(self) -> int:
        """Get count of files with loaded metadata.

        Returns:
            int: Number of files with metadata

        """
        count = 0
        items = self._app_context.file_store.get_loaded_files()

        for item in items:
            if self.has_metadata(item):
                count += 1

        return count

    def has_metadata(self, file_item: FileItem) -> bool:
        """Check if file has loaded metadata.

        Args:
            file_item: File to check

        Returns:
            bool: True if metadata is loaded

        """
        # Check if file has metadata in cache
        # Try to get metadata manager which has the cache
        try:
            from oncutf.utils.filesystem.path_normalizer import normalize_path

            metadata_manager = self._app_context.get_manager("metadata")
            norm_path = normalize_path(file_item.full_path)

            if not hasattr(metadata_manager, "metadata_cache"):
                return False

            cache_entry = metadata_manager.metadata_cache.get_entry(norm_path)

            return (
                cache_entry is not None
                and hasattr(cache_entry, "data")
                and cache_entry.data is not None
            )
        except (KeyError, AttributeError):
            # Manager not found or doesn't have metadata_cache
            return False

    def get_common_metadata_fields(self) -> list[str]:
        """Get list of common metadata fields across selected files.

        Returns:
            list: Common field names

        """
        try:
            # Get selected files from TableManager via manager registry
            table_manager = self._app_context.get_manager("table")
            selected_files = table_manager.get_selected_files()

            if not selected_files:
                return []

            # Common fields feature not currently supported
            logger.debug(
                "[MetadataController] get_common_fields not supported for %d files",
                len(selected_files),
            )

            return []

        except Exception as e:
            logger.exception(
                "[MetadataController] Failed to get common fields: %s",
                str(e),
            )
            return []
