"""
metadata_manager.py

Author: Michael Economou
Date: 2025-05-01

Centralized metadata management operations extracted from MainWindow.
Handles metadata loading, progress tracking, thread management, and UI coordination.
"""

import os
from typing import List, Optional, Any

from core.config_imports import LARGE_FOLDER_WARNING_THRESHOLD
from core.qt_imports import QApplication, QThread, QTimer
from models.file_item import FileItem
from utils.cursor_helper import wait_cursor
from utils.logger_factory import get_cached_logger
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
        self._preserved_selection = None  # Track selection before metadata loading starts
        self._preserved_selection = None  # Track selection before metadata loading starts

    def start_metadata_scan(self, file_paths: List[str]) -> None:
        """
        Initiates the metadata scan process for the given file paths.

        Args:
            file_paths: List of file paths to scan for metadata
        """
        logger.warning("[DEBUG] start_metadata_scan CALLED")
        logger.debug(f"[MetadataScan] Launch with force_extended = {self.force_extended_metadata}")

        # CRITICAL: Store current selection BEFORE showing dialog or starting thread
        # The dialog or thread might cause selection loss
        self._preserved_selection = None
        if (self.parent_window and
            hasattr(self.parent_window, 'file_table_view') and
            hasattr(self.parent_window.file_table_view, '_get_current_selection')):
            self._preserved_selection = self.parent_window.file_table_view._get_current_selection().copy()
            logger.debug(f"[MetadataManager] Preserved selection of {len(self._preserved_selection)} files before metadata scan")

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
            except:
                pass  # Already disconnected or not connected
            self.loading_dialog.close()

        # Always restore the cursor when metadata loading is finished
        QApplication.restoreOverrideCursor()
        logger.debug("[MetadataManager] Cursor explicitly restored after metadata task.")

        # Update metadata tree based on original selection
        if self._original_selection_count == 1 and self._target_file_path:
            # Single file was selected - show its metadata
            metadata_cache = getattr(self.parent_window, 'metadata_cache', None)
            if metadata_cache:
                metadata = metadata_cache.get(self._target_file_path)
                if (metadata and self.parent_window and
                    hasattr(self.parent_window, 'metadata_tree_view') and
                    hasattr(self.parent_window.metadata_tree_view, 'display_metadata')):
                    self.parent_window.metadata_tree_view.display_metadata(metadata, context="batch_completed")
                    logger.debug(f"[MetadataManager] Displayed metadata for single file after batch loading")
        elif self._original_selection_count > 1:
            # Multiple files were selected - show appropriate message
            if (self.parent_window and
                hasattr(self.parent_window, 'metadata_tree_view') and
                hasattr(self.parent_window.metadata_tree_view, 'show_empty_state')):
                self.parent_window.metadata_tree_view.show_empty_state("Multiple files selected")
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
                # Find the file in the model
                for i, file_item in enumerate(file_model.files):
                    if file_item.full_path == file_path:
                        # Update all columns for this row
                        for col in range(file_model.columnCount()):
                            idx = file_model.index(i, col)
                            rect = file_table_view.visualRect(idx)
                            if rect.isValid():
                                file_table_view.viewport().update(rect)
                        break

            logger.debug(f"[MetadataManager] Selective viewport update for {len(loaded_file_paths)} files after batch loading")

        # CRITICAL: Restore selection after all UI updates using preserved selection
        if (hasattr(self, '_preserved_selection') and
            self._preserved_selection is not None and
            self.parent_window and
            hasattr(self.parent_window, 'file_table_view')):

            logger.debug(f"[MetadataManager] Restoring selection immediately: {len(self._preserved_selection)} files")

            # Restore selection immediately
            if hasattr(self.parent_window.file_table_view, '_update_selection_store'):
                self.parent_window.file_table_view._update_selection_store(self._preserved_selection, emit_signal=True)
                logger.debug(f"[MetadataManager] Selection restored successfully")

            # Clear preserved selection after restoration
            self._preserved_selection = None
        else:
            # Debug why restoration is not happening
            logger.debug(f"[MetadataManager] Selection restoration NOT happening because:")
            logger.debug(f"  - hasattr(self, '_preserved_selection'): {hasattr(self, '_preserved_selection')}")
            if hasattr(self, '_preserved_selection'):
                logger.debug(f"  - self._preserved_selection is not None: {self._preserved_selection is not None}")
                if self._preserved_selection is not None:
                    logger.debug(f"  - self._preserved_selection has {len(self._preserved_selection)} files")

        # Reset tracking variables
        self._original_selection_count = 0
        self._target_file_path = None

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
        # Don't reset _preserved_selection here - it might still be used by the timer callback

    def cancel_metadata_loading(self) -> None:
        """
        Cancels the metadata loading process and ensures the thread is properly terminated.
        """
        logger.info("[MetadataManager] Cancelling metadata loading")

        # Clear preserved selection to prevent restoration after cancel
        self._preserved_selection = None

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

    def load_metadata_for_items(
        self,
        items: List[FileItem],
        use_extended: bool = False,
        source: str = "unknown"
    ) -> None:
        """
        Intelligent metadata loading with cache checking and smart UX.

        Features:
        - Cache intelligence: Only loads what's needed
        - Smart UX: Wait cursor for 1 file, dialog for multiple
        - Extended metadata support: Properly handles basic vs extended

        Parameters:
            items: List of FileItem objects to load metadata for
            use_extended: Whether to load extended metadata
            source: Source of the call (for logging)
        """
        if not items:
            if self.parent_window and hasattr(self.parent_window, 'set_status'):
                self.parent_window.set_status("No files selected.", color="gray", auto_reset=True)
            return

        if self.is_running_metadata_task():
            logger.warning(f"[{source}] Metadata scan already running — ignoring request.")
            return

        # CRITICAL: Store current selection BEFORE any operations
        # This ensures we can restore it after metadata loading completes
        self._preserved_selection = None
        if (self.parent_window and
            hasattr(self.parent_window, 'file_table_view') and
            hasattr(self.parent_window.file_table_view, '_get_current_selection')):
            self._preserved_selection = self.parent_window.file_table_view._get_current_selection().copy()
            logger.debug(f"[MetadataManager] Preserved selection of {len(self._preserved_selection)} files before metadata operations")

        # Get required components from parent window
        metadata_cache = getattr(self.parent_window, 'metadata_cache', None)
        metadata_loader = getattr(self.parent_window, 'metadata_loader', None)

        if not metadata_cache or not metadata_loader:
            logger.error("[load_metadata_for_items] Missing metadata_cache or metadata_loader from parent window")
            return

        # Intelligent cache checking - only load what's needed
        needs_loading = []
        for item in items:
            # Get the cached entry (which includes extended status)
            entry = metadata_cache.get_entry(item.full_path)

            # Add file to loading list if:
            # 1. No cached entry exists
            # 2. Extended metadata is requested but entry is not extended
            if not entry:
                logger.debug(f"[{source}] {item.filename} needs loading (no cache entry)")
                needs_loading.append(item)
            elif use_extended and not entry.is_extended:
                logger.debug(f"[{source}] {item.filename} needs loading (extended requested but only basic loaded)")
                needs_loading.append(item)
            else:
                logger.debug(f"[{source}] {item.filename} already has {'extended' if entry.is_extended else 'basic'} metadata")

        # Always show metadata for the last file in the list
        target_file = items[-1]

        # If all files already have appropriate metadata, just show it for the target file
        if not needs_loading:
            # For single file selection, display the existing metadata
            # For multiple files, don't show anything (like context menu behavior)
            if len(items) == 1:
                metadata = target_file.metadata or metadata_cache.get(target_file.full_path)
                if (self.parent_window and
                    hasattr(self.parent_window, 'metadata_tree_view') and
                    hasattr(self.parent_window.metadata_tree_view, 'display_metadata')):
                    self.parent_window.metadata_tree_view.display_metadata(metadata, context=f"existing_{source}")
                if self.parent_window and hasattr(self.parent_window, 'set_status'):
                    self.parent_window.set_status(f"Metadata already loaded for {target_file.filename}.", color="green", auto_reset=True)
            else:
                # Multiple files - don't show metadata tree, just status
                if self.parent_window and hasattr(self.parent_window, 'set_status'):
                    self.parent_window.set_status(f"Metadata already loaded for {len(items)} files.", color="green", auto_reset=True)
                # Optionally clear the tree or show a message
                if (self.parent_window and
                    hasattr(self.parent_window, 'metadata_tree_view') and
                    hasattr(self.parent_window.metadata_tree_view, 'show_empty_state')):
                    self.parent_window.metadata_tree_view.show_empty_state("Multiple files selected")
            # Reset preserved selection since nothing was loaded
            self._preserved_selection = None
            return

        # Check for large files if extended metadata was requested
        if (use_extended and self.parent_window and
            hasattr(self.parent_window, 'dialog_manager') and
            not self.parent_window.dialog_manager.confirm_large_files(needs_loading)):
            # Reset preserved selection since loading was cancelled
            self._preserved_selection = None
            return

        # Set extended metadata flag (sync with parent window)
        self.force_extended_metadata = use_extended
        if self.parent_window:
            self.parent_window.force_extended_metadata = use_extended

        # Store original selection info for metadata tree update after loading
        self._original_selection_count = len(items)
        self._target_file_path = target_file.full_path if target_file else None

        # Smart UX: Choose loading method based on number of files
        if len(needs_loading) > 1:
            # Multiple files: Use dialog with progress bar for better UX
            logger.info(f"[{source}] Loading metadata for {len(needs_loading)} files with dialog (extended={use_extended})")
            # Convert to file paths and use the base metadata scan method
            file_paths = [item.full_path for item in needs_loading]
            with wait_cursor(restore_after=False):
                self.start_metadata_scan(file_paths)
            # Metadata tree update will be handled in handle_metadata_finished()
            # Selection restoration will also be handled there
        else:
            # Single file: Use simple wait_cursor for faster UX
            logger.info(f"[{source}] Loading metadata for single file with wait_cursor (extended={use_extended})")

            # Store the selection before the wait cursor
            selection_before_load = self._preserved_selection

            with wait_cursor():
                metadata_loader.load(
                    needs_loading,
                    force=False,
                    cache=metadata_cache,
                    use_extended=use_extended
                )

            # Only display metadata if we have single file selection originally
            # For multiple files (even if only one needs loading), don't show metadata tree
            if len(items) == 1:
                # Always display metadata for the target file (last in list)
                metadata = target_file.metadata or metadata_cache.get(target_file.full_path)
                if (self.parent_window and
                    hasattr(self.parent_window, 'metadata_tree_view') and
                    hasattr(self.parent_window.metadata_tree_view, 'display_metadata')):
                    self.parent_window.metadata_tree_view.display_metadata(metadata, context=source)
            else:
                # Multiple files selected - don't show metadata tree
                logger.debug(f"[{source}] Multiple files selected ({len(items)}) - not updating metadata tree after single file load")
                if (self.parent_window and
                    hasattr(self.parent_window, 'metadata_tree_view') and
                    hasattr(self.parent_window.metadata_tree_view, 'show_empty_state')):
                    self.parent_window.metadata_tree_view.show_empty_state("Multiple files selected")

            # Update UI for all loaded files
            if (self.parent_window and
                hasattr(self.parent_window, 'file_model') and
                hasattr(self.parent_window, 'file_table_view')):
                for loaded_file in needs_loading:
                    try:
                        row = self.parent_window.file_model.files.index(loaded_file)
                        for col in range(self.parent_window.file_model.columnCount()):
                            idx = self.parent_window.file_model.index(row, col)
                            self.parent_window.file_table_view.viewport().update(
                                self.parent_window.file_table_view.visualRect(idx)
                            )
                    except (ValueError, AttributeError) as e:
                        logger.debug(f"[MetadataManager] Could not update UI for file: {e}")

            # CRITICAL: Restore selection after UI updates and metadata loading
            # This is especially important for single file drag & drop
            if selection_before_load is not None and hasattr(self.parent_window.file_table_view, '_update_selection_store'):
                self.parent_window.file_table_view._update_selection_store(selection_before_load, emit_signal=False)
                logger.debug(f"[MetadataManager] Restored selection of {len(selection_before_load)} files after single file metadata loading")

            # Reset preserved selection after successful restoration
            self._preserved_selection = None

    def save_metadata_for_selected(self) -> None:
        """
        Save modified metadata for the currently selected file(s).
        """
        if not hasattr(self.parent_window, 'metadata_tree_view'):
            logger.warning("[MetadataManager] No metadata tree view available")
            return

        # Get all modified metadata for all files
        all_modified_metadata = self.parent_window.metadata_tree_view.get_all_modified_metadata_for_files()

        if not all_modified_metadata:
            logger.info("[MetadataManager] No metadata modifications to save")
            return

        # Get selected files
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

        # Filter to only save selected files that have modifications
        files_to_save = []
        for file_item in selected_files:
            if file_item.full_path in all_modified_metadata:
                files_to_save.append(file_item)

        if not files_to_save:
            logger.info("[MetadataManager] No selected files have metadata modifications")
            return

        logger.info(f"[MetadataManager] Saving metadata for {len(files_to_save)} file(s)")

        # Create ExifToolWrapper instance
        from utils.exiftool_wrapper import ExifToolWrapper
        exiftool = ExifToolWrapper()

        success_count = 0
        failed_files = []

        try:
            # Save metadata for each file
            for file_item in files_to_save:
                modified_metadata = all_modified_metadata.get(file_item.full_path, {})
                if not modified_metadata:
                    continue

                logger.info(f"[MetadataManager] Saving metadata for: {file_item.filename}")

                # Write metadata to file
                success = exiftool.write_metadata(file_item.full_path, modified_metadata)

                if success:
                    logger.info(f"[MetadataManager] Successfully saved metadata to: {file_item.filename}")
                    success_count += 1

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
                else:
                    logger.error(f"[MetadataManager] Failed to save metadata to: {file_item.filename}")
                    failed_files.append(file_item.filename)

            # Show result message
            if success_count > 0:
                from utils.dialog_utils import show_info_message
                if failed_files:
                    message = f"Successfully saved metadata for {success_count} file(s).\n\nFailed files:\n" + "\n".join(failed_files)
                    show_info_message(self.parent_window, "Metadata Save Results", message)
                else:
                    if success_count == 1:
                        message = f"Successfully saved metadata changes to:\n{files_to_save[0].filename}"
                    else:
                        message = f"Successfully saved metadata changes to {success_count} files."
                    show_info_message(self.parent_window, "Metadata Saved", message)
            elif failed_files:
                from utils.dialog_utils import show_error_message
                show_error_message(
                    self.parent_window,
                    "Save Failed",
                    f"Failed to save metadata changes to:\n" + "\n".join(failed_files)
                )

        finally:
            exiftool.close()

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
