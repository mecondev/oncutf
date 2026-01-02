"""Module: hash_loading_service.py

Author: Michael Economou
Date: 2026-01-02

Hash Loading Service for Metadata System

Handles hash loading operations including:
- Worker lifecycle management
- Progress dialog management
- UI updates on hash completion
- Cancellation support

Extracted from UnifiedMetadataManager to improve separation of concerns.
"""

from typing import TYPE_CHECKING, Any, Callable

from PyQt5.QtCore import Qt

from oncutf.models.file_item import FileItem
from oncutf.utils.filesystem.path_utils import paths_equal
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.core.hash.parallel_hash_worker import ParallelHashWorker
    from oncutf.core.metadata.metadata_cache_service import MetadataCacheService
    from oncutf.utils.ui.progress_dialog import ProgressDialog

logger = get_cached_logger(__name__)


class HashLoadingService:
    """Service for hash loading operations.

    Responsibilities:
    - Orchestrate hash loading for multiple files
    - Manage progress dialog for hash operations
    - Handle worker lifecycle
    - Update UI on hash completion
    - Support cancellation
    """

    def __init__(self, parent_window, cache_service: "MetadataCacheService"):
        """Initialize HashLoadingService.

        Args:
            parent_window: Parent window reference for UI operations
            cache_service: Cache service for checking cached hashes
        """
        self.parent_window = parent_window
        self._cache_service = cache_service
        self._currently_loading: set[str] = set()
        self._hash_worker: "ParallelHashWorker | None" = None
        self._hash_progress_dialog: "ProgressDialog | None" = None
        self._on_finished_callback: Callable[[], None] | None = None

    def load_hashes_for_files(
        self, files: list[FileItem], source: str = "user_request", on_finished_callback=None
    ) -> None:
        """Load hashes for files that don't have them cached.

        Args:
            files: List of files to load hashes for
            source: Source of the request (for logging)
            on_finished_callback: Optional callback when loading finishes
        """
        if not files:
            return

        # Store callback for later
        self._on_finished_callback = on_finished_callback

        # Filter files that need loading
        files_to_load = []
        for file_item in files:
            if file_item.full_path not in self._currently_loading:
                cached = self._cache_service.check_cached_hash(file_item)
                if not cached:
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

            from oncutf.utils.ui.progress_dialog import ProgressDialog

            self._hash_progress_dialog = ProgressDialog.create_hash_dialog(
                self.parent_window, cancel_callback=cancel_hash_loading
            )
            dialog = self._hash_progress_dialog  # Local ref for type narrowing

            if self._hash_worker and dialog:
                self._hash_worker.progress_updated.connect(
                    lambda current, total, _: dialog.update_progress(current, total)
                )
                self._hash_worker.size_progress.connect(
                    lambda processed, total: dialog.update_progress(
                        processed_bytes=processed, total_bytes=total
                    )
                )

            if dialog:
                dialog.show()
            self._start_hash_loading(files, source)

        except Exception:
            logger.exception("[HashLoadingService] Error showing hash progress dialog")
            if hasattr(self, "_hash_progress_dialog") and self._hash_progress_dialog:
                self._hash_progress_dialog.close()
                self._hash_progress_dialog = None
            self._start_hash_loading(files, source)

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
        cast("Any", self._hash_worker.progress_updated).connect(
            lambda current, total, _: self._on_hash_progress(current, total), Qt.QueuedConnection
        )

        self._hash_worker.start()

    def _on_hash_progress(self, current: int, total: int) -> None:
        """Handle hash loading progress updates.

        Args:
            current: Current file index
            total: Total files
        """
        # Progress dialog handles this via connected signals

    def _on_file_hash_calculated(self, file_path: str, hash_value: str = "") -> None:
        """Handle individual file hash calculated.

        Note:
            Hash is already stored in cache by calculate_hash() — no need to store again

        Args:
            file_path: Path to file
            hash_value: Calculated hash (unused, already in cache)
        """
        self._currently_loading.discard(file_path)

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
