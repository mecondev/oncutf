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
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox
from PyQt5.QtCore import pyqtSignal, QTimer
from models.file_item import FileItem

# initialize logger
from logger_helper import get_logger
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
        field = self.combo.currentData()
        if not field:
            field = "date"

        return {
            "type": "metadata",
            "field": self.combo.currentData()
        }

    def apply(self, file_item) -> str:
        """
        Applies the metadata module by extracting the selected field
        from the given FileItem.

        Args:
            file_item (FileItem): The file item to rename.

        Returns:
            str: The extracted metadata value or 'unknown' if not found.
        """
        data = self.get_data()
        field = data.get("field")

        # For now we only support 'date' (i.e., last modified date)
        if field == "date" and hasattr(file_item, "date"):
            return file_item.date

        logger.warning("[MetadataModule] Unknown or unsupported field: %s", field)
        return "unknown"
