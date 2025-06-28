"""
Module: metadata_worker.py

Author: Michael Economou
Updated: 2025-05-23

This module defines a background worker that loads metadata from files using a MetadataLoader.
It is executed inside a thread to keep the GUI responsive during batch metadata extraction.

Features:
- Threaded metadata loading
- Signal-based progress reporting
- Safe cancellation during processing
- Optional support for extended metadata
- Integrated caching with skip logic
"""

import os
import threading
import time
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

# Logger setup
from utils.logger_factory import get_cached_logger
from utils.metadata_loader import MetadataLoader

logger = get_cached_logger(__name__)


class MetadataWorker(QObject):
    """
    Worker class for threaded metadata extraction.
    Emits progress and result signals and supports graceful cancellation.

    Attributes:
        reader (MetadataLoader): The metadata reader instance.
        metadata_cache: Cache for storing and checking metadata.
        file_path (list[str]): List of file paths to process.
        use_extended (bool): Whether to request extended metadata.
    """

    finished = pyqtSignal()
    progress = pyqtSignal(int, int)

    def __init__(self, *, reader: MetadataLoader, metadata_cache, parent: Optional[QObject] = None):
        super().__init__(parent)
        logger.debug("[Worker] __init__ called")
        self.main_window = parent
        self.reader = reader
        self.file_path = []
        self.metadata_cache = metadata_cache
        self._cancelled = False
        self.use_extended = False

    @pyqtSlot()
    def run_batch(self) -> None:
        """
        Executes a batch metadata extraction process in a separate thread with timing logs.

        This method:
        - Iterates over a list of file paths
        - Extracts metadata using the MetadataLoader
        - Logs time per file and total time
        - Updates the cache and progress bar
        - Emits finished signal at the end
        """
        logger.debug(f"[Worker] run_batch() started — use_extended = {self.use_extended}", extra={"dev_only": True})
        logger.warning(f"[Worker] run_batch() running in thread: {threading.current_thread().name}")

        start_total = time.time()

        try:
            total = len(self.file_path)
            for index, path in enumerate(self.file_path):
                if self._cancelled:
                    logger.warning(f"[Worker] Canceled before processing: {path}")
                    break

                file_size_mb = os.path.getsize(path) / (1024 * 1024)
                start_file = time.time()
                logger.debug(f"[Worker] Processing file {index + 1}/{total}: {path} ({file_size_mb:.2f} MB)", extra={"dev_only": True})

                try:
                    metadata = self.reader.read_metadata(
                        filepath=path,
                        use_extended=self.use_extended
                    )

                    previous_entry = self.metadata_cache.get_entry(path)
                    previous_extended = previous_entry.is_extended if previous_entry else False

                    # Check if metadata has the extended flag directly
                    metadata_has_extended = isinstance(metadata, dict) and metadata.get("__extended__") is True

                    # Determine final extended status from all sources
                    is_extended_flag = previous_extended or self.use_extended or metadata_has_extended

                    logger.debug(f"[Worker] Extended metadata flags for {path}:", extra={"dev_only": True})
                    logger.debug(f"[Worker] - Previous entry extended: {previous_extended}", extra={"dev_only": True})
                    logger.debug(f"[Worker] - use_extended parameter: {self.use_extended}", extra={"dev_only": True})
                    logger.debug(f"[Worker] - metadata has __extended__ flag: {metadata_has_extended}", extra={"dev_only": True})
                    logger.debug(f"[Worker] - final extended status: {is_extended_flag}", extra={"dev_only": True})

                    logger.debug(f"[Worker] Saving metadata for {path}, extended = {is_extended_flag}", extra={"dev_only": True})
                    self.metadata_cache.set(path, metadata, is_extended=is_extended_flag)

                except Exception as e:
                    logger.exception(f"[Worker] Exception while reading metadata for {path}: {e}")
                    metadata = {}

                # Note: File item status updates are handled by the parent window
                # after metadata loading is complete

                elapsed_file = time.time() - start_file
                logger.debug(f"[Worker] File processed in {elapsed_file:.2f} sec", extra={"dev_only": True})

                self.progress.emit(index + 1, total)

                # Optional: check again in case cancel happened during emit delay
                if self._cancelled:
                    logger.warning(f"[Worker] Canceled after emit at file: {path}")
                    break

        finally:
            elapsed_total = time.time() - start_total
            logger.debug(f"[Worker] Total time for batch: {elapsed_total:.2f} sec", extra={"dev_only": True})
            logger.warning("[Worker] FINALLY → emitting finished signal")
            self.finished.emit()

    def cancel(self) -> None:
        """
        Cancels the batch processing. Safe flag that is checked per file.
        """
        logger.info("[Worker] cancel() requested — will cancel after current file")
        self._cancelled = True
