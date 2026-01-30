"""Module: file_load_ui_service.py.

Author: Michael Economou
Date: 2026-01-03

UI refresh service for file loading operations.

This service handles all UI updates after files are loaded:
- Model updates (file_model.set_files)
- FileStore synchronization
- Placeholder visibility management
- Label updates
- Preview table refresh
- Metadata tree coordination
- Selection state synchronization
"""

import os
from typing import Any

from oncutf.models.file_item import FileItem
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class FileLoadUIService:
    """Service for coordinating UI updates after file loading.

    Extracted from FileLoadManager to separate I/O from UI concerns.
    This service knows about UI widgets and coordinates their updates.
    """

    def __init__(self, parent_window: Any = None) -> None:
        """Initialize with parent window reference for UI access."""
        self.parent_window = parent_window
        logger.debug("[FileLoadUIService] Initialized")

    def update_model_and_ui(self, items: list[FileItem], clear: bool = True) -> None:
        """Update file model and all UI elements after loading files.

        This is the main entry point for updating both model and UI.
        Handles:
        - Setting current folder path in context
        - Updating file_model with new items
        - Syncing FileStore
        - Choosing streaming vs immediate loading
        - Refreshing all UI widgets

        Args:
            items: List of FileItem objects to load
            clear: Whether to clear existing files (True) or merge (False)

        """
        if not hasattr(self.parent_window, "file_model"):
            logger.error("[FileLoadUIService] Parent window has no file_model attribute")
            return

        try:
            # Set current folder path from first file's directory
            if items and clear:
                first_file_path = items[0].full_path
                if first_file_path:
                    folder_path = os.path.dirname(first_file_path)

                    # Check if this was a recursive load by looking for files in subdirectories
                    has_subdirectory_files = any(
                        os.path.dirname(item.full_path) != folder_path for item in items
                    )

                    # Set folder path and recursive mode in QtAppContext (centralized state)
                    self.parent_window.context.set_current_folder(
                        folder_path, has_subdirectory_files
                    )
                    logger.info(
                        "[FileLoadUIService] Set current_folder_path to: %s",
                        folder_path,
                        extra={"dev_only": True},
                    )
                    logger.info(
                        "[FileLoadUIService] Recursive mode: %s",
                        has_subdirectory_files,
                        extra={"dev_only": True},
                    )

            # Use streaming loading for large file sets (> 200 files)
            if len(items) > 200:
                # Delegate to streaming loader (will handle model + UI updates)
                from oncutf.core.file.streaming_loader import StreamingFileLoader

                streaming_loader = StreamingFileLoader(self.parent_window, self)
                streaming_loader.load_files_streaming(items, clear=clear)
            else:
                # Small file sets: load immediately
                self._load_files_immediate(items, clear=clear)

        except Exception as e:
            logger.error("[FileLoadUIService] Error updating model and UI: %s", e)

    def _load_files_immediate(self, items: list[FileItem], clear: bool = True) -> None:
        """Load files immediately for small file sets.

        Updates the model and FileStore, then refreshes UI.

        Args:
            items: List of FileItem objects
            clear: Whether to replace (True) or merge (False)

        """
        if clear:
            # Replace existing files
            self.parent_window.file_model.set_files(items)
            self.parent_window.context.file_store.set_loaded_files(items)
            logger.info(
                "[FileLoadUIService] Replaced files with %d new items",
                len(items),
                extra={"dev_only": True},
            )
        else:
            # Merge mode: add to existing files with duplicate detection
            existing_files = self.parent_window.file_model.files

            # Create a set of existing file paths for fast lookup
            existing_paths = {file_item.full_path for file_item in existing_files}

            # Filter out duplicates from new items
            new_items = []
            duplicate_count = 0

            for item in items:
                if item.full_path not in existing_paths:
                    new_items.append(item)
                    existing_paths.add(item.full_path)
                else:
                    duplicate_count += 1

            # Combine existing files with new non-duplicate items
            combined_files = existing_files + new_items
            self.parent_window.file_model.set_files(combined_files)
            self.parent_window.context.file_store.set_loaded_files(combined_files)

            # Log the results
            if duplicate_count > 0:
                logger.info(
                    "[FileLoadUIService] Added %d new items, skipped %d duplicates",
                    len(new_items),
                    duplicate_count,
                )

        # Refresh UI to ensure placeholders, header and labels are updated
        self.refresh_ui_after_load()

        # Handle metadata search field special case (no files loaded)
        total_files = len(self.parent_window.file_model.files)
        if total_files == 0:
            self.update_metadata_search_state(False)

    def refresh_ui_after_load(self, total_files: int | None = None) -> None:
        """Refresh all UI elements after files are loaded.

        This ensures placeholders are hidden, labels are updated, and selection works.

        Args:
            total_files: Number of files loaded (optional, will query model if not provided)

        """
        try:
            if total_files is None:
                if hasattr(self.parent_window, "file_model"):
                    total_files = len(self.parent_window.file_model.files)
                else:
                    total_files = 0

            # Update files label (shows count)
            if hasattr(self.parent_window, "update_files_label"):
                self.parent_window.update_files_label()
                logger.debug("[FileLoadUIService] Updated files label", extra={"dev_only": True})

            # Update file table placeholder visibility
            self._update_file_table_placeholder(total_files)

            # Update header enabled state
            self._update_header_state(total_files)

            # Update preview tables
            self._update_preview_tables(total_files)

            # Refresh file table view
            self._refresh_file_table()

            # Update metadata tree (if not blocked)
            self._update_metadata_tree()

            logger.info(
                "[FileLoadUIService] UI refresh completed successfully",
                extra={"dev_only": True},
            )

        except Exception as e:
            logger.error("[FileLoadUIService] Error refreshing UI: %s", e)

    def _update_file_table_placeholder(self, total_files: int) -> None:
        """Update file table placeholder visibility."""
        if hasattr(self.parent_window, "file_table_view"):
            visible = total_files == 0
            self.parent_window.file_table_view.set_placeholder_visible(visible)
            logger.debug(
                "[FileLoadUIService] %s file table placeholder",
                "Shown" if visible else "Hidden",
                extra={"dev_only": True},
            )

    def _update_header_state(self, total_files: int) -> None:
        """Update header enabled state based on file count."""
        if hasattr(self.parent_window, "header") and self.parent_window.header is not None:
            try:
                enabled = total_files > 0
                self.parent_window.header.setEnabled(enabled)
                logger.debug(
                    "[FileLoadUIService] Header enabled state set to %s",
                    enabled,
                    extra={"dev_only": True},
                )
            except Exception:
                logger.debug(
                    "[FileLoadUIService] Failed to set header enabled state",
                    extra={"dev_only": True},
                )

    def _update_preview_tables(self, total_files: int) -> None:
        """Update preview table placeholders and data."""
        if hasattr(self.parent_window, "preview_tables_view"):
            visible = total_files == 0
            self.parent_window.preview_tables_view._set_placeholders_visible(visible)
            logger.debug(
                "[FileLoadUIService] %s preview table placeholders",
                "Shown" if visible else "Hidden",
                extra={"dev_only": True},
            )

        # Request preview update
        if hasattr(self.parent_window, "request_preview_update"):
            self.parent_window.request_preview_update()
            logger.debug("[FileLoadUIService] Requested preview update", extra={"dev_only": True})

    def _refresh_file_table(self) -> None:
        """Refresh file table view and restore sorting."""
        if not hasattr(self.parent_window, "file_table_view"):
            return

        # Restore previous sorting state for consistency
        if hasattr(self.parent_window, "current_sort_column") and hasattr(
            self.parent_window, "current_sort_order"
        ):
            sort_column = self.parent_window.current_sort_column
            sort_order = self.parent_window.current_sort_order
            logger.debug(
                "[FileLoadUIService] Restoring sort state: column=%s, order=%s",
                sort_column,
                sort_order,
                extra={"dev_only": True},
            )

            # Apply sorting through the model and header
            self.parent_window.file_model.sort(sort_column, sort_order)
            header = self.parent_window.file_table_view.horizontalHeader()
            header.setSortIndicator(sort_column, sort_order)

        # Force refresh of the table view
        self.parent_window.file_table_view.viewport().update()

        # Refresh icons to show any cached metadata/hash status
        if hasattr(self.parent_window.file_model, "refresh_icons"):
            self.parent_window.file_model.refresh_icons()
            logger.debug(
                "[FileLoadUIService] Refreshed file table icons",
                extra={"dev_only": True},
            )

        # Reset selection state to ensure clicks work
        if hasattr(self.parent_window.file_table_view, "_selection_behavior"):
            self.parent_window.file_table_view._selection_behavior.sync_selection_safely()
            logger.debug(
                "[FileLoadUIService] Refreshed file table view",
                extra={"dev_only": True},
            )

    def _update_metadata_tree(self) -> None:
        """Update metadata tree if not blocked by operation."""
        if not hasattr(self.parent_window, "metadata_tree_view"):
            return

        # Check if metadata operation is in progress (avoid conflicts)
        # This is coordinated by FileLoadManager's flag
        parent_manager = getattr(self.parent_window, "file_load_manager", None)
        if parent_manager and getattr(parent_manager, "_metadata_operation_in_progress", False):
            logger.debug(
                "[FileLoadUIService] Skipped metadata tree refresh (operation in progress)",
                extra={"dev_only": True},
            )
            return

        # Refresh metadata from current selection
        if hasattr(self.parent_window.metadata_tree_view, "refresh_metadata_from_selection"):
            self.parent_window.metadata_tree_view.refresh_metadata_from_selection()
            logger.debug("[FileLoadUIService] Refreshed metadata tree", extra={"dev_only": True})

    def update_metadata_search_state(self, enabled: bool) -> None:
        """Update metadata search field enabled state.

        Args:
            enabled: Whether to enable the search field

        """
        if hasattr(self.parent_window, "metadata_tree_view"):
            if hasattr(self.parent_window.metadata_tree_view, "_update_search_field_state"):
                self.parent_window.metadata_tree_view._update_search_field_state(enabled)
                logger.debug(
                    "[FileLoadUIService] %s metadata search field",
                    "Enabled" if enabled else "Disabled",
                    extra={"dev_only": True},
                )
