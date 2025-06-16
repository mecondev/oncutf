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

    def start_metadata_scan(self, file_paths: List[str]) -> None:
        """
        Initiates the metadata scan process for the given file paths.

        Args:
            file_paths: List of file paths to scan for metadata
        """
        logger.warning("[DEBUG] start_metadata_scan CALLED")
        logger.debug(f"[MetadataScan] Launch with force_extended = {self.force_extended_metadata}")

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
            metadata_cache=metadata_cache,
            parent=self.parent_window  # gives access to model for direct FileItem metadata assignment
        )

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

    def start_metadata_scan_for_items(self, items: List[FileItem], use_extended: bool = False) -> None:
        """
        Initiates the metadata scan process for the given FileItem objects.

        Args:
            items: List of FileItem objects to scan
            use_extended: Whether to load extended metadata (default: False)
        """
        logger.info(f"[MetadataManager] Starting metadata scan for {len(items)} items")

        # Set the extended metadata flag before starting scan
        self.force_extended_metadata = use_extended
        if self.parent_window:
            self.parent_window.force_extended_metadata = use_extended

        file_paths = [item.full_path for item in items]

        # Use wait_cursor without restoring it, so cursor remains as wait during dialog display
        with wait_cursor(restore_after=False):
            self.start_metadata_scan(file_paths)

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

        if self.loading_dialog:
            self.loading_dialog.close()

        # Always restore the cursor when metadata loading is finished
        QApplication.restoreOverrideCursor()
        logger.debug("[MetadataManager] Cursor explicitly restored after metadata task.")

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

    def cancel_metadata_loading(self) -> None:
        """
        Cancels the metadata loading process and ensures the thread is properly terminated.
        """
        logger.info("[MetadataManager] Cancelling metadata loading")

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

    def load_metadata_for_items(
        self,
        items: List[FileItem],
        use_extended: bool = False,
        source: str = "unknown"
    ) -> None:
        """
        Simplified method for loading metadata - always works, no complex logic.

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

        # Get required components from parent window
        metadata_cache = getattr(self.parent_window, 'metadata_cache', None)
        metadata_loader = getattr(self.parent_window, 'metadata_loader', None)

        if not metadata_cache or not metadata_loader:
            logger.error("[MetadataManager] Missing metadata_cache or metadata_loader from parent window")
            return

        # Check if metadata is already loaded and of the right type
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
            # Display the existing metadata for target file
            metadata = target_file.metadata or metadata_cache.get(target_file.full_path)
            if (self.parent_window and
                hasattr(self.parent_window, 'metadata_tree_view') and
                hasattr(self.parent_window.metadata_tree_view, 'display_metadata')):
                self.parent_window.metadata_tree_view.display_metadata(metadata, context=f"existing_{source}")
            if self.parent_window and hasattr(self.parent_window, 'set_status'):
                self.parent_window.set_status(f"Metadata already loaded for {target_file.filename}.", color="green", auto_reset=True)
            return

        # Check for large files if extended metadata was requested
        if (use_extended and self.parent_window and
            hasattr(self.parent_window, 'dialog_manager') and
            not self.parent_window.dialog_manager.confirm_large_files(needs_loading)):
            return

        # Set extended metadata flag (sync with parent window)
        self.force_extended_metadata = use_extended
        if self.parent_window:
            self.parent_window.force_extended_metadata = use_extended

        # If we need to load data, proceed with actual loading
        if needs_loading:
            # Decide whether to show dialog or simple wait_cursor
            if len(needs_loading) > 1:
                # Load with dialog (CompactWaitingWidget) for multiple files
                logger.info(f"[{source}] Loading metadata for {len(needs_loading)} files with dialog (extended={use_extended})")
                self.start_metadata_scan_for_items(needs_loading, use_extended)
            else:
                # Simple loading with wait_cursor for a single file
                logger.info(f"[{source}] Loading metadata for single file with wait_cursor (extended={use_extended})")
                with wait_cursor():
                    metadata_loader.load(
                        needs_loading,
                        force=False,
                        cache=metadata_cache,
                        use_extended=use_extended
                    )

                # Always display metadata for the target file (last in list)
                metadata = target_file.metadata or metadata_cache.get(target_file.full_path)
                if (self.parent_window and
                    hasattr(self.parent_window, 'metadata_tree_view') and
                    hasattr(self.parent_window.metadata_tree_view, 'display_metadata')):
                    self.parent_window.metadata_tree_view.display_metadata(metadata, context=source)

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

        if modifiers == Qt.NoModifier:
            modifiers = QApplication.keyboardModifiers()  # fallback to current

        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)

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

        ctrl = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)
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
            # Use unified dialog-based loading for consistency
            self.start_metadata_scan_for_items(selected, use_extended=False)

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
            # Use unified dialog-based loading for consistency
            self.start_metadata_scan_for_items(selected, use_extended=True)
