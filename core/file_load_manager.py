"""
file_load_manager.py

Author: Michael Economou
Date: 2025-05-01

Unified file loading manager with simplified policy:
- Non-recursive folder loading: wait_cursor only (fast, no progress bar)
- Recursive folder loading: FileLoadingDialog with progress bar
- Consistent behavior between drag-and-drop and import button
"""

import os
from typing import List, Set

from PyQt5.QtCore import Qt

from config import ALLOWED_EXTENSIONS
from core.drag_manager import force_cleanup_drag, is_dragging
from models.file_item import FileItem
from utils.cursor_helper import force_restore_cursor, wait_cursor
from utils.logger_factory import get_cached_logger
from utils.path_utils import find_file_by_path
from utils.timer_manager import get_timer_manager
from widgets.file_loading_dialog import FileLoadingDialog

logger = get_cached_logger(__name__)

class FileLoadManager:
    """
    Unified file loading manager with simplified policy:
    - Non-recursive: wait_cursor only (fast)
    - Recursive: progress dialog (for large operations)
    - Same behavior for drag and import
    """

    def __init__(self, parent_window=None):
        """Initialize FileLoadManager with parent window reference."""
        self.parent_window = parent_window
        self.allowed_extensions = set(ALLOWED_EXTENSIONS)
        self.timer_manager = get_timer_manager()
        # Flag to prevent metadata tree refresh conflicts during metadata operations
        self._metadata_operation_in_progress = False
        logger.debug("[FileLoadManager] Initialized with unified loading policy")

    def load_folder(self, folder_path: str, merge_mode: bool = False, recursive: bool = False) -> None:
        """
        Unified folder loading method for both drag and import operations.

        Policy:
        - Non-recursive: wait_cursor only (fast, synchronous)
        - Recursive: FileLoadingDialog with progress bar
        """
        logger.info(f"[FileLoadManager] load_folder: {folder_path} (merge={merge_mode}, recursive={recursive})", extra={"dev_only": True})

        if not os.path.isdir(folder_path):
            logger.error(f"Path is not a directory: {folder_path}")
            return

        # Store the recursive state for future reloads (if not merging)
        if not merge_mode and hasattr(self.parent_window, 'current_folder_is_recursive'):
            self.parent_window.current_folder_is_recursive = recursive
            logger.info(f"[FileLoadManager] Stored recursive state: {recursive}", extra={"dev_only": True})

        # CRITICAL: Force cleanup any active drag state immediately
        # This ensures ESC key works properly in FileLoadingDialog
        if is_dragging():
            logger.debug("[FileLoadManager] Active drag detected, forcing cleanup before loading")
            force_cleanup_drag()

        # Clear any existing cursors immediately
        force_restore_cursor()

        if recursive:
            # Recursive: Use progress dialog for potentially long operations
            self._load_folder_with_progress(folder_path, merge_mode)
        else:
            # Non-recursive: Simple wait cursor for fast operations
            self._load_folder_with_wait_cursor(folder_path, merge_mode)

    # Legacy method name for compatibility
    def handle_folder_drop(self, folder_path: str, merge_mode: bool = False, recursive: bool = False) -> None:
        """Legacy method - redirects to unified load_folder."""
        self.load_folder(folder_path, merge_mode, recursive)

    def load_files_from_paths(self, paths: List[str], clear: bool = True) -> None:
        """
        Load files from multiple paths (used by import button).
        Always uses progress dialog since it can handle multiple paths.
        """
        logger.info(f"[FileLoadManager] load_files_from_paths: {len(paths)} paths", extra={"dev_only": True})

        # Force cleanup any active drag state (import button shouldn't have drag, but safety first)
        if is_dragging():
            logger.debug("[FileLoadManager] Active drag detected during import, forcing cleanup")
            force_cleanup_drag()

        def on_files_loaded(file_paths: List[str]):
            logger.info(f"[FileLoadManager] Loaded {len(file_paths)} files from paths", extra={"dev_only": True})
            self._update_ui_with_files(file_paths, clear=clear)

        # Always use progress dialog for multi-path operations
        dialog = FileLoadingDialog(self.parent_window, on_files_loaded)
        dialog.load_files_with_options(paths, self.allowed_extensions, recursive=True)
        dialog.exec_()

    def load_single_item_from_drop(self, path: str, modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        Handle single item drop with modifier support.
        Uses unified load_folder method for consistent behavior.
        """
        logger.info(f"[FileLoadManager] load_single_item_from_drop: {path}", extra={"dev_only": True})

        # Parse modifiers
        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)
        recursive = ctrl
        merge_mode = shift

        logger.debug(f"[Drop] Modifiers: ctrl={ctrl}, shift={shift} → recursive={recursive}, merge={merge_mode}")

        if os.path.isdir(path):
            # Use unified folder loading (will handle drag cleanup internally)
            self.load_folder(path, merge_mode=merge_mode, recursive=recursive)
        else:
            # Handle single file - cleanup drag state first
            if is_dragging():
                logger.debug("[FileLoadManager] Active drag detected during single file drop, forcing cleanup")
                force_cleanup_drag()

            if self._is_allowed_extension(path):
                self._update_ui_with_files([path], clear=not merge_mode)

    def load_files_from_dropped_items(self, paths: list[str], modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        Handle multiple dropped items (table drop).
        Uses unified loading for consistent behavior.
        """
        if not paths:
            logger.info("[Drop] No files dropped in table.")
            return

        logger.info(f"[Drop] {len(paths)} file(s)/folder(s) dropped in table view")

        # Parse modifiers
        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)
        recursive = ctrl
        merge_mode = shift

        # Process all items with unified logic
        all_file_paths = []

        for path in paths:
            if os.path.isfile(path):
                if self._is_allowed_extension(path):
                    all_file_paths.append(path)
            elif os.path.isdir(path):
                # For table drops, collect files synchronously to avoid multiple dialogs
                folder_files = self._get_files_from_folder(path, recursive)
                all_file_paths.extend(folder_files)

        # Update UI with all collected files
        if all_file_paths:
            self._update_ui_with_files(all_file_paths, clear=not merge_mode)

    def load_metadata_from_dropped_files(self, paths: list[str], modifiers: Qt.KeyboardModifiers = Qt.NoModifier) -> None:
        """
        DEPRECATED: This method is no longer used.
        FileTableView now calls MetadataManager directly for better performance and simpler code.

        This method is kept for compatibility but should not be called in the new architecture.
        """
        logger.warning("[FileLoadManager] load_metadata_from_dropped_files is deprecated - FileTableView should call MetadataManager directly")

    def _load_folder_with_progress(self, folder_path: str, merge_mode: bool) -> None:
        """Load folder with progress dialog (for recursive operations)."""
        logger.debug(f"[FileLoadManager] Loading folder with progress: {folder_path}")

        def on_files_loaded(file_paths: List[str]):
            logger.info(f"[FileLoadManager] Progress loading completed: {len(file_paths)} files")
            self._update_ui_with_files(file_paths, clear=not merge_mode)

        # Show progress dialog
        dialog = FileLoadingDialog(self.parent_window, on_files_loaded)
        dialog.load_files_with_options([folder_path], self.allowed_extensions, recursive=True)
        dialog.exec_()

    def _load_folder_with_wait_cursor(self, folder_path: str, merge_mode: bool) -> None:
        """Load folder with wait cursor only (for non-recursive operations)."""
        logger.debug(f"[FileLoadManager] Loading folder with wait cursor: {folder_path}", extra={"dev_only": True})

        with wait_cursor():
            file_paths = self._get_files_from_folder(folder_path, recursive=False)
            self._update_ui_with_files(file_paths, clear=not merge_mode)

    def _count_files_in_folder(self, folder_path: str, recursive: bool = False) -> int:
        """
        Count total number of valid files in folder.
        Returns accurate count for progress bar decision.
        """
        count = 0
        if recursive:
            for root, _, filenames in os.walk(folder_path):
                count += sum(1 for f in filenames if self._is_allowed_extension(f))
        else:
            try:
                filenames = os.listdir(folder_path)
                count = sum(1 for f in filenames if self._is_allowed_extension(f))
            except OSError:
                pass
        return count

    def _get_files_from_folder(self, folder_path: str, recursive: bool = False) -> List[str]:
        """
        Get all valid files from folder.
        Returns list of file paths.
        """
        file_paths = []
        if recursive:
            for root, _, filenames in os.walk(folder_path):
                for filename in filenames:
                    if self._is_allowed_extension(filename):
                        file_paths.append(os.path.join(root, filename))
        else:
            try:
                for filename in os.listdir(folder_path):
                    if self._is_allowed_extension(filename):
                        full_path = os.path.join(folder_path, filename)
                        if os.path.isfile(full_path):
                            file_paths.append(full_path)
            except OSError:
                pass
        return file_paths

    def _is_allowed_extension(self, path: str) -> bool:
        """Check if file has allowed extension."""
        ext = os.path.splitext(path)[1].lower()
        if ext.startswith('.'):
            ext = ext[1:]
        return ext in self.allowed_extensions

    def _update_ui_with_files(self, file_paths: List[str], clear: bool = True) -> None:
        """
        Update UI with loaded files.
        Converts file paths to FileItem objects and updates the model.
        """
        if not file_paths:
            logger.info("[FileLoadManager] No files to update UI with")
            return

        logger.info(f"[FileLoadManager] Updating UI with {len(file_paths)} files (clear={clear})", extra={"dev_only": True})

        # Convert file paths to FileItem objects
        file_items = []
        for path in file_paths:
            try:
                file_item = FileItem.from_path(path)
                file_items.append(file_item)
            except Exception as e:
                logger.error(f"Error creating FileItem for {path}: {e}")

        if not file_items:
            logger.warning("[FileLoadManager] No valid FileItem objects created")
            return

        # Update the model
        self._update_ui_after_load(file_items, clear=clear)

    def _update_ui_after_load(self, items: List[FileItem], clear: bool = True) -> None:
        """
        Update UI after loading files.
        Handles model updates and UI refresh with duplicate detection in merge mode.
        """
        if not hasattr(self.parent_window, 'file_model'):
            logger.error("[FileLoadManager] Parent window has no file_model attribute")
            return

        try:
            # Set current folder path from first file's directory
            if items and clear:
                first_file_path = items[0].full_path
                if first_file_path:
                    folder_path = os.path.dirname(first_file_path)
                    self.parent_window.current_folder_path = folder_path
                    logger.info(f"[FileLoadManager] Set current_folder_path to: {folder_path}", extra={"dev_only": True})

                    # Check if this was a recursive load by looking for files in subdirectories
                    has_subdirectory_files = any(
                        os.path.dirname(item.full_path) != folder_path for item in items
                    )
                    self.parent_window.current_folder_is_recursive = has_subdirectory_files
                    logger.info(f"[FileLoadManager] Set recursive mode to: {has_subdirectory_files}", extra={"dev_only": True})

            if clear:
                # Replace existing files
                self.parent_window.file_model.set_files(items)
                logger.info(f"[FileLoadManager] Replaced files with {len(items)} new items", extra={"dev_only": True})
            else:
                # Add to existing files with duplicate detection
                existing_files = self.parent_window.file_model.files

                # Create a set of existing file paths for fast lookup
                existing_paths = {file_item.full_path for file_item in existing_files}

                # Filter out duplicates from new items
                new_items = []
                duplicate_count = 0

                for item in items:
                    if item.full_path not in existing_paths:
                        new_items.append(item)
                        existing_paths.add(item.full_path)  # Add to set to avoid duplicates within the new items too
                    else:
                        duplicate_count += 1

                # Combine existing files with new non-duplicate items
                combined_files = existing_files + new_items
                self.parent_window.file_model.set_files(combined_files)

                # Log the results
                if duplicate_count > 0:
                    logger.info(f"[FileLoadManager] Added {len(new_items)} new items, skipped {duplicate_count} duplicates (total: {len(combined_files)})")
                else:
                    logger.info(f"[FileLoadManager] Added {len(new_items)} new items to existing {len(existing_files)} files (total: {len(combined_files)})")

            # CRITICAL: Update all UI elements after file loading
            self._refresh_ui_after_file_load()

        except Exception as e:
            logger.error(f"[FileLoadManager] Error updating UI: {e}")

    def _refresh_ui_after_file_load(self) -> None:
        """
        Refresh all UI elements after files are loaded.
        This ensures placeholders are hidden, labels are updated, and selection works.
        """
        try:
            # Update files label (shows count)
            if hasattr(self.parent_window, 'update_files_label'):
                self.parent_window.update_files_label()
                logger.debug("[FileLoadManager] Updated files label", extra={"dev_only": True})

            total_files = len(self.parent_window.file_model.files)

            # Hide file table placeholder when files are loaded
            if hasattr(self.parent_window, 'file_table_view'):
                if total_files > 0:
                    # Hide file table placeholder when files are loaded
                    self.parent_window.file_table_view.set_placeholder_visible(False)
                    logger.debug("[FileLoadManager] Hidden file table placeholder", extra={"dev_only": True})
                else:
                    # Show file table placeholder when no files
                    self.parent_window.file_table_view.set_placeholder_visible(True)
                    logger.debug("[FileLoadManager] Shown file table placeholder", extra={"dev_only": True})

            # Hide placeholders in preview tables (if files are loaded)
            if hasattr(self.parent_window, 'preview_tables_view'):
                if total_files > 0:
                    # Hide placeholders when files are loaded
                    self.parent_window.preview_tables_view._set_placeholders_visible(False)
                    logger.debug("[FileLoadManager] Hidden preview table placeholders", extra={"dev_only": True})
                else:
                    # Show placeholders when no files
                    self.parent_window.preview_tables_view._set_placeholders_visible(True)
                    logger.debug("[FileLoadManager] Shown preview table placeholders", extra={"dev_only": True})

            # Update preview tables
            if hasattr(self.parent_window, 'request_preview_update'):
                self.parent_window.request_preview_update()
                logger.debug("[FileLoadManager] Requested preview update", extra={"dev_only": True})

            # Ensure file table selection works properly
            if hasattr(self.parent_window, 'file_table_view'):
                # Restore previous sorting state for consistency
                if (hasattr(self.parent_window, 'current_sort_column') and
                    hasattr(self.parent_window, 'current_sort_order')):
                    sort_column = self.parent_window.current_sort_column
                    sort_order = self.parent_window.current_sort_order
                    logger.debug(f"[FileLoadManager] Restoring sort state: column={sort_column}, order={sort_order}", extra={"dev_only": True})

                    # Apply sorting through the model and header
                    self.parent_window.file_model.sort(sort_column, sort_order)
                    header = self.parent_window.file_table_view.horizontalHeader()
                    header.setSortIndicator(sort_column, sort_order)

                # Force refresh of the table view
                self.parent_window.file_table_view.viewport().update()

                # Reset selection state to ensure clicks work
                if hasattr(self.parent_window.file_table_view, '_sync_selection_safely'):
                    self.parent_window.file_table_view._sync_selection_safely()

                logger.debug("[FileLoadManager] Refreshed file table view", extra={"dev_only": True})

            # Update metadata tree (clear it for new files)
            if hasattr(self.parent_window, 'metadata_tree_view'):
                # Only refresh metadata tree if we're not in the middle of a metadata operation
                # This prevents conflicts with metadata loading operations (drag & drop, context menu, etc.)
                if not self._metadata_operation_in_progress:
                    if hasattr(self.parent_window.metadata_tree_view, 'refresh_metadata_from_selection'):
                        self.parent_window.metadata_tree_view.refresh_metadata_from_selection()
                        logger.debug("[FileLoadManager] Refreshed metadata tree", extra={"dev_only": True})
                else:
                    logger.debug("[FileLoadManager] Skipped metadata tree refresh (metadata operation in progress)", extra={"dev_only": True})

            logger.info("[FileLoadManager] UI refresh completed successfully", extra={"dev_only": True})

        except Exception as e:
            logger.error(f"[FileLoadManager] Error refreshing UI: {e}")

    def prepare_folder_load(self, folder_path: str, *, clear: bool = True) -> list[str]:
        """
        Prepare folder for loading by getting file list.
        Returns list of file paths without loading them into UI.
        """
        logger.info(f"[FileLoadManager] prepare_folder_load: {folder_path}")
        return self._get_files_from_folder(folder_path, recursive=False)

    def reload_current_folder(self) -> None:
        """Reload the current folder if available."""
        logger.info("[FileLoadManager] reload_current_folder called")
        # Implementation depends on how current folder is tracked

    def set_allowed_extensions(self, extensions: Set[str]) -> None:
        """Update the set of allowed file extensions."""
        self.allowed_extensions = extensions
        logger.info(f"[FileLoadManager] Updated allowed extensions: {extensions}")

    def clear_metadata_operation_flag(self) -> None:
        """Clear the metadata operation flag. Called after metadata operations complete."""
        self._metadata_operation_in_progress = False
        logger.debug("[FileLoadManager] Cleared metadata operation flag")
