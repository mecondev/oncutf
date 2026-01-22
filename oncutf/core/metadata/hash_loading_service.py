"""Module: hash_loading_service.py

Author: Michael Economou
Date: 2026-01-02 (Updated: 2026-01-15)

Unified Hash Loading Service

Handles all hash loading operations including:
- Worker lifecycle management
- Progress dialog management
- UI updates on hash completion
- Cancellation support
- Duplicate detection
- External folder comparison
- Checksum calculation

Refactored 2026-01-15: Consolidated from HashWorkerCoordinator to provide
unified callback architecture for all hash operations.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Optional

from PyQt5.QtCore import Qt

from oncutf.config import STATUS_COLORS
from oncutf.models.file_item import FileItem
from oncutf.utils.filesystem.path_utils import paths_equal
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.core.hash.parallel_hash_worker import ParallelHashWorker
    from oncutf.core.metadata.metadata_cache_service import MetadataCacheService
    from oncutf.utils.ui.progress_dialog import ProgressDialog

logger = get_cached_logger(__name__)


class HashLoadingService:
    """Unified service for all hash loading operations.

    Responsibilities:
    - Orchestrate hash loading for multiple files
    - Manage progress dialog for hash operations
    - Handle worker lifecycle
    - Update UI on hash completion
    - Support cancellation
    - Support custom callbacks for advanced operations
    - Duplicate detection (find files with matching hashes)
    - External folder comparison (compare with external files)
    - Checksum calculation and display
    """

    def __init__(self, parent_window, cache_service: Optional["MetadataCacheService"] = None):
        """Initialize HashLoadingService.

        Args:
            parent_window: Parent window reference for UI operations
            cache_service: Cache service for checking cached hashes (optional)
        """
        self.parent_window = parent_window
        self._cache_service = cache_service
        self._currently_loading: set[str] = set()
        self._hash_worker: ParallelHashWorker | None = None
        self._hash_progress_dialog: ProgressDialog | None = None

        # Callbacks for basic hash loading
        self._on_finished_callback: Callable[[], None] | Callable[[bool], None] | None = None
        self._on_file_hash_callback: Callable[[str, str, int], None] | None = None
        self._on_progress_callback: Callable[[int, int, str], None] | None = None

        # Callbacks for advanced operations
        self._on_duplicates_callback: Callable[[dict[str, Any], str], None] | None = None
        self._on_comparison_callback: Callable[[dict[str, Any], str], None] | None = None
        self._on_checksums_callback: Callable[[dict[str, Any]], None] | None = None
        self._on_error_callback: Callable[[str], None] | None = None

        # Operation state
        self._operation_type: str | None = None
        self._operation_cancelled = False
        self._operation_start_time: float | None = None
        self._total_size: int = 0
        self._operation_scope: str = "all"  # For duplicate detection context
        self._external_folder: str | None = None  # For compare operation

    def load_hashes_for_files(
        self,
        files: list[FileItem],
        source: str = "user_request",
        on_finished_callback=None,
        on_file_hash_callback=None,
        on_progress_callback=None,
    ) -> None:
        """Load hashes for files that don't have them cached.

        Args:
            files: List of files to load hashes for
            source: Source of the request (for logging)
            on_finished_callback: Optional callback when loading finishes
            on_file_hash_callback: Optional callback(path, hash, size) for each file
            on_progress_callback: Optional callback(current, total, message) for progress updates
        """
        if not files:
            return

        # Store callbacks for later
        self._on_finished_callback = on_finished_callback
        self._on_file_hash_callback = on_file_hash_callback
        self._on_progress_callback = on_progress_callback

        # Filter files that need loading
        files_to_load = []
        for file_item in files:
            if file_item.full_path not in self._currently_loading:
                # Skip cache check if no cache service (used by HashOperationsManager)
                if self._cache_service:
                    cached = self._cache_service.check_cached_hash(file_item)
                    if cached:
                        continue
                files_to_load.append(file_item)
                self._currently_loading.add(file_item.full_path)

        if not files_to_load:
            logger.info(
                "[HashLoadingService] All %d files already have cached hashes",
                len(files),
            )
            return

        logger.info(
            "[HashLoadingService] Loading hashes for %d files (%s)",
            len(files_to_load),
            source,
        )

        # Show progress dialog for multiple files
        if len(files_to_load) > 1:
            self._show_hash_progress_dialog(files_to_load, source)
        else:
            self._start_hash_loading(files_to_load, source)

    def _show_hash_progress_dialog(self, files: list[FileItem], source: str) -> None:
        """Show progress dialog for hash loading.

        Args:
            files: Files being processed
            source: Source of the request
        """
        try:

            def cancel_hash_loading():
                self.cancel_loading()

            from oncutf.app.services import create_hash_dialog

            self._hash_progress_dialog = create_hash_dialog(
                self.parent_window, cancel_callback=cancel_hash_loading
            )
            dialog = self._hash_progress_dialog  # Local ref for type narrowing

            # Set initial status and start tracking (even with 0 size to init labels)
            dialog.set_status("Calculating hash...")
            dialog.start_progress_tracking(0)

            # Start worker FIRST, then connect signals (worker is created in _start_hash_loading)
            self._start_hash_loading(files, source)

            if self._hash_worker and dialog:
                from typing import cast

                cast("Any", self._hash_worker.progress_updated).connect(
                    lambda current, total, filename: self._update_hash_dialog(
                        dialog, current, total, filename
                    ),
                    Qt.QueuedConnection,
                )
                cast("Any", self._hash_worker.size_progress).connect(
                    lambda processed, total: dialog.update_progress(
                        processed_bytes=processed, total_bytes=total
                    ),
                    Qt.QueuedConnection,
                )
                # Connect status updates from worker (e.g. "Calculating total size...")
                if hasattr(self._hash_worker, "status_updated"):
                    cast("Any", self._hash_worker.status_updated).connect(
                        dialog.set_status,
                        Qt.QueuedConnection,
                    )

            if dialog:
                dialog.show()

        except Exception:
            logger.exception("[HashLoadingService] Error showing hash progress dialog")
            if hasattr(self, "_hash_progress_dialog") and self._hash_progress_dialog:
                self._hash_progress_dialog.close()
                self._hash_progress_dialog = None
            self._start_hash_loading(files, source)

    def _update_hash_dialog(
        self, dialog: "ProgressDialog", current: int, total: int, filename: str
    ) -> None:
        """Update hash progress dialog with current progress.

        Args:
            dialog: Progress dialog to update
            current: Current file index
            total: Total files
            filename: Current filename being processed
        """
        # Update progress with named arguments (like metadata does)
        dialog.update_progress(file_count=current, total_files=total)
        # Update count label separately
        dialog.set_count(current, total)
        # Update filename if available
        if filename:
            dialog.set_filename(filename)

        # Call custom progress callback if provided
        if self._on_progress_callback:
            self._on_progress_callback(current, total, filename)

    def _start_hash_loading(self, files: list[FileItem], _source: str) -> None:
        """Start hash loading using parallel hash worker.

        Args:
            files: Files to process
            _source: Source of request (unused, for logging)
        """
        if not files:
            return

        from oncutf.core.hash.parallel_hash_worker import ParallelHashWorker

        file_paths = [f.full_path for f in files]
        self._hash_worker = ParallelHashWorker(parent=self.parent_window)
        self._hash_worker.setup_checksum_calculation(file_paths)

        from typing import cast

        cast("Any", self._hash_worker.file_hash_calculated).connect(
            self._on_file_hash_calculated, Qt.QueuedConnection
        )
        cast("Any", self._hash_worker.finished_processing).connect(
            lambda _: self._on_hash_finished(), Qt.QueuedConnection
        )

        self._hash_worker.start()

    def _on_file_hash_calculated(self, file_path: str, hash_value: str = "") -> None:
        """Handle individual file hash calculated.

        Note:
            Hash is already stored in cache by calculate_hash() — no need to store again

        Args:
            file_path: Path to file
            hash_value: Calculated hash value
        """
        self._currently_loading.discard(file_path)

        # Call custom callback if provided
        if self._on_file_hash_callback:
            import os

            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            self._on_file_hash_callback(file_path, hash_value, file_size)

        # Progressive UI update
        if self.parent_window and hasattr(self.parent_window, "file_model"):
            if hasattr(self.parent_window.file_model, "refresh_icon_for_file"):
                self.parent_window.file_model.refresh_icon_for_file(file_path)
            else:
                try:
                    for i, file in enumerate(self.parent_window.file_model.files):
                        if paths_equal(file.full_path, file_path):
                            top_left = self.parent_window.file_model.index(i, 0)
                            bottom_right = self.parent_window.file_model.index(
                                i, self.parent_window.file_model.columnCount() - 1
                            )
                            self.parent_window.file_model.dataChanged.emit(
                                top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole]
                            )
                            break
                except Exception:
                    pass

            # Force immediate UI update to show out-of-order completion
            from oncutf.core.pyqt_imports import QApplication

            QApplication.processEvents()

    def _on_hash_finished(self) -> None:
        """Handle hash loading completion."""
        self._cleanup_hash_worker()

        # Call stored callback if provided
        if hasattr(self, "_on_finished_callback") and self._on_finished_callback:
            self._on_finished_callback()

        # UI refresh
        if self.parent_window:
            if hasattr(self.parent_window, "file_model"):
                self.parent_window.file_model.refresh_icons()
            if (
                hasattr(self.parent_window, "preview_manager")
                and self.parent_window.preview_manager
            ):
                self.parent_window.preview_manager.on_hash_calculation_completed()

        logger.info("[HashLoadingService] Hash loading completed")

    def cancel_loading(self) -> None:
        """Cancel current hash loading operation."""
        if hasattr(self, "_hash_worker") and self._hash_worker:
            self._hash_worker.cancel()
            logger.info("[HashLoadingService] Hash loading cancelled")

    def _cleanup_hash_worker(self) -> None:
        """Clean up hash worker."""
        if hasattr(self, "_hash_worker") and self._hash_worker:
            if self._hash_worker.isRunning():
                if not self._hash_worker.wait(3000):
                    self._hash_worker.terminate()
                    self._hash_worker.wait(1000)
            self._hash_worker.deleteLater()
            self._hash_worker = None

    def cleanup(self) -> None:
        """Clean up resources."""
        self.cancel_loading()
        self._cleanup_hash_worker()
        self._currently_loading.clear()
        logger.info("[HashLoadingService] Cleanup completed")

    # ===== Advanced Hash Operations =====

    def start_duplicate_scan(
        self,
        file_paths: list[str],
        scope: str = "all",
        on_duplicates: Callable[[dict[str, Any], str], None] | None = None,
        on_progress: Callable[[int, int, str], None] | None = None,
        on_file_hash: Callable[[str, str, int], None] | None = None,
        on_finished: Callable[[bool], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        """Start duplicate file detection.

        Args:
            file_paths: List of file paths to scan for duplicates
            scope: Scope of the operation ("selected" or "all")
            on_duplicates: Callback(duplicates_dict, scope) when duplicates found
            on_progress: Callback(current, total, filename) for progress
            on_file_hash: Callback(path, hash, size) for each file
            on_finished: Callback(success) when operation completes
            on_error: Callback(error_message) on error
        """
        self._operation_type = "duplicates"
        self._operation_scope = scope
        self._operation_cancelled = False
        self._on_duplicates_callback = on_duplicates
        self._on_progress_callback = on_progress
        self._on_file_hash_callback = on_file_hash
        self._on_finished_callback = on_finished
        self._on_error_callback = on_error

        self._start_operation(file_paths, "duplicates")

    def start_external_comparison(
        self,
        file_paths: list[str],
        external_folder: str,
        on_comparison: Callable[[dict[str, Any], str], None] | None = None,
        on_progress: Callable[[int, int, str], None] | None = None,
        on_file_hash: Callable[[str, str, int], None] | None = None,
        on_finished: Callable[[bool], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        """Start external folder comparison.

        Args:
            file_paths: List of file paths to compare
            external_folder: External folder path to compare against
            on_comparison: Callback(results_dict, external_folder) with comparison results
            on_progress: Callback(current, total, filename) for progress
            on_file_hash: Callback(path, hash, size) for each file
            on_finished: Callback(success) when operation completes
            on_error: Callback(error_message) on error
        """
        self._operation_type = "compare"
        self._external_folder = external_folder
        self._operation_cancelled = False
        self._on_comparison_callback = on_comparison
        self._on_progress_callback = on_progress
        self._on_file_hash_callback = on_file_hash
        self._on_finished_callback = on_finished
        self._on_error_callback = on_error

        self._start_operation(file_paths, "compare", external_folder=external_folder)

    def start_checksum_calculation(
        self,
        file_paths: list[str],
        on_checksums: Callable[[dict[str, Any]], None] | None = None,
        on_progress: Callable[[int, int, str], None] | None = None,
        on_file_hash: Callable[[str, str, int], None] | None = None,
        on_finished: Callable[[bool], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        """Start checksum calculation and display.

        Args:
            file_paths: List of file paths to calculate checksums for
            on_checksums: Callback(checksums_dict) with results
            on_progress: Callback(current, total, filename) for progress
            on_file_hash: Callback(path, hash, size) for each file
            on_finished: Callback(success) when operation completes
            on_error: Callback(error_message) on error
        """
        self._operation_type = "checksums"
        self._operation_cancelled = False
        self._on_checksums_callback = on_checksums
        self._on_progress_callback = on_progress
        self._on_file_hash_callback = on_file_hash
        self._on_finished_callback = on_finished
        self._on_error_callback = on_error

        self._start_operation(file_paths, "checksums")

    def _start_operation(
        self,
        file_paths: list[str],
        operation: str,
        external_folder: str | None = None,
    ) -> None:
        """Start a hash operation with worker thread and progress dialog.

        Args:
            file_paths: List of file paths to process
            operation: Operation type ("duplicates", "compare", "checksums")
            external_folder: External folder path (for compare operation only)
        """
        import time

        from oncutf.core.hash.parallel_hash_worker import ParallelHashWorker
        from oncutf.utils.filesystem.file_size_calculator import calculate_files_total_size

        self._operation_start_time = time.time()

        # Create worker thread
        self._hash_worker = ParallelHashWorker(parent=self.parent_window)

        # Setup worker based on operation type
        if operation == "duplicates":
            self._hash_worker.setup_duplicate_scan(file_paths)
        elif operation == "compare":
            self._hash_worker.setup_external_comparison(file_paths, external_folder or "")
        elif operation == "checksums":
            self._hash_worker.setup_checksum_calculation(file_paths)

        # Connect progress signals
        from typing import cast

        cast("Any", self._hash_worker.progress_updated).connect(
            self._on_operation_progress, Qt.QueuedConnection
        )
        cast("Any", self._hash_worker.size_progress).connect(
            self._on_size_progress, Qt.QueuedConnection
        )
        cast("Any", self._hash_worker.file_hash_calculated).connect(
            self._on_operation_file_hash, Qt.QueuedConnection
        )

        # Connect result signals
        if operation == "duplicates":
            cast("Any", self._hash_worker.duplicates_found).connect(
                self._on_duplicates_result, Qt.QueuedConnection
            )
        elif operation == "compare":
            cast("Any", self._hash_worker.comparison_result).connect(
                self._on_comparison_result, Qt.QueuedConnection
            )
        elif operation == "checksums":
            cast("Any", self._hash_worker.checksums_calculated).connect(
                self._on_checksums_result, Qt.QueuedConnection
            )

        # Connect completion and error signals
        if hasattr(self._hash_worker, "finished_processing"):
            cast("Any", self._hash_worker.finished_processing).connect(
                self._on_operation_finished, Qt.QueuedConnection
            )
        cast("Any", self._hash_worker.error_occurred).connect(
            self._on_operation_error, Qt.QueuedConnection
        )

        # Create progress dialog
        self._create_operation_progress_dialog(operation, len(file_paths))

        # Calculate total size for progress tracking
        try:
            self._total_size = calculate_files_total_size(file_paths)
        except Exception:
            self._total_size = 0

        # Start worker
        self._hash_worker.start()

        logger.info(
            "[HashLoadingService] Started %s operation for %d files",
            operation,
            len(file_paths),
        )

    def _create_operation_progress_dialog(self, operation: str, file_count: int) -> None:
        """Create and show a progress dialog for hash operations.

        Args:
            operation: Type of operation for dialog title
            file_count: Number of files being processed
        """
        from oncutf.app.services import create_hash_dialog

        self._hash_progress_dialog = create_hash_dialog(
            self.parent_window,
            cancel_callback=self._cancel_operation,
            use_size_based_progress=True,
        )

        dialog = self._hash_progress_dialog
        if not dialog:
            return

        # Initialize status + tracking
        dialog.set_status("Calculating hash...")
        dialog.set_count(0, file_count)
        dialog.start_progress_tracking(self._total_size)

        # Connect status updates from worker
        if self._hash_worker and hasattr(self._hash_worker, "status_updated"):
            from typing import cast

            cast("Any", self._hash_worker.status_updated).connect(
                dialog.set_status, Qt.QueuedConnection
            )

        dialog.show()

    def _cancel_operation(self) -> None:
        """Cancel the current operation."""
        logger.info("[HashLoadingService] User cancelled operation")
        self._operation_cancelled = True

        if self._hash_worker:
            self._hash_worker.cancel()

        if hasattr(self.parent_window, "set_status"):
            self.parent_window.set_status(
                "Hash operation cancelled",
                color=STATUS_COLORS["no_action"],
                auto_reset=True,
            )

    def _on_operation_progress(self, current: int, total: int, filename: str) -> None:
        """Handle operation progress update.

        Args:
            current: Current progress value
            total: Total progress value
            filename: Current filename being processed
        """
        if self._hash_progress_dialog:
            self._hash_progress_dialog.set_count(current, total)
            self._hash_progress_dialog.set_filename(filename)

            # Force UI update
            from oncutf.core.pyqt_imports import QApplication

            app_instance = QApplication.instance()
            if app_instance:
                app_instance.processEvents()

        if self._on_progress_callback:
            self._on_progress_callback(current, total, filename)

    def _on_size_progress(self, current_bytes: int, total_bytes: int) -> None:
        """Handle size-based progress update.

        Args:
            current_bytes: Current bytes processed
            total_bytes: Total bytes to process
        """
        if self._hash_progress_dialog:
            self._hash_progress_dialog.update_progress(
                processed_bytes=current_bytes, total_bytes=total_bytes
            )

            # Update time info
            if self._operation_start_time:
                import time

                elapsed = time.time() - self._operation_start_time

                if current_bytes > 0 and total_bytes > 0:
                    rate = current_bytes / elapsed if elapsed > 0 else 0
                    estimated_total = total_bytes / rate if rate > 0 else 0
                else:
                    estimated_total = None

                self._hash_progress_dialog.set_time_info(elapsed, estimated_total)

            # Force UI update
            from oncutf.core.pyqt_imports import QApplication

            app_instance = QApplication.instance()
            if app_instance:
                app_instance.processEvents()

    def _on_operation_file_hash(self, file_path: str, hash_value: str = "") -> None:
        """Handle individual file hash calculated during operation.

        Args:
            file_path: Path to file
            hash_value: Calculated hash value
        """
        # Update file table view to show new hash
        if hasattr(self.parent_window, "file_table_view") and self.parent_window.file_table_view:
            try:
                from oncutf.core.application_context import get_app_context

                file_store = get_app_context().file_store
                model = self.parent_window.file_table_view.model()

                if model and file_store:
                    file_items = file_store.get_loaded_files()
                    for row, file_item in enumerate(file_items):
                        if file_item.full_path == file_path:
                            left_index = model.index(row, 0)
                            right_index = model.index(row, model.columnCount() - 1)
                            model.dataChanged.emit(left_index, right_index, [Qt.DisplayRole])

                            from oncutf.core.pyqt_imports import QApplication

                            app_instance = QApplication.instance()
                            if app_instance:
                                app_instance.processEvents()
                            break
            except Exception as e:
                logger.debug(
                    "[HashLoadingService] Could not refresh file item UI: %s",
                    e,
                    extra={"dev_only": True},
                )

        # Call custom callback
        if self._on_file_hash_callback:
            import os

            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            self._on_file_hash_callback(file_path, hash_value, file_size)

    def _on_duplicates_result(self, duplicates: dict[str, Any]) -> None:
        """Handle duplicate detection results.

        Args:
            duplicates: Dictionary with hash as key and list of file paths as value
        """
        if self._on_duplicates_callback:
            self._on_duplicates_callback(duplicates, self._operation_scope)

    def _on_comparison_result(self, results: dict[str, Any]) -> None:
        """Handle external comparison results.

        Args:
            results: Dictionary with comparison results
        """
        if self._on_comparison_callback:
            external_folder = getattr(self, "_external_folder", "")
            self._on_comparison_callback(results, external_folder or "")

    def _on_checksums_result(self, checksums: dict[str, Any]) -> None:
        """Handle checksum calculation results.

        Args:
            checksums: Dictionary with file paths and hash values
        """
        # Force restore cursor before showing results dialog
        from oncutf.app.services import force_restore_cursor

        force_restore_cursor()

        if self._on_checksums_callback:
            self._on_checksums_callback(checksums)

    def _on_operation_finished(self, success: bool) -> None:
        """Handle operation completion.

        Args:
            success: Whether the operation completed successfully
        """
        # Refresh file table icons
        if hasattr(self.parent_window, "file_model") and self.parent_window.file_model:
            if hasattr(self.parent_window.file_model, "refresh_icons"):
                self.parent_window.file_model.refresh_icons()

        # Notify preview manager
        if hasattr(self.parent_window, "preview_manager") and self.parent_window.preview_manager:
            self.parent_window.preview_manager.on_hash_calculation_completed()

        # Clean up
        self._cleanup_operation()

        # Call finished callback
        if self._on_finished_callback:
            self._on_finished_callback(success)  # type: ignore[call-arg]

        logger.info("[HashLoadingService] Operation completed (success=%s)", success)

    def _on_operation_error(self, error_message: str) -> None:
        """Handle operation error.

        Args:
            error_message: Error message from the worker
        """
        logger.error("[HashLoadingService] Operation error: %s", error_message)

        if hasattr(self.parent_window, "set_status"):
            self.parent_window.set_status(
                "Hash operation failed",
                color=STATUS_COLORS["critical_error"],
                auto_reset=True,
            )

        self._cleanup_operation()

        if self._on_error_callback:
            self._on_error_callback(error_message)

    def _cleanup_operation(self) -> None:
        """Clean up operation resources."""
        # Close dialog immediately
        if self._hash_progress_dialog:
            try:
                self._hash_progress_dialog.close()
            except Exception as e:
                logger.debug("[HashLoadingService] Error closing dialog: %s", e)
            finally:
                self._hash_progress_dialog = None

        # Clean up worker
        self._cleanup_hash_worker()

        # Reset state
        self._operation_cancelled = False
        self._operation_type = None

    def is_cancelled(self) -> bool:
        """Check if the operation was cancelled.

        Returns:
            bool: True if operation was cancelled
        """
        return self._operation_cancelled

    def reset_cancelled(self) -> None:
        """Reset the cancelled flag."""
        self._operation_cancelled = False
