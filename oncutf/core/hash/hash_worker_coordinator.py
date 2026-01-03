"""Hash Worker Coordination Layer.

Author: Michael Economou
Date: 2026-01-04

Coordinates hash worker threads, progress dialogs, and signal connections for hash operations.
Handles cancellation and cleanup of long-running operations.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget

from oncutf.config import STATUS_COLORS
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class HashWorkerCoordinator:
    """Coordinates hash worker threads and progress dialogs.

    This class handles:
    - Creating and managing hash worker threads
    - Setting up progress dialogs with cancellation support
    - Connecting worker signals to handlers
    - Cleanup of workers and resources
    """

    def __init__(self, parent_window: QWidget) -> None:
        """Initialize the worker coordinator.

        Args:
            parent_window: Reference to the main window

        """
        self.parent_window: Any = parent_window
        self.hash_worker: Any = None
        self.hash_dialog: Any = None
        self._operation_cancelled = False

    def start_hash_operation(
        self,
        operation: str,
        file_paths: list[str],
        on_duplicates: Callable[..., None] | None = None,
        on_comparison: Callable[..., None] | None = None,
        on_checksums: Callable[..., None] | None = None,
        on_progress: Callable[..., None] | None = None,
        on_size_progress: Callable[..., None] | None = None,
        on_file_hash: Callable[..., None] | None = None,
        on_finished: Callable[..., None] | None = None,
        on_error: Callable[..., None] | None = None,
        external_folder: str | None = None,
    ) -> None:
        """Start a hash operation with worker thread and progress dialog.

        Args:
            operation: Type of operation ("duplicates", "compare", "checksums")
            file_paths: List of file paths to process
            on_duplicates: Callback for duplicate results
            on_comparison: Callback for comparison results
            on_checksums: Callback for checksum results
            on_progress: Callback for progress updates (current, total, message)
            on_size_progress: Callback for size-based progress (current_bytes, total_bytes)
            on_file_hash: Callback for individual file hash completion
            on_finished: Callback for operation completion
            on_error: Callback for errors
            external_folder: External folder path (for compare operation only)

        """
        # Reset cancellation flag
        self._operation_cancelled = False

        # Import hash worker
        from oncutf.core.hash.hash_worker import HashWorker

        # Create worker thread
        self.hash_worker = HashWorker()

        # Setup worker based on operation type
        if operation == "duplicates":
            self.hash_worker.setup_duplicate_scan(file_paths)
        elif operation == "compare":
            self.hash_worker.setup_external_comparison(file_paths, external_folder)
        elif operation == "checksums":
            self.hash_worker.setup_checksum_calculation(file_paths)

        # Connect signals for progress updates
        from oncutf.core.pyqt_imports import Qt

        if self.hash_worker and on_progress:
            self.hash_worker.progress_updated.connect(on_progress, Qt.QueuedConnection)
        if self.hash_worker and on_size_progress:
            self.hash_worker.size_progress.connect(on_size_progress, Qt.QueuedConnection)
        if self.hash_worker and on_file_hash:
            self.hash_worker.file_hash_calculated.connect(
                on_file_hash, Qt.QueuedConnection
            )

        # Connect signals for results
        if self.hash_worker and on_duplicates:
            self.hash_worker.duplicates_found.connect(on_duplicates, Qt.QueuedConnection)
        if self.hash_worker and on_comparison:
            self.hash_worker.comparison_result.connect(
                on_comparison, Qt.QueuedConnection
            )
        if self.hash_worker and on_checksums:
            self.hash_worker.checksums_calculated.connect(
                on_checksums, Qt.QueuedConnection
            )

        # Connect completion and error signals
        if self.hash_worker and on_finished:
            if hasattr(self.hash_worker, "finished_processing"):
                self.hash_worker.finished_processing.connect(
                    on_finished, Qt.QueuedConnection
                )
            else:
                self.hash_worker.finished.connect(
                    lambda: on_finished(True), Qt.QueuedConnection
                )

        if self.hash_worker and on_error:
            self.hash_worker.error_occurred.connect(on_error, Qt.QueuedConnection)

        # Create progress dialog
        self._create_hash_progress_dialog(operation, len(file_paths))

        # Start worker
        if self.hash_worker:
            self.hash_worker.start()

        logger.info(
            "[HashWorkerCoordinator] Started hash operation: %s for %d files",
            operation,
            len(file_paths),
        )

    def _create_hash_progress_dialog(
        self, _operation: str, file_count: int
    ) -> None:
        """Create and show a progress dialog for hash operations.

        Args:
            _operation: Type of operation for dialog title
            file_count: Number of files being processed

        """
        from oncutf.utils.ui.progress_dialog import ProgressDialog

        # Create dialog using the unified ProgressDialog for hash operations
        self.hash_dialog = ProgressDialog.create_hash_dialog(
            self.parent_window,
            cancel_callback=self._cancel_hash_operation,
            use_size_based_progress=True,
        )
        # Initialize count and show
        self.hash_dialog.set_count(0, file_count)
        self.hash_dialog.show()

    def _cancel_hash_operation(self) -> None:
        """Cancel the current hash operation."""
        logger.info("[HashWorkerCoordinator] User cancelled hash operation")

        # Set cancellation flag
        self._operation_cancelled = True

        # Tell worker to stop
        if self.hash_worker:
            self.hash_worker.cancel()

        # Update status
        if hasattr(self.parent_window, "set_status"):
            self.parent_window.set_status(
                "Hash operation cancelled",
                color=STATUS_COLORS["no_action"],
                auto_reset=True,
            )

    def update_progress(self, current: int, total: int, message: str) -> None:
        """Update operation progress in dialog.

        Args:
            current: Current progress value
            total: Total progress value
            message: Progress message to display

        """
        if hasattr(self, "hash_dialog") and self.hash_dialog:
            self.hash_dialog.set_count(current, total)
            self.hash_dialog.set_message(message)

    def update_size_progress(self, current_bytes: int, total_bytes: int) -> None:
        """Update size-based progress in dialog.

        Args:
            current_bytes: Current bytes processed
            total_bytes: Total bytes to process

        """
        if hasattr(self, "hash_dialog") and self.hash_dialog:
            # Calculate percentage
            if total_bytes > 0:
                percentage = int((current_bytes / total_bytes) * 100)
                self.hash_dialog.set_count(percentage, 100)
            else:
                self.hash_dialog.set_count(0, 100)

    def cleanup_worker(self) -> None:
        """Clean up the worker thread and dialog."""
        # Close dialog
        if hasattr(self, "hash_dialog") and self.hash_dialog:
            from oncutf.utils.shared.timer_manager import schedule_dialog_close

            schedule_dialog_close(self.hash_dialog.close, 500)

        # Clean up worker
        if hasattr(self, "hash_worker") and self.hash_worker:
            self.hash_worker.quit()
            self.hash_worker.wait()
            self.hash_worker = None

        # Reset cancellation flag
        self._operation_cancelled = False

    def is_cancelled(self) -> bool:
        """Check if the operation was cancelled.

        Returns:
            bool: True if operation was cancelled, False otherwise

        """
        return self._operation_cancelled

    def mark_cancelled(self) -> None:
        """Mark operation as cancelled."""
        self._operation_cancelled = True

    def reset_cancelled(self) -> None:
        """Reset the cancelled flag."""
        self._operation_cancelled = False
