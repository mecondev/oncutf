"""
Module: metadata_worker.py

Author: Michael Economou
Date: 2025-05-01

This module defines a worker thread or task responsible for retrieving
metadata from files asynchronously. It decouples metadata extraction
from the UI thread to keep the application responsive.

Typically used in the oncutf application to run exiftool or similar
metadata extractors in the background and emit signals when data is ready.

Features:
- Threaded metadata reading
- Signal-based communication with UI
- Error handling and progress updates
- Graceful cancellation support
"""

import time
import os
import traceback
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from utils.metadata_reader import MetadataReader
from utils.metadata_cache import MetadataCache


# initialize logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)


class MetadataWorker(QObject):
    finished = pyqtSignal(dict)  # emits {filename: metadata}
    progress = pyqtSignal(int, int)

    def __init__(self, reader: MetadataReader, metadata_cache: MetadataCache, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.reader = reader
        self.file_path = []
        self.metadata_cache = metadata_cache
        self._cancelled = False

    def load_batch(self, file_path) -> None:
        """
        Initializes the batch loading of metadata for the provided list of files.

        Args:
            file_path (list): A list of file paths for which metadata should be retrieved.
        """
        logger.debug("Batch loaded: %d files", len(file_path))
        self.file_path = file_path

        logger.info("load_batch() called with %d files", len(file_path))
        QTimer.singleShot(0, self.run_batch)

    def run_batch(self) -> None:
        """
        Processes metadata for all provided file paths and emits the result.
        Results are cached if a metadata_cache is available.

        Emits:
            progress (int, int): Current index and total count
            finished (dict): Final metadata results per file
        """
        start_time = time.time()
        result = {}
        total = len(self.file_path)

        logger.info("Metadata batch run started for %d files", total)

        for index, path in enumerate(self.file_path):
            if self._cancelled:
                logger.warning("Metadata batch was cancelled at index %d", index)
                self.finished.emit(result)
                return
            try:
                metadata = self.reader.read_metadata(path)
                filename = os.path.basename(path)

                if isinstance(metadata, dict) and metadata:
                    result[path] = metadata
                    if self.metadata_cache:
                        self.metadata_cache.set(path, metadata)
                else:
                    logger.warning("No metadata found for %s", filename)
                    result[path] = {}

            except Exception as e:
                logger.warning("Failed to read metadata for %s: %s", path, str(e))
                result[path] = {}

            self.progress.emit(index + 1, total)

        duration = time.time() - start_time
        logger.info("Metadata batch completed in %.2f seconds", duration)

        self.finished.emit(result)

    def cancel(self) -> None:
        """
        Requests cancellation of the current batch process.
        """
        logger.warning("MetadataWorker.cancel() called — cancel flag set.")
        logger.debug("Call stack:\n%s", ''.join(traceback.format_stack()))
        self._cancelled = True
