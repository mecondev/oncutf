"""
cancellable_file_loader.py

Author: Michael Economou
Date: 2025-06-14

Cancellable file loader with progress dialog and Esc key support.
Provides non-blocking file scanning operations.
"""

from typing import Callable, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget

from core.unified_file_worker import UnifiedFileWorker
from utils.logger_factory import get_cached_logger
from widgets.file_loading_dialog import FileLoadingDialog

logger = get_cached_logger(__name__)


class CancellableFileLoader(QObject):
    """
    Cancellable file loader with progress dialog.

    Provides non-blocking file scanning with Esc key cancellation support.
    Uses CompactWaitProgress for user feedback.
    """

    # Signals
    files_loaded = pyqtSignal(list)  # List of file paths loaded
    loading_cancelled = pyqtSignal()  # Loading was cancelled
    loading_failed = pyqtSignal(str)  # Loading failed with error message

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._parent_widget = parent
        self._worker = None
        self._progress_dialog = None
        self._completion_callback = None

    def load_files_from_folder(self,
                             folder_path: str,
                             recursive: bool = False,
                             completion_callback: Optional[Callable[[List[str]], None]] = None):
        """
        Load files from folder with progress dialog.

        Args:
            folder_path: Path to scan
            recursive: Whether to scan recursively
            completion_callback: Optional callback for completion
        """
        if self._worker and self._worker.isRunning():
            logger.warning("[CancellableFileLoader] Already loading files")
            return

        self._completion_callback = completion_callback

        # Create unified worker
        self._worker = UnifiedFileWorker(self)
        self._worker.setup_scan(folder_path, recursive=recursive)

        # Connect signals - map unified worker signals to existing methods
        self._worker.progress_updated.connect(self._on_progress_updated)
        self._worker.files_found.connect(self._on_files_found)
        self._worker.finished_scanning.connect(self._on_scanning_finished)
        self._worker.error_occurred.connect(self._on_error_occurred)

        # Create progress dialog
        operation_text = f"Scanning {'recursively' if recursive else 'folder'}: {folder_path}"
        self._progress_dialog = FileLoadingDialog(
            parent=self._parent_widget,
            operation_text=operation_text
        )

        # Connect Esc key to cancellation
        self._progress_dialog.cancelled.connect(self._cancel_loading)

        # Show progress and start worker
        self._progress_dialog.show()
        self._worker.start()

        logger.debug(f"[CancellableFileLoader] Started loading: {folder_path} (recursive={recursive})")

    def _cancel_loading(self):
        """Cancel the current loading operation."""
        if self._worker and self._worker.isRunning():
            logger.debug("[CancellableFileLoader] Cancelling file loading")
            self._worker.cancel()

            # Give worker a moment to stop gracefully
            from utils.timer_manager import schedule_cleanup
        schedule_cleanup(self._force_cleanup, 100)

    def _force_cleanup(self):
        """Force cleanup if worker doesn't stop gracefully."""
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(1000)  # Wait up to 1 second

        self._cleanup()
        self.loading_cancelled.emit()

    def _on_progress_updated(self, current: int, total: int):
        """Handle progress updates from worker."""
        if self._progress_dialog:
            # Update progress bar and text
            self._progress_dialog.set_progress(current, total)
            progress_text = f"Processing {current:,} of {total:,} items..."
            self._progress_dialog.set_status(progress_text)

    def _on_files_found(self, file_paths: List[str]):
        """Handle files found by worker."""
        logger.debug(f"[CancellableFileLoader] Files found: {len(file_paths)}")

        # Call completion callback if provided
        if self._completion_callback:
            self._completion_callback(file_paths)

        self.files_loaded.emit(file_paths)

    def _on_scanning_finished(self, success: bool):
        """Handle scanning completion."""
        logger.debug(f"[CancellableFileLoader] Scanning finished: success={success}")

        if not success and self._worker and not self._worker.is_cancelled():
            # Failed for reasons other than cancellation
            self.loading_failed.emit("File scanning failed")

        self._cleanup()

    def _on_error_occurred(self, error_message: str):
        """Handle errors from worker."""
        logger.error(f"[CancellableFileLoader] Error: {error_message}")
        self.loading_failed.emit(error_message)
        self._cleanup()

    def _cleanup(self):
        """Clean up resources."""
        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

        if self._worker:
            if self._worker.isRunning():
                self._worker.quit()
                self._worker.wait()
            self._worker.deleteLater()
            self._worker = None

        self._completion_callback = None

    def is_loading(self) -> bool:
        """Check if currently loading files."""
        return self._worker is not None and self._worker.isRunning()

    def cleanup(self):
        """Public cleanup method."""
        if self.is_loading():
            self._cancel_loading()
        else:
            self._cleanup()
