"""
file_item.py

This module defines the FileItem class, which represents a single file entry
with attributes such as filename, filetype, last modification date, and a checked
state indicating whether the file is selected for renaming. The class is used
within the FileTableModel to manage file entries in a table view.

Classes:
    FileItem: Represents a single file item in the table.

Author: Michael Economou
Date: 2025-05-01
"""
from typing import Optional

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)


class FileItem:
    """
    Represents a single file item in the table.

    Attributes:
        filename (str): The name of the file without the path.
        filetype (str): The extension/type of the file (e.g., jpg, png, mp4).
        date (str): The file's last modification date as a string.
        checked (bool): Whether the file is selected for renaming.
    """

class FileItem:
    def __init__(self, filename: str, extension: str, modified: str, full_path: Optional[str] = None):
        self.filename = filename
        self.extension = extension
        self.modified = modified
        self.full_path = full_path  # ✅ νέο πεδίο
        self.checked = True
        self.date = None
        self.metadata = {}

    @property
    def name(self) -> str:
        return self.filename
