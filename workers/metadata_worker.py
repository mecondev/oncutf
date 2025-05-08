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
"""

import time
import os
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from utils.metadata_reader import MetadataReader

# initialize logger
from logger_helper import get_logger
logger = get_logger(__name__)


class MetadataWorker(QObject):
    finished = pyqtSignal(dict)  # emits {filename: metadata}
    progress = pyqtSignal(int, int)

    def __init__(self, reader: MetadataReader, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.reader = reader
        self.files = []

    def load_batch(self, files) -> None:
        """
        Initializes the batch loading of metadata for the provided list of files.

        Args:
            files (list): A list of file paths for which metadata should be retrieved.
        """
        logger.debug("Batch loaded: %d files", len(files))

        self.files = files
        QTimer.singleShot(0, self.run_batch)

    def run_batch(self) -> None:
        """
        Runs the batch metadata extraction in the background.

        This method is executed in its own thread and emits signals
        to the main thread to report progress and signal completion.

        :return: None
        """

        start_time = time.time()

        logger.info("Metadata batch run started for %d files", len(self.files))

        result = {}
        total = len(self.files)

        for i, path in enumerate(self.files):
            logger.debug("Reading metadata for: %s", path)

            try:
                metadata = self.reader.read_metadata(path)
                result[os.path.basename(path)] = metadata
            except Exception as e:
                logger.warning("Failed to read metadata for %s: %s", path, e)
                result[os.path.basename(path)] = {}

            self.progress.emit(i + 1, total)

        duration = time.time() - start_time
        logger.info("Metadata batch completed in %.2f seconds", duration)

        self.finished.emit(result)
