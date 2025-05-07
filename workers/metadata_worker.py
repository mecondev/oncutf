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

from PyQt5.QtCore import QObject, pyqtSignal, QThread
from utils.metadata_reader import MetadataReader

# initialize logger
from logger_helper import get_logger
logger = get_logger(__name__)


class MetadataWorker(QObject):
    finished = pyqtSignal(dict)  # emits {filename: metadata}
    progress = pyqtSignal(int, int)

    def load_batch(self, files):
        """
        Initializes the batch loading of metadata for the provided list of files.

        Args:
            files (list): A list of file paths for which metadata should be retrieved.
        """
        logger.debug("Reading metadata for: %s", path)

        self.files = files
        QTimer.singleShot(0, self.run_batch)

    def run_batch(self):
        """
        Runs the batch metadata extraction in the background.

        This method is executed in its own thread and emits signals
        to the main thread to report progress and signal completion.

        :return: None
        """
        result = {}
        total = len(self.files)

        for i, path in enumerate(self.files):
            try:
                metadata = MetadataReader.read_metadata(path)
                result[os.path.basename(path)] = metadata
            except Exception:
                result[os.path.basename(path)] = {}

            self.progress.emit(i + 1, total)

        self.finished.emit(result)
