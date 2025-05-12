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

    def apply(self, file_item) -> str:
        return self.apply_from_data(self.get_data(), file_item)

    @staticmethod
    def apply_from_data(data: dict, file_item, index: int = 0) -> str:
        """
        Static method to extract metadata field from file_item based on selected config.

        :param data: Dict with field type
        :param file_item: FileItem with .date or .metadata attributes
        :param index: Unused, placeholder for future batch awareness
        :return: A string to use in the filename
        """
        field = data.get("field", "date")

        if field == "date":
            date_str = None

            if hasattr(file_item, "date") and file_item.date:
                date_str = file_item.date
            elif hasattr(file_item, "metadata"):
                metadata = getattr(file_item, "metadata", {})
                logger.debug(f"[MetadataModule] Metadata keys: {list(metadata.keys())}")
                for key in ["FileModifyDate", "FileAccessDate", "DateTimeOriginal"]:
                    if key in metadata:
                        date_str = metadata[key]
                        logger.debug(f"[MetadataModule] Found date '{date_str}' from key '{key}'")
                        break

            logger.debug(f"[MetadataModule] file: {getattr(file_item, 'filename', 'N/A')}")
            logger.debug(f"[MetadataModule] .date: {getattr(file_item, 'date', None)}")
            logger.debug(f"[MetadataModule] metadata keys: {list(getattr(file_item, 'metadata', {}).keys())}")
            logger.debug(f"[MetadataModule] selected field: {field}")

            if date_str:
                cleaned = date_str.split("+")[0].strip()
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y:%m:%d %H:%M:%S"):
                    try:
                        dt = datetime.strptime(cleaned, fmt)
                        result = dt.strftime("%Y%m%d")
                        logger.debug(f"[MetadataModule] final result: {result}")
                        return result
                    except ValueError:
                        continue

                logger.warning(f"[MetadataModule] Failed to parse date: {date_str}")
                return "invalid_date"

        logger.warning("[MetadataModule] Unknown or unsupported field: %s", field)
        return "unknown"
