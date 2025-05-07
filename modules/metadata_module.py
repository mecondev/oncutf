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
from PyQt5.QtCore import pyqtSignal

# initialize logger
from logger_helper import get_logger
logger = get_logger(__name__)


class MetadataModule(QWidget):
    """
    A widget that allows the user to select a metadata field to include in the filename.
    Currently supports basic fields like file modification date.
    """

    updated = pyqtSignal()  # Emitted when selection changes

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
        # Future: self.combo.addItem("EXIF Creation Date", userData="exif_create_date")

        self.combo.currentIndexChanged.connect(self.updated.emit)

        layout.addWidget(label)
        layout.addWidget(self.combo)

    def get_data(self) -> dict:
        """
        Returns selected metadata info as dictionary for preview/generation.

        :return: Dict with metadata field type
        """
        return {
            "type": "metadata",
            "field": self.combo.currentData()
        }
