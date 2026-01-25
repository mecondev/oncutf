"""Module: streaming_loader.py.

Author: Michael Economou
Date: 2026-01-03

Streaming file loading for large file sets.

Handles batch loading of files to keep UI responsive when loading
large directories (>200 files). Uses QTimer to process files in chunks.
"""

from typing import Any

from oncutf.models.file_item import FileItem
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class StreamingFileLoader:
    """Handles streaming file loading for large file sets.

    For large directories (>200 files), loading all files at once can freeze
    the UI. This class loads files in batches using QTimer scheduling.
    """

    def __init__(self, parent_window: Any = None, ui_service: Any = None, batch_size: int = 100) -> None:
        """Initialize streaming loader.

        Args:
            parent_window: Parent window for accessing models
            ui_service: UI service for refresh operations
            batch_size: Number of files to load per batch

        """
        self.parent_window = parent_window
        self.ui_service = ui_service
        self._batch_size = batch_size
        self._pending_files: list[FileItem] = []
        self._loading_in_progress = False
        logger.debug("[StreamingFileLoader] Initialized (batch_size=%d)", batch_size)

    def load_files_streaming(self, items: list[FileItem], clear: bool = True) -> None:
        """Load files in batches to keep UI responsive.

        Used for large file sets (> 200 files) to prevent UI freeze.

        Args:
            items: List of FileItem objects to load
            clear: Whether to clear existing files first

        """
        logger.info(
            "[StreamingFileLoader] Starting streaming load for %d files (batch_size=%d)",
            len(items),
            self._batch_size,
        )

        # Clear existing files if requested
        if clear:
            self.parent_window.file_model.set_files([])
            self.parent_window.context.file_store.set_loaded_files([])
            self._pending_files = items.copy()
        else:
            # Merge mode: filter duplicates first
            existing_files = self.parent_window.file_model.files
            existing_paths = {f.full_path for f in existing_files}
            self._pending_files = [item for item in items if item.full_path not in existing_paths]

        self._loading_in_progress = True
        self._process_next_batch()

    def _process_next_batch(self) -> None:
        """Process next batch of files in streaming loading.

        Called recursively via QTimer to keep UI responsive.
        """
        if not self._loading_in_progress or not self._pending_files:
            # Streaming complete
            self._loading_in_progress = False
            self._pending_files = []
            logger.info("[StreamingFileLoader] Streaming load complete")
            # Final UI refresh after streaming completes
            if self.ui_service:
                try:
                    self.ui_service.refresh_ui_after_load()
                except Exception:
                    logger.debug(
                        "[StreamingFileLoader] UI refresh (stream end) failed",
                        extra={"dev_only": True},
                    )
            return

        # Take next batch
        batch = self._pending_files[: self._batch_size]
        self._pending_files = self._pending_files[self._batch_size :]

        # Add batch to model
        existing_files = self.parent_window.file_model.files
        combined_files = existing_files + batch
        self.parent_window.file_model.set_files(combined_files)
        self.parent_window.context.file_store.set_loaded_files(combined_files)

        # Update status
        loaded_count = len(combined_files)
        total_count = loaded_count + len(self._pending_files)
        logger.debug(
            "[StreamingFileLoader] Streaming progress: %d/%d files",
            loaded_count,
            total_count,
            extra={"dev_only": True},
        )

        # Update files label to show progress
        if hasattr(self.parent_window, "update_files_label"):
            self.parent_window.update_files_label()

        # Schedule next batch (5ms delay to allow UI updates)
        from oncutf.utils.shared.timer_manager import TimerType, get_timer_manager

        get_timer_manager().schedule(
            self._process_next_batch,
            delay=5,
            timer_type=TimerType.UI_UPDATE,
            timer_id="file_load_next_batch",
            consolidate=False,  # Each batch must execute independently
        )

    def cancel_loading(self) -> None:
        """Cancel streaming loading in progress."""
        if self._loading_in_progress:
            logger.info("[StreamingFileLoader] Cancelling streaming load")
            self._loading_in_progress = False
            self._pending_files = []

    def is_loading(self) -> bool:
        """Check if streaming load is in progress."""
        return self._loading_in_progress
