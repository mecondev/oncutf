# workers/metadata_worker.py
# Author: Firstname Lastname
# Date: 2025-05-01
# Description: Worker thread for reading metadata from files

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
