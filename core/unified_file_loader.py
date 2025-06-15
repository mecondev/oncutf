"""
unified_file_loader.py

Author: Michael Economou
Date: 2025-01-20

Unified file loading system that combines the functionality of:
- core/file_loader.py
- widgets/file_loading_dialog.py
- core/file_load_manager.py

Provides a single, comprehensive interface for all file loading operations
with support for both dialog-based and direct loading modes.
"""

import os
from typing import List, Set, Optional, Callable, Union
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget, QApplication

from core.unified_file_worker import UnifiedFileWorker
from widgets.compact_waiting_widget import CompactWaitingWidget
from widgets.file_loading_dialog import FileLoadingDialog
from utils.cursor_helper import wait_cursor
from utils.dialog_utils import center_widget_on_parent
from utils.logger_factory import get_cached_logger
from config import ALLOWED_EXTENSIONS

logger = get_cached_logger(__name__)


class UnifiedFileLoader(QObject):
    """
    Unified file loading system that handles all file loading scenarios.

    Features:
    - Automatic mode selection (dialog vs cursor) based on file count
    - Support for single files, multiple files, and directories
    - Configurable allowed extensions
    - Progress feedback with cancellation support
    - Thread-safe operations
    - Consistent UI experience across all loading types
    """

    # Signals
    files_loaded = pyqtSignal(list)  # List of file paths loaded
    loading_cancelled = pyqtSignal()  # Loading was cancelled
    loading_failed = pyqtSignal(str)  # Loading failed with error message
    progress_updated = pyqtSignal(int, int)  # current, total
    status_updated = pyqtSignal(str)  # status message

    def __init__(self, parent_window: Optional[QWidget] = None):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.worker: Optional[UnifiedFileWorker] = None
        self.waiting_widget: Optional[CompactWaitingWidget] = None
        self.loading_dialog: Optional[FileLoadingDialog] = None

        # Configuration
        self.allowed_extensions: Set[str] = set(ALLOWED_EXTENSIONS)
        self.dialog_threshold = 1000  # Show dialog for folders with >1000 estimated files

    def load_files(self,
                   paths: Union[str, List[str]],
                   recursive: bool = False,
                   allowed_extensions: Optional[Set[str]] = None,
                   force_dialog: bool = False,
                   completion_callback: Optional[Callable[[List[str]], None]] = None) -> None:
        """
        Load files from the given paths with automatic mode selection.

        Args:
            paths: Single path string or list of paths to load
            recursive: Whether to scan directories recursively
            allowed_extensions: Set of allowed file extensions (uses default if None)
            force_dialog: Force dialog mode regardless of file count
            completion_callback: Callback function called when loading completes
        """
        # Normalize paths to list
        if isinstance(paths, str):
            path_list = [paths]
        else:
            path_list = list(paths)

        # Use provided extensions or default
        extensions = allowed_extensions or self.allowed_extensions

        logger.info(f"[UnifiedFileLoader] Loading {len(path_list)} paths (recursive={recursive})")

        # Estimate total files to decide on loading mode
        estimated_files = self._estimate_total_files(path_list, recursive, extensions)
        use_dialog = force_dialog or estimated_files > self.dialog_threshold

        if use_dialog:
            self._load_with_dialog(path_list, recursive, extensions, completion_callback)
        else:
            self._load_with_cursor(path_list, recursive, extensions, completion_callback)

    def load_folder(self,
                    folder_path: str,
                    recursive: bool = False,
                    merge_mode: bool = False,
                    completion_callback: Optional[Callable[[List[str]], None]] = None) -> None:
        """
        Load files from a folder with automatic mode selection.

        Args:
            folder_path: Path to the folder to load
            recursive: Whether to scan recursively
            merge_mode: Whether to merge with existing files (affects UI clearing)
            completion_callback: Callback function called when loading completes
        """
        if not os.path.isdir(folder_path):
            logger.error(f"[UnifiedFileLoader] Path is not a directory: {folder_path}")
            self.loading_failed.emit(f"Path is not a directory: {folder_path}")
            return

        # Wrapper callback that handles merge mode
        def folder_callback(file_paths: List[str]):
            logger.info(f"[UnifiedFileLoader] Loaded {len(file_paths)} files from folder")
            if completion_callback:
                completion_callback(file_paths)
            self.files_loaded.emit(file_paths)

        self.load_files(folder_path, recursive=recursive, completion_callback=folder_callback)

    def cancel_loading(self) -> None:
        """Cancel any ongoing loading operation."""
        if self.worker and self.worker.isRunning():
            logger.info("[UnifiedFileLoader] Cancelling file loading")
            self.worker.cancel()
            self.worker.wait(2000)  # Wait max 2 seconds

        if self.waiting_widget:
            self.waiting_widget.close()
            self.waiting_widget = None

        if self.loading_dialog:
            self.loading_dialog.close()
            self.loading_dialog = None

        self.loading_cancelled.emit()

    def _estimate_total_files(self, paths: List[str], recursive: bool, extensions: Set[str]) -> int:
        """Estimate total number of files to determine loading mode."""
        total = 0

        for path in paths:
            if os.path.isfile(path):
                # Check if file has allowed extension
                _, ext = os.path.splitext(path)
                if ext.startswith('.'):
                    ext = ext[1:].lower()
                if ext in extensions:
                    total += 1
            elif os.path.isdir(path):
                try:
                    if recursive:
                        # Quick estimation for recursive scan
                        for root, _, files in os.walk(path):
                            total += len(files)
                            if total > self.dialog_threshold:
                                return total  # Early exit if we know it's large
                    else:
                        # Count files in immediate directory
                        files = os.listdir(path)
                        total += len(files)
                except (OSError, PermissionError):
                    # If we can't access, assume it's large
                    total += self.dialog_threshold + 1

        return total

    def _load_with_dialog(self,
                         paths: List[str],
                         recursive: bool,
                         extensions: Set[str],
                         completion_callback: Optional[Callable[[List[str]], None]]) -> None:
        """Load files using dialog-based progress feedback."""
        logger.debug("[UnifiedFileLoader] Using dialog mode for file loading")

        def on_files_loaded(file_paths: List[str]):
            if completion_callback:
                completion_callback(file_paths)
            self.files_loaded.emit(file_paths)

        # Create and show loading dialog
        self.loading_dialog = FileLoadingDialog(self.parent_window, on_files_loaded)
        self.loading_dialog.load_files_with_options(paths, extensions, recursive=recursive)
        self.loading_dialog.exec_()

        # Clean up
        self.loading_dialog = None

    def _load_with_cursor(self,
                         paths: List[str],
                         recursive: bool,
                         extensions: Set[str],
                         completion_callback: Optional[Callable[[List[str]], None]]) -> None:
        """Load files using cursor-based feedback for small operations."""
        logger.debug("[UnifiedFileLoader] Using cursor mode for file loading")

        with wait_cursor():
            # Create worker for background processing
            self.worker = UnifiedFileWorker()
            self.worker.setup_scan(paths, extensions, recursive)

            # Connect signals
            self.worker.files_found.connect(lambda files: self._on_files_loaded(files, completion_callback))
            self.worker.error_occurred.connect(self._on_error)
            self.worker.finished_scanning.connect(self._on_finished)

            # Start worker and wait for completion
            self.worker.start()
            self.worker.wait()  # Synchronous wait for small operations

    def _load_with_widget(self,
                         paths: List[str],
                         recursive: bool,
                         extensions: Set[str],
                         completion_callback: Optional[Callable[[List[str]], None]]) -> None:
        """Load files using standalone widget (for intermediate file counts)."""
        logger.debug("[UnifiedFileLoader] Using widget mode for file loading")

        # Create standalone waiting widget
        self.waiting_widget = CompactWaitingWidget(
            self.parent_window,
            bar_color="#64b5f6",  # blue
            bar_bg_color="#0a1a2a"  # darker blue bg
        )
        self.waiting_widget.set_status("Scanning files...")

        # Center and show widget
        center_widget_on_parent(self.waiting_widget, self.parent_window)
        self.waiting_widget.show()

        # Create and setup worker
        self.worker = UnifiedFileWorker()
        self.worker.setup_scan(paths, extensions, recursive)

        # Connect signals
        self.worker.progress_updated.connect(self._update_widget_progress)
        self.worker.status_updated.connect(self._update_widget_status)
        self.worker.file_loaded.connect(self._update_widget_filename)
        self.worker.files_found.connect(lambda files: self._on_files_loaded(files, completion_callback))
        self.worker.error_occurred.connect(self._on_error)
        self.worker.finished_scanning.connect(self._on_finished)

        # Start worker
        self.worker.start()

    def _update_widget_progress(self, current: int, total: int) -> None:
        """Update standalone widget progress."""
        if self.waiting_widget:
            self.waiting_widget.set_progress(current, total)
        self.progress_updated.emit(current, total)

    def _update_widget_status(self, status: str) -> None:
        """Update standalone widget status."""
        if self.waiting_widget:
            self.waiting_widget.set_status(status)
        self.status_updated.emit(status)

    def _update_widget_filename(self, filename: str) -> None:
        """Update standalone widget filename."""
        if self.waiting_widget:
            self.waiting_widget.set_filename(filename)

    def _on_files_loaded(self, files: List[str], completion_callback: Optional[Callable[[List[str]], None]]) -> None:
        """Handle successful file loading completion."""
        logger.info(f"[UnifiedFileLoader] Successfully loaded {len(files)} files")

        if completion_callback:
            completion_callback(files)

        self.files_loaded.emit(files)

    def _on_error(self, error_msg: str) -> None:
        """Handle loading error."""
        logger.error(f"[UnifiedFileLoader] Error loading files: {error_msg}")
        self.loading_failed.emit(error_msg)
        self._cleanup()

    def _on_finished(self, success: bool) -> None:
        """Handle worker completion."""
        logger.debug(f"[UnifiedFileLoader] Worker finished (success={success})")
        self._cleanup()

    def _cleanup(self) -> None:
        """Clean up resources after loading completion."""
        if self.waiting_widget:
            self.waiting_widget.close()
            self.waiting_widget = None

        if self.worker:
            self.worker.deleteLater()
            self.worker = None
