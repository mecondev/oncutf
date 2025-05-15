"""
Module: metadata_module.py

Author: Michael Economou
Date: 2025-05-04

This module provides a widget-based rename module that allows selecting
a metadata field (such as creation date, modification date, or EXIF tag)
to include in the renamed filename.

It is used in the oncutf tool to dynamically extract and apply file
metadata during batch renaming.
"""

from typing import Optional
from datetime import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox
from PyQt5.QtCore import pyqtSignal, QTimer
from models.file_item import FileItem

# initialize logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)


class MetadataModule(QWidget):
    """
    A widget that allows the user to select a metadata field to include in the filename.
    Currently supports basic fields like file modification date.
    """

    updated = pyqtSignal(object)  # Emitted when selection changes

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initializes the MetadataModule widget.

        :param parent: Optional parent widget
        """
        super().__init__(parent)

        layout = QVBoxLayout(self)

        label = QLabel("Select metadata field:")
        self.combo = QComboBox()

        # Supported metadata fields
        self.combo.addItem("Modification Date", userData="date")

        layout.addWidget(label)
        layout.addWidget(self.combo)

        self.combo.currentIndexChanged.connect(lambda _: self.updated.emit(self))

        QTimer.singleShot(0, lambda: self.updated.emit(self))
        logger.info(f"[MetadataModule] Emitting initial update with field: {self.combo.currentData()}")

    def get_data(self) -> dict:
        """
        Returns selected metadata info as dictionary for preview/generation.

        :return: Dict with metadata field type
        """
        field = self.combo.currentData() or "date"
        return {
            "type": "metadata",
            "field": field
        }

    def apply(self, file_item, index=0, metadata_cache=None) -> str:
        return self.apply_from_data(self.get_data(), file_item, index, metadata_cache)

    @staticmethod
    def apply_from_data(
        data: dict,
        file_item,
        index: int = 0,
        metadata_cache: Optional[dict] = None
    ) -> str:
        """
        Extracts a metadata-based value from the file, using the specified field.

        Parameters
        ----------
        data : dict
            Dictionary with keys:
                - 'type': 'metadata'
                - 'field': the metadata field to extract (e.g., 'date', 'Model')
        file_item : FileItem
            The file item (used for filename, direct .date, or embedded metadata).
        index : int, optional
            Index of the file in the list.
        metadata_cache : dict, optional
            Optional cache mapping file path → metadata dict.

        Returns
        -------
        str
            A stringified metadata value suitable for filenames (e.g., a formatted date).
        """

        field = data.get("field")
        path = getattr(file_item, "full_path", None) or file_item.filename
        metadata = {}

        # Try to get metadata from cache first
        if metadata_cache and path in metadata_cache:
            metadata = metadata_cache[path]
            logger.debug(f"[MetadataModule] Using cached metadata for {path}")
        elif hasattr(file_item, "metadata") and isinstance(file_item.metadata, dict):
            metadata = file_item.metadata
            logger.debug(f"[MetadataModule] Using file_item.metadata for {path}")
        else:
            logger.warning(f"[MetadataModule] No metadata found for {path}")
            return "unknown"

        # === Special case: formatted date field ===
        if field == "date":
            # Try direct .date if available
            date_str = getattr(file_item, "date", None)

            # Otherwise, fallback to metadata keys
            if not date_str and metadata:
                for key in ["FileModifyDate", "FileAccessDate", "DateTimeOriginal"]:
                    if key in metadata:
                        date_str = metadata[key]
                        logger.debug(f"[MetadataModule] Found date '{date_str}' from key '{key}'")
                        break

            if date_str:
                cleaned = date_str.split("+")[0].strip()
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y:%m:%d %H:%M:%S"):
                    try:
                        dt = datetime.strptime(cleaned, fmt)
                        result = dt.strftime("%Y%m%d")
                        logger.debug(f"[MetadataModule] Final date result: {result}")
                        return result
                    except ValueError:
                        continue

                logger.warning(f"[MetadataModule] Failed to parse date: {date_str}")
                return "invalid_date"

            logger.warning(f"[MetadataModule] No date value found for {path}")
            return "unknown"

        # === Generic metadata field ===
        value = metadata.get(field)
        if value:
            return str(value).strip()

        logger.warning(f"[MetadataModule] Field '{field}' not found in metadata for {path}")
        return "unknown"
