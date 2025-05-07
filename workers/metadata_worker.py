"""
Module: metadata_worker.py

Author: Michael Economou
Date: 2025-05-01

This module defines a worker thread or task responsible for retrieving
metadata from files asynchronously. It decouples metadata extraction
from the UI thread to keep the application responsive.

Typically used in the ReNExif application to run exiftool or similar
metadata extractors in the background and emit signals when data is ready.

Features:
- Threaded metadata reading
- Signal-based communication with UI
- Error handling and progress updates
"""


from PyQt5.QtCore import QObject, pyqtSignal, QThread
from utils.metadata_reader import MetadataReader

class MetadataWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            metadata = MetadataReader.read_metadata(self.file_path)
            self.finished.emit(metadata)
        except Exception as e:
            self.error.emit(str(e))
