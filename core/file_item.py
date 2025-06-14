from datetime import datetime
from typing import Optional
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

class FileItem:
    """
    Represents a file in the application.
    Stores file metadata and handles file operations.
    """

    def __init__(self, path: str, extension: str, modified: datetime):
        self.path = path
        self.extension = extension
        self.modified = modified
        self.name = path.split('/')[-1]
        self.size = 0  # Will be updated later if needed
        self.metadata = {}  # Will store file metadata

    def __str__(self) -> str:
        return f"FileItem({self.name})"

    def __repr__(self) -> str:
        return f"FileItem(path='{self.path}', extension='{self.extension}', modified='{self.modified}')"
