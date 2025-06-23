"""
metadata_manager.py

Author: Michael Economou
Date: 2025-05-01

Centralized metadata management operations extracted from MainWindow.
Handles metadata loading, progress tracking, thread management, and UI coordination.
"""

from typing import List, Optional

from PyQt5.QtCore import Qt

from core.qt_imports import QApplication
from models.file_item import FileItem
from utils.logger_factory import get_cached_logger
from utils.path_utils import find_file_by_path, paths_equal

logger = get_cached_logger(__name__)


class MetadataManager:
    """
    Centralized metadata management operations.

    Handles:
    - Thread-based metadata scanning with progress tracking
    - Modifier-based metadata mode decisions
    - Dialog management for progress indication
    - Error handling and cleanup
    - Integration with existing metadata cache and loader
    """

    def __init__(self, parent_window=None):
        """Initialize MetadataManager with parent window reference."""
        self.parent_window = parent_window

        # State tracking
        self.force_extended_metadata = False

        # Initialize metadata cache and exiftool wrapper
        self._metadata_cache = {}  # Cache for metadata results

        # Initialize ExifTool wrapper for single file operations
        from utils.exiftool_wrapper import ExifToolWrapper
        self._exiftool_wrapper = ExifToolWrapper()

    def determine_loading_mode(self, file_count: int, use_extended: bool = False) -> str:
        """
        Determine the appropriate loading mode based on file count.

        Args:
            file_count: Number of files to load metadata for
            use_extended: Whether extended metadata is requested

        Returns:
            str: Loading mode ("single_file_wait_cursor", "multiple_files_dialog", etc.)
        """
        if file_count == 1:
            return "single_file_wait_cursor"
        else:
            # For any multiple files, use dialog
            return "multiple_files_dialog"

    def determine_metadata_mode(self, modifier_state=None) -> tuple[bool, bool]:
        """
        Determines whether to skip metadata scan or use extended mode based on modifier keys.

        Args:
            modifier_state: Qt.KeyboardModifiers to use, or None for current state

        Returns:
            tuple: (skip_metadata, use_extended)

            - skip_metadata = True ➜ No metadata scan (no modifiers)
            - skip_metadata = False & use_extended = False ➜ Fast scan (Ctrl)
            - skip_metadata = False & use_extended = True ➜ Extended scan (Ctrl+Shift)
        """
        from core.qt_imports import Qt

        modifiers = modifier_state
        if modifiers is None:
            if self.parent_window and hasattr(self.parent_window, 'modifier_state'):
                modifiers = self.parent_window.modifier_state
            else:
                modifiers = QApplication.keyboardModifiers()

        if modifiers == Qt.NoModifier: # type: ignore
            modifiers = QApplication.keyboardModifiers()  # fallback to current

        ctrl = bool(modifiers & Qt.ControlModifier) # type: ignore
        shift = bool(modifiers & Qt.ShiftModifier) # type: ignore

        # - No modifiers: skip metadata
        # - With Ctrl: load basic metadata
        # - With Ctrl+Shift: load extended metadata
        skip_metadata = not ctrl
        use_extended = ctrl and shift

        logger.debug(
            f"[determine_metadata_mode] modifiers={int(modifiers)}, "
            f"ctrl={ctrl}, shift={shift}, skip_metadata={skip_metadata}, use_extended={use_extended}"
        )

        return skip_metadata, use_extended

    def should_use_extended_metadata(self, modifier_state=None) -> bool:
        """
        Returns True if Ctrl+Shift are both held,
        used in cases where metadata is always loaded (double click, drag & drop).

        This assumes that metadata will be loaded — we only decide if it's fast or extended.

        Args:
            modifier_state: Qt.KeyboardModifiers to use, or None for current state
        """
        from core.qt_imports import Qt

        modifiers = modifier_state
        if modifiers is None:
            if self.parent_window and hasattr(self.parent_window, 'modifier_state'):
                modifiers = self.parent_window.modifier_state
            else:
                modifiers = QApplication.keyboardModifiers()

        ctrl = bool(modifiers & Qt.ControlModifier) # type: ignore
        shift = bool(modifiers & Qt.ShiftModifier) # type: ignore
        return ctrl and shift

    def shortcut_load_metadata(self) -> None:
        """
        Loads standard (non-extended) metadata for currently selected files.
        """
        if not self.parent_window:
            return

        if (hasattr(self.parent_window, 'file_table_view') and
            hasattr(self.parent_window, 'file_model')):
            # Use the new selection system
            selected_rows = self.parent_window.file_table_view._get_current_selection()
            selected = [self.parent_window.file_model.files[r]
                       for r in selected_rows
                       if 0 <= r < len(self.parent_window.file_model.files)]

            if not selected:
                logger.info("[Shortcut] No files selected for metadata loading")
                return

            logger.info(f"[Shortcut] Loading basic metadata for {len(selected)} files")
            # Use intelligent loading with cache checking and smart UX
            self.load_metadata_for_items(selected, use_extended=False, source="shortcut")

    def shortcut_load_extended_metadata(self) -> None:
        """
        Loads extended metadata for selected files via custom selection system.
        """
        if not self.parent_window:
            return

        if self.is_running_metadata_task():
            logger.warning("[Shortcut] Metadata scan already running — shortcut ignored.")
            return

        if (hasattr(self.parent_window, 'file_table_view') and
            hasattr(self.parent_window, 'file_model')):
            # Use the new selection system
            selected_rows = self.parent_window.file_table_view._get_current_selection()
            selected = [self.parent_window.file_model.files[r]
                       for r in selected_rows
                       if 0 <= r < len(self.parent_window.file_model.files)]

            if not selected:
                logger.info("[Shortcut] No files selected for extended metadata loading")
                return

            logger.info(f"[Shortcut] Loading extended metadata for {len(selected)} files")
            # Use intelligent loading with cache checking and smart UX
            self.load_metadata_for_items(selected, use_extended=True, source="shortcut")

    def load_metadata_for_items(self, items: List[FileItem], use_extended: bool = False, source: str = "unknown") -> None:
        """
        Load metadata for the given FileItem objects.

        Args:
            items: List of FileItem objects to load metadata for
            use_extended: Whether to use extended metadata loading
            source: Source of the request (for logging)
        """
        if not items:
            logger.warning("[MetadataManager] No items provided for metadata loading")
            return

        logger.debug(f"[MetadataManager] Processing {len(items)} items (extended={use_extended}, source={source})", extra={"dev_only": True})

        logger.debug(f"[MetadataManager] Loading metadata for {len(items)} items (extended={use_extended}, source={source})", extra={"dev_only": True})

        # SIMPLIFIED: No selection preservation or flag setting needed

        # Check what items need loading vs what's already cached
        needs_loading = []
        logger.debug(f"[MetadataManager] Cache check start: items={len(items)}, use_extended={use_extended}", extra={"dev_only": True})

        for item in items:
            # Check cache for existing metadata
            cache_entry = self.parent_window.metadata_cache.get_entry(item.full_path) if self.parent_window else None

            if cache_entry and hasattr(cache_entry, 'is_extended'):
                # If we have cache and it matches the requested type, skip loading
                if cache_entry.is_extended == use_extended:
                    logger.debug(f"[{source}] {item.filename} already cached (extended={use_extended})")
                    continue

            logger.debug(f"[{source}] {item.filename} needs loading (no cache entry)")
            needs_loading.append(item)

        logger.debug(f"[MetadataManager] Cache check result: needs_loading={len(needs_loading)}", extra={"dev_only": True})

        # Get metadata tree view reference
        metadata_tree_view = (self.parent_window.metadata_tree_view
                            if self.parent_window and hasattr(self.parent_window, 'metadata_tree_view')
                            else None)

        # If nothing needs loading, just handle display logic
        if not needs_loading:
            logger.info(f"[{source}] All {len(items)} files already cached")

            # SIMPLIFIED: Always display metadata for cached items too
            if metadata_tree_view and items:
                # Always display metadata - same logic as loaded items
                display_file = items[0] if len(items) == 1 else items[-1]
                logger.debug(f"[MetadataManager] Displaying cached metadata for: {display_file.filename}", extra={"dev_only": True})
                metadata_tree_view.display_file_metadata(display_file)

            return

        # Determine loading mode based on file count and settings
        loading_mode = self.determine_loading_mode(len(needs_loading), use_extended)
        logger.debug(f"[MetadataManager] Loading mode: {loading_mode}", extra={"dev_only": True})

        # Handle different loading modes
        if loading_mode == "single_file_wait_cursor":
            logger.info(f"[{source}] Loading metadata for single file with wait_cursor (extended={use_extended})")

            from utils.cursor_helper import wait_cursor
            with wait_cursor():
                # Load metadata for the single file
                file_item = needs_loading[0]
                metadata = self._exiftool_wrapper.get_metadata(file_item.full_path, use_extended=use_extended)

                if metadata:
                    # Cache the result in both local and parent window caches
                    cache_key = (file_item.full_path, use_extended)
                    self._metadata_cache[cache_key] = metadata

                    # Also save to parent window's metadata_cache for UI display
                    if self.parent_window and hasattr(self.parent_window, 'metadata_cache'):
                        self.parent_window.metadata_cache.set(file_item.full_path, metadata, is_extended=use_extended)

                    # Update the file item
                    file_item.metadata = metadata

                    # Emit dataChanged signal to update UI
                    if self.parent_window and hasattr(self.parent_window, 'file_model'):
                        try:
                            # Find the row index and emit dataChanged for the entire row
                            for i, file in enumerate(self.parent_window.file_model.files):
                                if paths_equal(file.full_path, file_item.full_path):
                                    top_left = self.parent_window.file_model.index(i, 0)
                                    bottom_right = self.parent_window.file_model.index(i, self.parent_window.file_model.columnCount() - 1)
                                    self.parent_window.file_model.dataChanged.emit(top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole])
                                    break
                        except Exception as e:
                            logger.warning(f"[Loader] Failed to emit dataChanged for {file_item.filename}: {e}")

        elif loading_mode == "multiple_files_dialog":
            logger.info(f"[{source}] Loading metadata for {len(needs_loading)} files with dialog (extended={use_extended})")

            # Use metadata waiting dialog for large batches
            from widgets.metadata_waiting_dialog import MetadataWaitingDialog

            # Create loading dialog
            loading_dialog = MetadataWaitingDialog(
                parent=self.parent_window,
                is_extended=use_extended,
                cancel_callback=None  # No cancellation for now
            )
            loading_dialog.set_status("Loading metadata..." if not use_extended else "Loading extended metadata...")
            loading_dialog.show()

            # Process each file
            for i, file_item in enumerate(needs_loading):
                # Update progress
                loading_dialog.set_progress(i, len(needs_loading))
                loading_dialog.set_filename(file_item.filename)

                # Process events to update the dialog
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()

                metadata = self._exiftool_wrapper.get_metadata(file_item.full_path, use_extended=use_extended)

                if metadata:
                    # Cache the result in both local and parent window caches
                    cache_key = (file_item.full_path, use_extended)
                    self._metadata_cache[cache_key] = metadata

                    # Also save to parent window's metadata_cache for UI display
                    if self.parent_window and hasattr(self.parent_window, 'metadata_cache'):
                        self.parent_window.metadata_cache.set(file_item.full_path, metadata, is_extended=use_extended)

                    # Update the file item
                    file_item.metadata = metadata

                    # Emit dataChanged signal to update UI
                    if self.parent_window and hasattr(self.parent_window, 'file_model'):
                        try:
                            # Find the row index and emit dataChanged for the entire row
                            for i, file in enumerate(self.parent_window.file_model.files):
                                if paths_equal(file.full_path, file_item.full_path):
                                    top_left = self.parent_window.file_model.index(i, 0)
                                    bottom_right = self.parent_window.file_model.index(i, self.parent_window.file_model.columnCount() - 1)
                                    self.parent_window.file_model.dataChanged.emit(top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole])
                                    break
                        except Exception as e:
                            logger.warning(f"[Loader] Failed to emit dataChanged for {file_item.filename}: {e}")

            # Complete progress and close dialog
            loading_dialog.set_progress(len(needs_loading), len(needs_loading))
            loading_dialog.set_status("Loading complete!")
            QApplication.processEvents()

            # Keep dialog visible for a moment to show completion
            from utils.timer_manager import schedule_dialog_close
            schedule_dialog_close(loading_dialog.close, 500)

        else:
            logger.warning(f"[MetadataManager] Unhandled loading mode: {loading_mode}")

        # SIMPLIFIED APPROACH: ALWAYS DISPLAY METADATA
        # For both single and multiple files, show metadata for the first/last file
        if metadata_tree_view and items:
            # For single file, use first item; for multiple files, use last item for better UX
            display_file = items[0] if len(items) == 1 else items[-1]
            logger.info(f"[MetadataManager] Displaying metadata for file: {display_file.filename} (from {len(items)} selected)")
            metadata_tree_view.display_file_metadata(display_file)

    def save_metadata_for_selected(self) -> None:
        """
        Save modified metadata for the currently selected file(s) only.
        """
        if not hasattr(self.parent_window, 'metadata_tree_view'):
            logger.warning("[MetadataManager] No metadata tree view available")
            return

        # Get all modified metadata for all files
        all_modified_metadata = self.parent_window.metadata_tree_view.get_all_modified_metadata_for_files()

        if not all_modified_metadata:
            logger.info("[MetadataManager] No metadata modifications to save")
            return

        # Get selected files for filtering
        selected_files = []
        if hasattr(self.parent_window, 'file_table_view'):
            selected_rows = self.parent_window.file_table_view._get_current_selection()
            if selected_rows and hasattr(self.parent_window, 'file_model'):
                for row in selected_rows:
                    if 0 <= row < len(self.parent_window.file_model.files):
                        selected_files.append(self.parent_window.file_model.files[row])

        if not selected_files:
            logger.warning("[MetadataManager] No files selected for metadata save")
            return

        # Get file paths of selected files for filtering
        selected_file_paths = {file_item.full_path for file_item in selected_files}

        # Find files that have modifications AND are selected
        files_to_save = []
        for file_path, modified_metadata in all_modified_metadata.items():
            if file_path in selected_file_paths and modified_metadata:
                # Find the corresponding FileItem using normalized path comparison
                file_item = find_file_by_path(selected_files, file_path, 'full_path')
                if file_item:
                    files_to_save.append(file_item)

        if not files_to_save:
            logger.info("[MetadataManager] No selected files have metadata modifications")
            return

        logger.info(f"[MetadataManager] Saving metadata for {len(files_to_save)} selected file(s)")
        self._save_metadata_files(files_to_save, all_modified_metadata)

    def save_all_modified_metadata(self) -> None:
        """
        Save modified metadata for ALL files that have modifications, regardless of selection.
        """
        if not hasattr(self.parent_window, 'metadata_tree_view'):
            logger.warning("[MetadataManager] No metadata tree view available")
            return

        # Get all modified metadata for all files
        all_modified_metadata = self.parent_window.metadata_tree_view.get_all_modified_metadata_for_files()

        if not all_modified_metadata:
            logger.info("[MetadataManager] No metadata modifications to save")
            return

        # Get all files from file model to find corresponding FileItems
        all_files = []
        if hasattr(self.parent_window, 'file_model') and self.parent_window.file_model.files:
            all_files = self.parent_window.file_model.files

        if not all_files:
            logger.warning("[MetadataManager] No files available in file model")
            return

        # DEBUG: Log what we got from MetadataTree
        logger.debug(f"[MetadataManager] Got modifications for {len(all_modified_metadata)} files:", extra={"dev_only": True})
        for file_path, modifications in all_modified_metadata.items():
            logger.debug(f"[MetadataManager]   - {file_path}: {list(modifications.keys())}", extra={"dev_only": True})

        # Find FileItems for all files that have modifications
        files_to_save = []
        for file_path, modified_metadata in all_modified_metadata.items():
            if modified_metadata:  # Only files with actual modifications
                logger.debug(f"[MetadataManager] Looking for FileItem with path: {file_path}", extra={"dev_only": True})

                # Find the corresponding FileItem using normalized path comparison
                file_item = find_file_by_path(all_files, file_path, 'full_path')
                if file_item:
                    files_to_save.append(file_item)
                    logger.debug(f"[MetadataManager] MATCH found for: {file_item.filename}", extra={"dev_only": True})
                else:
                    logger.warning(f"[MetadataManager] NO MATCH found for path: {file_path}")

        logger.debug(f"[MetadataManager] Found {len(files_to_save)} FileItems to save", extra={"dev_only": True})

        if not files_to_save:
            logger.info("[MetadataManager] No files with metadata modifications found")
            return

        logger.info(f"[MetadataManager] Saving metadata for ALL {len(files_to_save)} modified file(s)")
        self._save_metadata_files(files_to_save, all_modified_metadata)

    def _save_metadata_files(self, files_to_save: list, all_modified_metadata: dict) -> None:
        """
        Common method to save metadata for a list of files.

        Args:
            files_to_save: List of FileItem objects to save
            all_modified_metadata: Dictionary of all modified metadata
        """
        # Create ExifToolWrapper instance
        from utils.exiftool_wrapper import ExifToolWrapper
        exiftool = ExifToolWrapper()

        success_count = 0
        failed_files = []

        try:
            if len(files_to_save) == 1:
                # Single file: Use wait cursor
                from utils.cursor_helper import wait_cursor
                with wait_cursor():
                    file_item = files_to_save[0]
                    modified_metadata = all_modified_metadata.get(file_item.full_path, {})

                    if modified_metadata:
                        logger.info(f"[MetadataManager] Saving metadata for: {file_item.filename}")
                        success = exiftool.write_metadata(file_item.full_path, modified_metadata)

                        if success:
                            logger.info(f"[MetadataManager] Successfully saved metadata to: {file_item.filename}")
                            success_count += 1
                            self._update_file_after_save(file_item)
                        else:
                            logger.error(f"[MetadataManager] Failed to save metadata to: {file_item.filename}")
                            failed_files.append(file_item.filename)
            else:
                # Multiple files: Use waiting dialog
                from widgets.metadata_waiting_dialog import MetadataWaitingDialog

                # Create save dialog
                save_dialog = MetadataWaitingDialog(
                    parent=self.parent_window,
                    is_extended=False,  # Save operation, not extended metadata
                    cancel_callback=None  # No cancellation for save operations
                )
                save_dialog.set_status("Saving metadata...")
                save_dialog.show()

                # Process each file
                for i, file_item in enumerate(files_to_save):
                    # Update progress
                    save_dialog.set_progress(i, len(files_to_save))
                    save_dialog.set_filename(file_item.filename)

                    # Process events to update the dialog
                    from PyQt5.QtWidgets import QApplication
                    QApplication.processEvents()

                    modified_metadata = all_modified_metadata.get(file_item.full_path, {})
                    if not modified_metadata:
                        continue

                    logger.info(f"[MetadataManager] Saving metadata for: {file_item.filename}")

                    # Write metadata to file
                    success = exiftool.write_metadata(file_item.full_path, modified_metadata)

                    if success:
                        logger.info(f"[MetadataManager] Successfully saved metadata to: {file_item.filename}")
                        success_count += 1
                        self._update_file_after_save(file_item)
                    else:
                        logger.error(f"[MetadataManager] Failed to save metadata to: {file_item.filename}")
                        failed_files.append(file_item.filename)

                # Complete progress and close dialog
                save_dialog.set_progress(len(files_to_save), len(files_to_save))
                save_dialog.set_status("Save complete!")
                QApplication.processEvents()

                # Keep dialog visible for a moment to show completion
                from utils.timer_manager import schedule_dialog_close
                schedule_dialog_close(save_dialog.close, 500)

            # Show result message
            self._show_save_results(success_count, failed_files, files_to_save)

        finally:
            exiftool.close()

    def _update_file_after_save(self, file_item):
        """Update file state after successful metadata save."""
        # Clear modifications for this file in tree view
        self.parent_window.metadata_tree_view.clear_modifications_for_file(file_item.full_path)

        # Clear modified flag in cache
        metadata_entry = self.parent_window.metadata_cache.get_entry(file_item.full_path)
        if metadata_entry:
            metadata_entry.modified = False

        # Update file icon
        file_item.metadata_status = "loaded"

        # Refresh file table to show updated icon
        if hasattr(self.parent_window, 'file_model'):
            try:
                row = self.parent_window.file_model.files.index(file_item)
                icon_index = self.parent_window.file_model.index(row, 0)
                from PyQt5.QtCore import Qt
                self.parent_window.file_model.dataChanged.emit(
                    icon_index,
                    icon_index,
                    [Qt.DecorationRole]
                )
            except ValueError:
                pass  # File not in model

    def _show_save_results(self, success_count, failed_files, files_to_save):
        """Show results status message after save operation."""
        if success_count > 0:
            if failed_files:
                # Show error dialog only for failed files
                from utils.dialog_utils import show_error_message
                message = f"Successfully saved {success_count} file(s), but failed to save:\n" + "\n".join(failed_files)
                show_error_message(self.parent_window, "Partial Save Failure", message)
            else:
                # Success - just show status message, no dialog
                if success_count == 1:
                    status_msg = f"Saved metadata changes to {files_to_save[0].filename}"
                else:
                    status_msg = f"Saved metadata changes to {success_count} files"

                if hasattr(self.parent_window, 'set_status'):
                    self.parent_window.set_status(status_msg, color="green", auto_reset=True)
        elif failed_files:
            # Show error dialog only for failures
            from utils.dialog_utils import show_error_message
            show_error_message(
                self.parent_window,
                "Save Failed",
                "Failed to save metadata changes to:\n" + "\n".join(failed_files)
            )

    def _get_files_from_source(self, source: str) -> Optional[List[FileItem]]:
        """
        Get list of files based on source identifier.

        Args:
            source: Source identifier (e.g., "selected", "all")

        Returns:
            List of FileItem objects or None
        """
        if not self.parent_window:
            return None

        if source == "selected":
            # Get selected files
            if hasattr(self.parent_window, 'file_table_view'):
                selected_rows = self.parent_window.file_table_view._get_current_selection()
                if selected_rows and hasattr(self.parent_window, 'file_model'):
                    return [self.parent_window.file_model.files[r]
                           for r in selected_rows
                           if 0 <= r < len(self.parent_window.file_model.files)]
        elif source == "all":
            # Get all files
            if hasattr(self.parent_window, 'file_model'):
                return self.parent_window.file_model.files

        return None
