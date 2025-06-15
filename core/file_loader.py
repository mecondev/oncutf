"""
file_loader.py

Author: Michael Economou
Date: 2025-05-01

File loading utilities with progress feedback.
Handles both synchronous and asynchronous file loading operations.
Uses UnifiedFileWorker for consistent file loading behavior.
"""

import os
from typing import List
from PyQt5.QtWidgets import QApplication

from models.file_item import FileItem
from config import ALLOWED_EXTENSIONS
from utils.cursor_helper import wait_cursor
from utils.logger_factory import get_cached_logger
from utils.dialog_utils import center_widget_on_parent
from widgets.compact_waiting_widget import CompactWaitingWidget
from core.unified_file_worker import UnifiedFileWorker

logger = get_cached_logger(__name__)


class FileLoader:
    """
    Handles file loading operations with support for both synchronous and threaded loading.
    Provides progress feedback and cancellation support.
    Uses UnifiedFileWorker for consistent behavior across the application.
    """

    def __init__(self, parent_window=None):
        self.parent_window = parent_window
        self.worker = None
        self.waiting_widget = None
        self.loaded_files = []

    def load_files(self, path: str, recursive: bool = False) -> List[FileItem]:
        """
        Load files from the given path, optionally recursively.

        Args:
            path: Directory path to load files from
            recursive: Whether to load files from subdirectories

        Returns:
            List of FileItem objects
        """
        logger.info(f"[FileLoader] Loading files from {path} (recursive: {recursive})")

        # Check if path is a directory
        if not os.path.isdir(path):
            logger.error(f"[FileLoader] Path is not a directory: {path}")
            return []

        # Estimate folder size to decide on threading
        total_files = self._estimate_folder_size(path, recursive)
        use_threading = total_files > 1000  # Use threading for large folders

        if use_threading:
            return self._load_files_threaded(path, recursive)
        else:
            return self._load_files_sync(path, recursive)

    def _estimate_folder_size(self, path: str, recursive: bool) -> int:
        """Estimate total number of files in folder."""
        try:
            count = 0
            for root, _, files in os.walk(path):
                if not recursive and root != path:
                    continue
                count += len(files)
                if count > 1000:  # Stop counting if we know it's large
                    break
            return count
        except Exception as e:
            logger.error(f"Error estimating folder size: {str(e)}")
            return 0

    def _load_files_threaded(self, path: str, recursive: bool) -> List[FileItem]:
        """Load files using background thread with progress dialog."""
        self.loaded_files = []

        # Create unified worker
        self.worker = UnifiedFileWorker()
        self.worker.setup_scan(path, recursive=recursive)

        # Create waiting widget
        self.waiting_widget = CompactWaitingWidget(
            self.parent_window,
            bar_color="#64b5f6",  # blue
            bar_bg_color="#0a1a2a"  # darker blue bg
        )
        self.waiting_widget.set_status("Scanning files...")

        # Center the widget on parent window using utility function
        center_widget_on_parent(self.waiting_widget, self.parent_window)
        self.waiting_widget.show()

        # Connect signals
        self.worker.progress_updated.connect(self._update_progress)
        self.worker.status_updated.connect(self._update_status)
        self.worker.file_loaded.connect(self._update_filename)
        self.worker.files_found.connect(self._handle_files_found)
        self.worker.finished_scanning.connect(self._handle_finished)
        self.worker.error_occurred.connect(self._handle_error)

        # Start worker
        self.worker.start()

        # Process events to show dialog
        QApplication.processEvents()

        # Wait for completion
        self.worker.wait()
        return self.loaded_files

    def _load_files_sync(self, path: str, recursive: bool) -> List[FileItem]:
        """Load files synchronously with wait cursor."""
        with wait_cursor():
            files = []

            for root, _, filenames in os.walk(path):
                if not recursive and root != path:
                    continue

                for filename in filenames:
                    if os.path.splitext(filename)[1].lower()[1:] in ALLOWED_EXTENSIONS:
                        full_path = os.path.join(root, filename)
                        files.append(FileItem(full_path))

            return files

    def _update_progress(self, current: int, total: int):
        """Update progress dialog."""
        if self.waiting_widget:
            self.waiting_widget.set_progress(current, total)
            QApplication.processEvents()

    def _update_status(self, status: str):
        """Update status message."""
        if self.waiting_widget:
            self.waiting_widget.set_status(status)
            QApplication.processEvents()

    def _update_filename(self, filename: str):
        """Update current filename."""
        if self.waiting_widget:
            self.waiting_widget.set_filename(filename)
            QApplication.processEvents()

    def _handle_files_found(self, file_paths: List[str]):
        """Handle files found by worker - convert to FileItem objects."""
        self.loaded_files = [FileItem(path) for path in file_paths]
        logger.info(f"[FileLoader] Converted {len(file_paths)} paths to FileItem objects")

    def _handle_finished(self, success: bool):
        """Handle worker completion."""
        if self.waiting_widget:
            self.waiting_widget.close()
            self.waiting_widget = None

        if success:
            logger.info(f"[FileLoader] Successfully loaded {len(self.loaded_files)} files")
        else:
            logger.warning("[FileLoader] File loading was cancelled or failed")

    def _handle_error(self, error_msg: str):
        """Handle worker error."""
        logger.error(f"[FileLoader] Error loading files: {error_msg}")
        if self.waiting_widget:
            self.waiting_widget.close()
            self.waiting_widget = None

    def cancel_loading(self):
        """Cancel ongoing file loading operation."""
        if self.worker and self.worker.isRunning():
            logger.info("[FileLoader] Cancelling file loading")
            self.worker.cancel()
            self.worker.wait(1000)  # Wait max 1 second
