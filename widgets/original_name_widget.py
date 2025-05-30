"""
Module: original_name_widget.py

Author: Michael Economou
Date: 2025-05-01

This module defines a QWidget-based rename module that allows users to reuse
the original filename with optional Greek-to-Greeklish transliteration.

Case and separator transformations are now handled by the NameTransformModule
in the post-transform area to avoid duplication.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QCheckBox, QHBoxLayout
from PyQt5.QtCore import pyqtSignal, Qt
from utils.logger_helper import get_logger

logger = get_logger(__name__)


class OriginalNameWidget(QWidget):
    """
    Rename module widget for reusing the original filename.

    Provides a checkbox for optional Greek-to-Greeklish conversion.
    Case and separator transformations are handled by NameTransformModule.
    """

    updated = pyqtSignal(object)

    LABEL_WIDTH = 120
    DROPDOWN_WIDTH = 128

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setProperty("module", True)
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Only Greeklish option - case and separator transforms are handled by NameTransformModule
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self.checkbox = QCheckBox("Convert Greek to Greeklish")
        self.checkbox.toggled.connect(self._emit_updated)

        row.addWidget(self.checkbox)
        row.addStretch()
        layout.addLayout(row)
        layout.addStretch()

    def _emit_updated(self) -> None:
        logger.debug("[OriginalNameWidget] Emitting updated signal")
        self.updated.emit(self)

    def get_data(self) -> dict:
        return {
            "type": "original_name",
            "greeklish": self.checkbox.isChecked()
        }
