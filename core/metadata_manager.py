"""
metadata_manager.py

Author: Michael Economou
Date: 2025-05-01

Centralized metadata management operations extracted from MainWindow.
Handles metadata loading, progress tracking, thread management, and UI coordination.
"""

import os
from typing import List, Optional

from core.qt_imports import QApplication, QThread, QTimer
from PyQt5.QtCore import Qt
from models.file_item import FileItem
from utils.cursor_helper import wait_cursor
from utils.logger_factory import get_cached_logger
from utils.path_utils import find_file_by_path, paths_equal
from utils.timer_manager import schedule_ui_update
from widgets.custom_msgdialog import CustomMessageDialog
from widgets.metadata_waiting_dialog import MetadataWaitingDialog
from widgets.metadata_worker import MetadataWorker

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

        # Thread management
        self.metadata_thread = None
        self.metadata_worker = None
        self.loading_dialog = None

        # State tracking
        self.force_extended_metadata = False
        self._original_selection_count = 0  # Track original selection count for metadata tree update
        self._target_file_path = None  # Track target file for single selection display


        # Initialize metadata cache and exiftool wrapper
        self._metadata_cache = {}  # Cache for metadata results

        # Initialize ExifTool wrapper for single file operations
        from utils.exiftool_wrapper import ExifToolWrapper
        self._exiftool_wrapper = ExifToolWrapper()

        # Flag to skip selection changes during metadata operations
        self._skip_selection_changed = False

    def start_metadata_scan(self, file_paths: List[str]) -> None:
        """
        Initiates the metadata scan process for the given file paths.

        Args:
            file_paths: List of file paths to scan for metadata
        """

        logger.debug(f"[MetadataScan] Launch with force_extended = {self.force_extended_metadata}")

        # Store current selection count and target file for later use
        current_selection = None
        if (self.parent_window and
            hasattr(self.parent_window, 'file_table_view') and
            hasattr(self.parent_window.file_table_view, '_get_current_selection')):
            current_selection = self.parent_window.file_table_view._get_current_selection()
            self._original_selection_count = len(current_selection)
            if len(current_selection) == 1 and len(file_paths) == 1:
                self._target_file_path = file_paths[0]
            logger.debug(f"[MetadataManager] Selection count before metadata scan: {self._original_selection_count}")

        is_extended = self.force_extended_metadata
        self.loading_dialog = MetadataWaitingDialog(self.parent_window, is_extended=is_extended)
        self.loading_dialog.set_status("Reading metadata...")
        self.loading_dialog.set_filename("")
        self.loading_dialog.set_progress(0, len(file_paths))

        # Connect cancel (ESC or manual close) to cancel logic
        self.loading_dialog.rejected.connect(self.cancel_metadata_loading)

        self.loading_dialog.show()
        QApplication.processEvents()

        self.load_metadata_in_thread(file_paths)

    def load_metadata_in_thread(self, file_paths: List[str]) -> None:
        """
        Initializes and starts a metadata loading thread using MetadataWorker.

        This method:
        - Creates a QThread and assigns a MetadataWorker to it
        - Passes the list of file paths and extended mode flag to the worker
        - Connects worker signals (progress, finished) to appropriate slots
        - Ensures signal `progress` updates the dialog safely via on_metadata_progress()
        - Starts the thread execution with the run_batch method

        Parameters
        ----------
        file_paths : List[str]
            A list of full file paths to extract metadata from.
        """
        logger.info(f"[MetadataManager] Starting metadata thread for {len(file_paths)} files")

        # Create background thread
        self.metadata_thread = QThread()

        # Get required components from parent window
        metadata_loader = getattr(self.parent_window, 'metadata_loader', None)
        metadata_cache = getattr(self.parent_window, 'metadata_cache', None)

        if not metadata_loader or not metadata_cache:
            logger.error("[MetadataManager] Missing metadata_loader or metadata_cache from parent window")
            return

        # Create worker object (inherits from QObject)
        self.metadata_worker = MetadataWorker(
            reader=metadata_loader,
            metadata_cache=metadata_cache
            # No parent to allow moveToThread
        )

        # Give worker access to main window for FileItem updates
        self.metadata_worker.main_window = self.parent_window

        # Set the worker's inputs
        self.metadata_worker.file_path = file_paths
        self.metadata_worker.use_extended = self.force_extended_metadata

        # Move worker to the thread context
        self.metadata_worker.moveToThread(self.metadata_thread)

        # Connect signals
        self.metadata_thread.started.connect(self.metadata_worker.run_batch)

        # update progress bar and message
        self.metadata_worker.progress.connect(self.on_metadata_progress)

        # Signal when finished
        self.metadata_worker.finished.connect(self.handle_metadata_finished)

        # Start thread execution
        self.metadata_thread.start()



    def on_metadata_progress(self, current: int, total: int) -> None:
        """
        Slot connected to the `progress` signal of the MetadataWorker.

        This method updates the loading dialog's progress bar and message label
        as metadata files are being processed in the background.

        Args:
            current (int): Number of files analyzed so far (1-based index).
            total (int): Total number of files to analyze.
        """
        if self.metadata_worker is None:
            logger.warning("Progress signal received after worker was already cleaned up — ignoring.")
            return

        logger.debug(f"Metadata progress update: {current} of {total}", extra={"dev_only": True})

        if self.loading_dialog:
            self.loading_dialog.set_progress(current, total)

            # Show filename of current file (current-1 because progress starts at 1)
            if 0 <= current - 1 < len(self.metadata_worker.file_path):
                filename = os.path.basename(self.metadata_worker.file_path[current - 1])
                self.loading_dialog.set_filename(filename)
            else:
                self.loading_dialog.set_filename("")

            # Optional: update the label only once at the beginning
            if current == 1:
                self.loading_dialog.set_status("Reading metadata...")

            # Force immediate UI refresh
            QApplication.processEvents()
        else:
            logger.warning("Loading dialog not available during progress update — skipping UI update.")

    def handle_metadata_finished(self) -> None:
        """
        Slot to handle the completion of metadata loading.

        - Closes the loading dialog
        - Restores the cursor to default
        - Updates the UI as needed
        """
        logger.info("[MetadataManager] Metadata loading finished")

        # Disconnect the cancel handler to prevent ESC after completion from clearing selection
        if self.loading_dialog:
            try:
                self.loading_dialog.rejected.disconnect()
                logger.debug("[MetadataManager] Disconnected cancel handler from dialog")
            except (TypeError, RuntimeError):
                pass  # Already disconnected or not connected
            self.loading_dialog.close()

        # Always restore the cursor when metadata loading is finished
        QApplication.restoreOverrideCursor()
        logger.debug("[MetadataManager] Cursor explicitly restored after metadata task.")

        # Update metadata tree based on original selection using centralized logic
        metadata_tree_view = getattr(self.parent_window, 'metadata_tree_view', None)
        should_display = (metadata_tree_view and
                        hasattr(metadata_tree_view, 'should_display_metadata_for_selection') and
                        metadata_tree_view.should_display_metadata_for_selection(self._original_selection_count))

        if should_display and self._target_file_path:
            # Single file was selected - show its metadata
            metadata_cache = getattr(self.parent_window, 'metadata_cache', None)
            if metadata_cache:
                metadata = metadata_cache.get(self._target_file_path)
                if (metadata and metadata_tree_view and hasattr(metadata_tree_view, 'display_metadata')):
                    metadata_tree_view.display_metadata(metadata, context="batch_completed")
                    logger.debug("[MetadataManager] Displayed metadata for single file after batch loading")
        elif self._original_selection_count > 0:
            # Multiple files were selected - show appropriate message
            if (metadata_tree_view and hasattr(metadata_tree_view, 'show_empty_state')):
                metadata_tree_view.show_empty_state("Multiple files selected")
                logger.debug(f"[MetadataManager] Showing 'Multiple files selected' after batch loading {self._original_selection_count} files")

        # CRITICAL: Selective UI update for loaded files only
        # This ensures the metadata icons are updated without causing selection loss
        if (self.parent_window and
            hasattr(self.parent_window, 'file_model') and
            hasattr(self.parent_window, 'file_table_view') and
            hasattr(self.parent_window.metadata_worker, 'file_path')):
            # Get the list of files that were loaded
            loaded_file_paths = self.metadata_worker.file_path
            file_model = self.parent_window.file_model
            file_table_view = self.parent_window.file_table_view

            # Update only the rows for files that were loaded
            for file_path in loaded_file_paths:
                # Find the file in the model using normalized path comparison
                for i, file_item in enumerate(file_model.files):
                    if paths_equal(file_item.full_path, file_path):
                        # Update all columns for this row
                        for col in range(file_model.columnCount()):
                            idx = file_model.index(i, col)
                            rect = file_table_view.visualRect(idx)
                            if rect.isValid():
                                file_table_view.viewport().update(rect)
                        break

            logger.debug(f"[MetadataManager] Selective viewport update for {len(loaded_file_paths)} files after batch loading")



        # Reset tracking variables
        self._original_selection_count = 0
        self._target_file_path = None

        # CRITICAL: Clear metadata operation flag in FileLoadManager to allow normal UI refresh
        if (self.parent_window and
            hasattr(self.parent_window, 'file_load_manager') and
            hasattr(self.parent_window.file_load_manager, 'clear_metadata_operation_flag')):
            self.parent_window.file_load_manager.clear_metadata_operation_flag()

        # CRITICAL: Clean up the worker and thread to prevent "already running" issues
        self.cleanup_metadata_worker()
        logger.debug("[MetadataManager] Worker and thread cleaned up after metadata loading finished")

    def cleanup_metadata_worker(self) -> None:
        """
        Safely shuts down and deletes the metadata worker and its thread.

        This method ensures that:
        - The thread is properly stopped (using quit + wait)
        - The worker and thread are deleted using deleteLater
        - All references are cleared to avoid leaks or crashes
        """
        if self.metadata_thread:
            if self.metadata_thread.isRunning():
                logger.debug("[MetadataManager] Quitting metadata thread...")
                self.metadata_thread.quit()
                self.metadata_thread.wait()
                logger.debug("[MetadataManager] Metadata thread has stopped.")

            self.metadata_thread.deleteLater()
            self.metadata_thread = None
            logger.debug("[MetadataManager] Metadata thread deleted.")

        if self.metadata_worker:
            self.metadata_worker.deleteLater()
            self.metadata_worker = None
            logger.debug("[MetadataManager] Metadata worker deleted.")

        self.force_extended_metadata = False
        if self.parent_window:
            self.parent_window.force_extended_metadata = False

        # Reset tracking variables
        self._original_selection_count = 0
        self._target_file_path = None

    def cancel_metadata_loading(self) -> None:
        """
        Cancels the metadata loading process and ensures the thread is properly terminated.
        """
        logger.info("[MetadataManager] Cancelling metadata loading")

        # CRITICAL: Clear metadata operation flag in FileLoadManager
        if (self.parent_window and
            hasattr(self.parent_window, 'file_load_manager') and
            hasattr(self.parent_window.file_load_manager, 'clear_metadata_operation_flag')):
            self.parent_window.file_load_manager.clear_metadata_operation_flag()

        if hasattr(self, 'metadata_thread') and self.metadata_thread and self.metadata_thread.isRunning():
            if self.metadata_worker:
                self.metadata_worker.cancel()  # Use cancel method to stop the worker
            self.metadata_thread.quit()
            self.metadata_thread.wait()

        if self.loading_dialog:
            self.loading_dialog.close()

        # Ensure cursor is restored, even if there were multiple setOverrideCursor calls
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()

        logger.debug("[MetadataManager] Cursor fully restored after metadata cancellation.")

        # CRITICAL: Clean up the worker and thread to prevent "already running" issues
        self.cleanup_metadata_worker()
        logger.debug("[MetadataManager] Worker and thread cleaned up after metadata cancellation")

    def on_metadata_error(self, message: str) -> None:
        """
        Handles unexpected errors during metadata loading.

        - Restores the UI cursor
        - Closes the progress dialog
        - Cleans up worker and thread
        - Shows an error message to the user

        Args:
            message (str): The error message to display.
        """
        logger.error(f"Metadata error: {message}")

        # 1. Restore busy cursor
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()
        logger.debug("[MetadataManager] Cursor fully restored after metadata error.")

        # 2. Close the loading dialog
        if self.loading_dialog:
            logger.info("Closing loading dialog due to error.")
            self.loading_dialog.close()
            self.loading_dialog = None
        else:
            logger.warning("No loading dialog found during error handling.")

        # 3. Clean up worker and thread
        self.cleanup_metadata_worker()

        # 4. Notify user
        if self.parent_window:
            CustomMessageDialog.show_warning(self.parent_window, "Metadata Error", f"Failed to read metadata:\n\n{message}")

    def is_running_metadata_task(self) -> bool:
        """
        Returns True if a metadata thread is currently active.

        This helps prevent overlapping metadata scans by checking if
        a previous background task is still running.

        Returns
        -------
        bool
            True if metadata_thread exists and is running, False otherwise.
        """
        running = (
            self.metadata_thread is not None
            and self.metadata_thread.isRunning()
        )
        logger.debug(f"Metadata task running? {running}")
        return running

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

        # New logic:
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

        # DEBUG: Log what we received
        logger.warning(f"[DEBUG] METADATA MANAGER RECEIVED: {len(items)} items, extended={use_extended}, source={source}")
        logger.warning(f"[DEBUG] METADATA MANAGER FILES: {[item.filename for item in items[:3]]}{'...' if len(items) > 3 else ''}")

        logger.debug(f"[MetadataManager] Loading metadata for {len(items)} items (extended={use_extended}, source={source})")

        # Store current selection to restore later (BEFORE any UI changes)
        current_selection = None
        if (self.parent_window and
            hasattr(self.parent_window, 'file_table_view') and
            hasattr(self.parent_window.file_table_view, '_get_current_selection')):
            current_selection = self.parent_window.file_table_view._get_current_selection()
            logger.debug(f"[MetadataManager] Preserved selection of {len(current_selection)} files before metadata operations")

        # Set flag to skip selection changes during metadata operations
        self._skip_selection_changed = True
        logger.debug("[MetadataManager] Enabled _skip_selection_changed flag")

        # Also set flag in FileTableView to prevent selection changes
        if self.parent_window and hasattr(self.parent_window, 'file_table_view'):
            self.parent_window.file_table_view._skip_selection_changed = True
            logger.debug("[MetadataManager] Set _skip_selection_changed flag in FileTableView")

        # Check what items need loading vs what's already cached
        needs_loading = []
        logger.debug(f"[MetadataManager] Cache check start: items={len(items)}, use_extended={use_extended}")
        logger.debug(f"[MetadataManager] Preserved selection at start: {current_selection}")

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

        logger.debug(f"[MetadataManager] Cache check result: needs_loading={len(needs_loading)}")

        # Get metadata tree view reference
        metadata_tree_view = (self.parent_window.metadata_tree_view
                            if self.parent_window and hasattr(self.parent_window, 'metadata_tree_view')
                            else None)

        # If nothing needs loading, just handle display logic
        if not needs_loading:
            logger.info(f"[{source}] All {len(items)} files already cached")

            # Clear the flag since we're not doing any loading
            self._skip_selection_changed = False
            logger.debug("[MetadataManager] Disabled _skip_selection_changed flag (cached)")

            # Also clear flag in FileTableView
            if self.parent_window and hasattr(self.parent_window, 'file_table_view'):
                self.parent_window.file_table_view._skip_selection_changed = False
                logger.debug("[MetadataManager] Cleared _skip_selection_changed flag in FileTableView (cached)")

            # SIMPLIFIED: Always display metadata for cached items too
            if metadata_tree_view and items:
                # Always display metadata - same logic as loaded items
                display_file = items[0] if len(items) == 1 else items[-1]
                logger.warning(f"[DEBUG] CACHED ITEMS - Displaying metadata for: {display_file.filename} (from {len(items)} cached)")
                metadata_tree_view.display_file_metadata(display_file)

            # ALSO restore selection for cached items
            if current_selection and self.parent_window and hasattr(self.parent_window, 'file_table_view'):
                file_table_view = self.parent_window.file_table_view
                logger.warning(f"[DEBUG] CACHED ITEMS - RESTORING SELECTION: {len(current_selection)} files")
                if hasattr(file_table_view, '_restore_selection_immediately'):
                    file_table_view._restore_selection_immediately(current_selection)

                # Force viewport update and status update for cached items too
                file_table_view.viewport().update()
                if hasattr(self.parent_window, 'update_files_label'):
                    self.parent_window.update_files_label()

            return

        # Determine loading mode based on file count and settings
        loading_mode = self.determine_loading_mode(len(needs_loading), use_extended)
        logger.debug(f"[MetadataManager] Loading mode: {loading_mode}")

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
                                if file.full_path == file_item.full_path:
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
                                if file.full_path == file_item.full_path:
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
            logger.warning(f"[DEBUG] LOADING MODE NOT HANDLED: {loading_mode}")

        # Clear flags BEFORE display and selection restoration to avoid conflicts
        self._skip_selection_changed = False
        logger.debug("[MetadataManager] Disabled _skip_selection_changed flag BEFORE display")

        # Also clear flag in FileTableView BEFORE display
        if self.parent_window and hasattr(self.parent_window, 'file_table_view'):
            self.parent_window.file_table_view._skip_selection_changed = False
            logger.debug("[MetadataManager] Cleared _skip_selection_changed flag in FileTableView BEFORE display")

        # SIMPLIFIED APPROACH: ALWAYS DISPLAY METADATA
        # For both single and multiple files, show metadata for the first/last file
        if metadata_tree_view and items:
            # For single file, use first item; for multiple files, use last item for better UX
            display_file = items[0] if len(items) == 1 else items[-1]
            logger.warning(f"[DEBUG] METADATA DISPLAY: Showing metadata for {display_file.filename} (from {len(items)} selected)")
            logger.info(f"[MetadataManager] Displaying metadata for file: {display_file.filename} (from {len(items)} selected)")
            metadata_tree_view.display_file_metadata(display_file)

        # Restore selection after metadata operations complete
        if current_selection and self.parent_window and hasattr(self.parent_window, 'file_table_view'):
            # Use immediate restoration AFTER clearing flags
            file_table_view = self.parent_window.file_table_view
            logger.warning(f"[DEBUG] RESTORING SELECTION: {len(current_selection)} files")
            if hasattr(file_table_view, '_restore_selection_immediately'):
                file_table_view._restore_selection_immediately(current_selection)

            # Force viewport update to show selection visually
            file_table_view.viewport().update()

            # Also update status label to show correct count
            if hasattr(self.parent_window, 'update_files_label'):
                self.parent_window.update_files_label()
            else:
                # Fallback: use the selection store
                file_table_view._update_selection_store(current_selection, emit_signal=True)

        # Always clear the flag at the end
        self._skip_selection_changed = False
        logger.warning("[DEBUG] DISABLED _skip_selection_changed flag (normal loading)")

        # Also clear flag in FileTableView
        if self.parent_window and hasattr(self.parent_window, 'file_table_view'):
            self.parent_window.file_table_view._skip_selection_changed = False
            logger.debug("[MetadataManager] Cleared _skip_selection_changed flag in FileTableView")

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
        logger.debug(f"[MetadataManager] Got modifications for {len(all_modified_metadata)} files:")
        for file_path, modifications in all_modified_metadata.items():
            logger.debug(f"[MetadataManager]   - {file_path}: {list(modifications.keys())}")

        # Find FileItems for all files that have modifications
        files_to_save = []
        for file_path, modified_metadata in all_modified_metadata.items():
            if modified_metadata:  # Only files with actual modifications
                logger.debug(f"[MetadataManager] Looking for FileItem with path: {file_path}")

                # Find the corresponding FileItem using normalized path comparison
                file_item = find_file_by_path(all_files, file_path, 'full_path')
                if file_item:
                    files_to_save.append(file_item)
                    logger.debug(f"[MetadataManager] MATCH found for: {file_item.filename}")
                else:
                    logger.warning(f"[MetadataManager] NO MATCH found for path: {file_path}")

        logger.debug(f"[MetadataManager] Found {len(files_to_save)} FileItems to save")

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
