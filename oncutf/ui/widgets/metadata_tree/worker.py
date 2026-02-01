"""Module: metadata_worker.py.

Author: Michael Economou
Date: 2025-05-09

Updated: 2025-01-31
This module defines a background worker that loads metadata from files using a MetadataLoader.
It is executed inside a thread to keep the GUI responsive during batch metadata extraction.
Features:
- Threaded metadata loading
- Signal-based progress reporting
- Safe cancellation during processing
- Optional support for extended metadata
- Integrated caching with skip logic
- Batch operations optimization for better performance
"""

import os
import threading
import time
from pathlib import Path
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

# Logger setup
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataWorker(QObject):
    """Worker class for threaded metadata extraction with batch optimization.
    Emits progress and result signals and supports graceful cancellation.

    NOTE: This worker requires an ExifToolClient to be injected via set_reader().
    The UI layer should NOT instantiate ExifToolClient directly - this should be
    done by the MetadataController.

    Attributes:
        reader: The ExifTool client instance (injected).
        metadata_cache: Cache for storing and checking metadata.
        file_path (list[str]): List of file paths to process.
        use_extended (bool): Whether to request extended metadata.

    """

    finished = pyqtSignal()
    progress = pyqtSignal(int, int)
    size_progress = pyqtSignal(int, int)  # processed_bytes, total_bytes

    # Real-time UI update signal - same as HashWorker
    file_metadata_loaded = pyqtSignal(
        str
    )  # file_path - emitted when individual file metadata is loaded

    def __init__(
        self,
        reader: Any | None = None,
        metadata_cache: Any | None = None,
        files: Any | None = None,
        use_extended: bool = False,
        parent: Any | None = None,
    ):
        """Initialize the metadata worker with files and extended metadata flag.

        Args:
            reader: ExifTool client (should be injected by controller)
            metadata_cache: Metadata cache
            files: List of FileItem objects (new style)
            use_extended: Whether to use extended metadata extraction
            parent: Parent QObject

        """
        super().__init__(parent)
        # Handle both old-style (reader, metadata_cache) and new-style (files) initialization
        if files is not None:
            # New style initialization
            self.files = files
            self.file_path = [f.full_path for f in files]
            self.reader = reader  # Must be injected by controller
            self.metadata_cache = None  # Will use cache helper
        else:
            # Old style initialization for backward compatibility
            self.files = []
            self.file_path = []
            self.reader = reader
            self.metadata_cache = metadata_cache

        self.use_extended = use_extended
        self.cancelled = False
        self._cancelled = False  # Alias for compatibility
        self.batch_operations_enabled = True

        # Initialize batch manager attributes
        self._batch_manager = None
        self._batch_operations = []
        self._enable_batching = False
        self._total_size = 0
        self._processed_size = 0

        logger.debug("[Worker] __init__ called", extra={"dev_only": True})

    def set_reader(self, reader: Any) -> None:
        """Set the ExifTool client (dependency injection).

        This should be called by the controller before running the worker.

        Args:
            reader: ExifToolClient instance

        """
        self.reader = reader
        logger.debug("[Worker] ExifTool client injected", extra={"dev_only": True})

    def set_total_size(self, total_size: int) -> None:
        """Set the total size of all files to process."""
        self._total_size = total_size
        self._processed_size = 0

    def enable_batch_operations(self, enabled: bool = True) -> None:
        """Enable or disable batch operations."""
        self.batch_operations_enabled = enabled
        logger.debug(
            "[Worker] Batch operations %s",
            "enabled" if enabled else "disabled",
            extra={"dev_only": True},
        )

    @pyqtSlot()
    def run_batch(self) -> None:
        """Executes a batch metadata extraction process in a separate thread with timing logs.

        This method:
        - Iterates over a list of file paths
        - Extracts metadata using the MetadataLoader
        - Logs time per file and total time
        - Updates the cache using batch operations for better performance
        - Emits finished signal at the end
        """
        logger.debug(
            "[Worker] run_batch() started - use_extended = %s",
            self.use_extended,
            extra={"dev_only": True},
        )
        logger.warning(
            "[Worker] run_batch() running in thread: %s",
            threading.current_thread().name,
        )

        # Ensure we have a reader (must be injected by controller)
        if not self.reader:
            logger.error(
                "[Worker] No ExifTool client provided! Worker cannot run without injected client."
            )
            self.finished.emit()
            return

        start_total = time.time()

        # Initialize batch service if enabled
        if self.batch_operations_enabled:
            logger.debug("[Worker] Batch operations enabled", extra={"dev_only": True})
            from oncutf.app.services import get_batch_service

            self._batch_manager = get_batch_service().batch_manager
            self._enable_batching = True

        try:
            total = len(self.file_path)
            for index, path in enumerate(self.file_path):
                if self._cancelled:
                    logger.warning("[Worker] Canceled before processing: %s", path)
                    break

                # Get file size for progress tracking
                try:
                    file_size = Path(path).stat().st_size
                    file_size_mb = file_size / (1024 * 1024)
                except (OSError, AttributeError):
                    file_size = 0
                    file_size_mb = 0

                start_file = time.time()
                logger.debug(
                    "[Worker] Processing file %d/%d: %s (%.2f MB)",
                    index + 1,
                    total,
                    path,
                    file_size_mb,
                    extra={"dev_only": True},
                )

                try:
                    metadata = self.reader.extract_metadata(Path(path))

                    # Get previous entry using file_status_helpers
                    from oncutf.utils.filesystem.file_status_helpers import (
                        get_metadata_cache_entry,
                    )

                    previous_extended = False
                    try:
                        previous_entry = get_metadata_cache_entry(path)
                        previous_extended = previous_entry.is_extended if previous_entry else False
                    except Exception as e:
                        logger.debug(
                            "[Worker] Cache entry error: %s",
                            e,
                            extra={"dev_only": True},
                        )

                    # Check if metadata has the extended flag directly
                    metadata_has_extended = (
                        isinstance(metadata, dict) and metadata.get("__extended__") is True
                    )

                    # Determine final extended status from all sources
                    is_extended_flag = (
                        previous_extended or self.use_extended or metadata_has_extended
                    )

                    logger.debug(
                        "[Worker] Extended metadata flags for %s:",
                        path,
                        extra={"dev_only": True},
                    )
                    logger.debug(
                        "[Worker] - Previous entry extended: %s",
                        previous_extended,
                        extra={"dev_only": True},
                    )
                    logger.debug(
                        "[Worker] - use_extended parameter: %s",
                        self.use_extended,
                        extra={"dev_only": True},
                    )
                    logger.debug(
                        "[Worker] - metadata has __extended__ flag: %s",
                        metadata_has_extended,
                        extra={"dev_only": True},
                    )
                    logger.debug(
                        "[Worker] - final extended status: %s",
                        is_extended_flag,
                        extra={"dev_only": True},
                    )

                    # Store metadata using batch operations if available
                    if self._enable_batching and self._batch_manager:
                        logger.debug(
                            "[Worker] Queuing metadata for batching: %s",
                            path,
                            extra={"dev_only": True},
                        )

                        # Queue for batch processing
                        self._batch_manager.queue_metadata_set(
                            file_path=path,
                            metadata=metadata,
                            is_extended=is_extended_flag,
                            priority=10,  # High priority for worker operations
                        )

                        # Store operation info for final flush
                        self._batch_operations.append(
                            {
                                "path": path,
                                "metadata": metadata,
                                "is_extended": is_extended_flag,
                            }
                        )
                    else:
                        # Fallback to direct cache operation
                        logger.debug(
                            "[Worker] Saving metadata directly: %s, extended = %s",
                            path,
                            is_extended_flag,
                            extra={"dev_only": True},
                        )
                        self.metadata_cache.set(path, metadata, is_extended=is_extended_flag)

                    # Emit real-time update signal for immediate UI refresh (same as HashWorker)
                    self.file_metadata_loaded.emit(path)
                    logger.debug(
                        "[Worker] Emitted file_metadata_loaded signal for: %s",
                        Path(path).name,
                        extra={"dev_only": True},
                    )

                except Exception as e:
                    logger.exception(
                        "[Worker] Exception while reading metadata for %s", path
                    )
                    metadata = {}

                # Update processed size and emit size progress
                self._processed_size += file_size
                self.size_progress.emit(self._processed_size, self._total_size)

                # Note: Real-time file item status updates are now handled via file_metadata_loaded signal

                elapsed_file = time.time() - start_file
                logger.debug(
                    "[Worker] File processed in %.2f sec",
                    elapsed_file,
                    extra={"dev_only": True},
                )

                self.progress.emit(index + 1, total)

                # Optional: check again in case cancel happened during emit delay
                if self._cancelled:
                    logger.warning("[Worker] Canceled after emit at file: %s", path)
                    break

        finally:
            # Flush any remaining batch operations
            if self._enable_batching and self._batch_manager and self._batch_operations:
                logger.info(
                    "[Worker] Flushing %d batched metadata operations",
                    len(self._batch_operations),
                )

                try:
                    # Force flush all metadata operations
                    flushed = self._batch_manager.flush_batch_type("metadata_set")
                    logger.info("[Worker] Successfully flushed %d metadata operations", flushed)

                    # Get batch statistics
                    stats = self._batch_manager.get_stats()
                    logger.info(
                        "[Worker] Batch stats: %d batched, avg batch size: %.1f, time saved: %.2fs",
                        stats.batched_operations,
                        stats.average_batch_size,
                        stats.total_time_saved,
                    )

                except Exception:
                    logger.exception("[Worker] Error flushing batch operations")

                    # Fallback: save operations individually
                    logger.warning("[Worker] Falling back to individual metadata saves")
                    for op in self._batch_operations:
                        try:
                            self.metadata_cache.set(
                                op["path"],
                                op["metadata"],
                                is_extended=op["is_extended"],
                            )
                        except Exception:
                            logger.exception(
                                "[Worker] Fallback save failed for %s",
                                op["path"],
                            )

            elapsed_total = time.time() - start_total
            logger.debug(
                "[Worker] Total time for batch: %.2f sec",
                elapsed_total,
                extra={"dev_only": True},
            )

            # Log batch optimization results
            if self._batch_operations:
                batch_count = len(self._batch_operations)
                estimated_individual_time = batch_count * 0.01  # 10ms per individual operation
                estimated_time_saved = max(
                    0, estimated_individual_time - elapsed_total * 0.1
                )  # Rough estimate
                logger.info(
                    "[Worker] Batch optimization: %d operations, estimated time saved: %.3fs",
                    batch_count,
                    estimated_time_saved,
                )

            logger.warning("[Worker] FINALLY -> emitting finished signal")
            self.finished.emit()

    def cancel(self) -> None:
        """Cancels the batch processing. Safe flag that is checked per file."""
        logger.info("[Worker] cancel() requested — will cancel after current file")
        self._cancelled = True
        self.cancelled = True  # Also set the old attribute for compatibility

        # Also flush any pending batch operations on cancellation
        if self._enable_batching and self._batch_manager and self._batch_operations:
            logger.info("[Worker] Flushing batch operations due to cancellation")
            try:
                self._batch_manager.flush_batch_type("metadata_set")
            except Exception:
                logger.exception("[Worker] Error flushing on cancellation")
