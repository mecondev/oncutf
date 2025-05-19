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
import os

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
        self.combo.addItem("Last Modified (file system)", userData="last_modified")
        self.combo.addItem("Metadata: Modification Date", userData="date")

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
        field = self.combo.currentData() or "last_modified"
        return {
            "type": "metadata",
            "field": field
        }

    def apply(self, file_item, index=0, metadata_cache=None) -> str:
        return self.apply_from_data(self.get_data(), file_item, index, metadata_cache)

    @staticmethod
    def apply_from_data(data: dict,
            file_item,
            index: int = 0,
            metadata_cache: dict = None
        ) -> str:
        """
        Extracts a metadata value from the cache for use in filename.

        Args:
            data (dict): Must contain the 'field' key
            file_item (FileItem): The file to rename
            index (int): Unused
            metadata_cache (dict): full_path → metadata dict

        Returns:
            str: The stringified metadata value or a fallback ("unknown", "invalid")
        """
        field = data.get("field")
        if not field:
            logger.warning("[MetadataModule] Missing 'field' in data config.")
            return "invalid"

        path = file_item.full_path
        metadata = metadata_cache.get(path) if metadata_cache else {}

        if not isinstance(metadata, dict):
            logger.warning(f"[MetadataModule] No metadata dict found for {path}")
            metadata = {}  # fallback to empty

        logger.debug(f"[MetadataModule] apply_from_data for {file_item.filename} with field='{field}'")

        if field == "last_modified":
            try:
                ts = os.path.getmtime(path)
                return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            except Exception as e:
                logger.warning(f"[MetadataModule] Failed to read last modified time: {e}")
                return "invalid"

        if field == "date":
            value = metadata.get("date")
            if not value:
                logger.info(f"[MetadataModule] No 'date' field in metadata for {file_item.filename}")
                return "unknown"
            return str(value)

        # === Generic metadata field ===
        value = metadata.get(field)
        if value is None:
            logger.warning(f"[MetadataModule] Field '{field}' not found in metadata for {path}")
            return "unknown"

        try:
            return str(value).strip()
        except Exception as e:
            logger.warning(f"[MetadataModule] Failed to stringify metadata value: {e}")
            return "invalid"

    @staticmethod
    def is_effective(data: dict) -> bool:
        return data.get('field') != 'last_modified'

