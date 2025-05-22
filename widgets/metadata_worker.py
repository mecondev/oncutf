"""
Module: metadata_worker.py

Author: Michael Economou
Date: 2025-05-01

This module defines a worker thread or task responsible for retrieving metadata from files asynchronously. It decouples metadata extraction from the UI thread to keep the application responsive.

Typically used in the oncutf application to run exiftool or similar metadata extractors in the background and emit signals when data is ready.

Features:

* Threaded metadata reading
* Signal-based communication with UI
* Error handling and progress updates
* Graceful cancellation support
"""

import time
import os
import traceback
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from utils.metadata_loader import MetadataLoader
from utils.metadata_cache import MetadataCache

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)



class MetadataWorker(QObject):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int, int)

    def __init__(self, *, reader: MetadataLoader, metadata_cache: MetadataCache, parent: Optional[QObject] = None):
        super().__init__(parent)
        logger.warning("[DEBUG] MetadataWorker __init__ CALLED")
        self.reader = reader
        self.file_path = []
        self.metadata_cache = metadata_cache
        self._cancelled = False
        self.use_extended = False

    def load_batch(self, file_path) -> None:
        logger.warning(f"[DEBUG] load_batch() CALLED with {len(file_path)} files")
        self.file_path = file_path
        self.run_batch()

    @pyqtSlot()
    def run_batch(self) -> None:
        logger.warning(f"[DEBUG] run_batch() STARTED with {len(self.file_path)} files")
        start_time = time.time()
        result = {}
        total = len(self.file_path)

        for index, path in enumerate(self.file_path):
            try:
                metadata = self.reader.read_metadata(path, use_extended=self.use_extended)
                filename = os.path.basename(path)

                if isinstance(metadata, dict) and metadata:
                    result[path] = metadata
                    if self.metadata_cache:
                        self.metadata_cache.set(path, metadata)
                else:
                    logger.warning(f"[Worker] No metadata found for {filename}")
                    result[path] = {}

            except Exception as e:
                logger.warning(f"[Worker] Failed to read metadata for {path}: {str(e)}")
                result[path] = {}

            logger.debug(f"[Worker] progress.emit({index + 1}, {total})")
            self.progress.emit(index + 1, total)

            if self._cancelled:
                logger.warning(f"[Worker] Cancel detected after index {index + 1} — exiting batch early.")
                break

        duration = time.time() - start_time
        avg_time = duration / (index + 1) if index + 1 else 0
        logger.info(f"[Worker] Metadata batch completed in {duration:.2f}s — avg {avg_time:.2f}s/file")
        self.finished.emit(result)

    def cancel(self) -> None:
        logger.warning("[MetadataWorker] cancel() CALLED — will cancel after current file")
        self._cancelled = True
