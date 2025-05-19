"""
Module: original_name_widget.py

Author: Michael Economou
Date: 2025-05-01

This module defines a QWidget-based rename module that allows users to reuse
the original filename with two configurable transformations:
1) Case transformation (original, lower, UPPER)
2) Separator transformation (as-is, snake_case, kebab-case, space)
Also includes optional Greek-to-Greeklish transliteration.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QCheckBox, QHBoxLayout
from PyQt5.QtCore import pyqtSignal, Qt
from utils.logger_helper import get_logger

logger = get_logger(__name__)


class OriginalNameWidget(QWidget):
    """
    Rename module widget for reusing the original filename.

    Provides dropdowns for case transformation and separator style,
    and a checkbox for Greeklish conversion.
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

        # Row 1: Case Transformation
        self.case_dropdown = QComboBox()
        self.case_dropdown.addItems(["original", "lower", "UPPER"])
        self.case_dropdown.setFixedWidth(self.DROPDOWN_WIDTH)
        self.case_dropdown.currentIndexChanged.connect(self._emit_updated)

        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(6)
        label1 = QLabel("Text Case:")
        label1.setFixedWidth(self.LABEL_WIDTH)
        label1.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row1.addWidget(label1)
        row1.addWidget(self.case_dropdown)
        row1.addStretch()
        layout.addLayout(row1)

        # Row 2: Separator Style
        self.sep_dropdown = QComboBox()
        self.sep_dropdown.addItems(["as-is", "snake_case", "kebab-case", "space"])
        self.sep_dropdown.setFixedWidth(self.DROPDOWN_WIDTH)
        self.sep_dropdown.currentIndexChanged.connect(self._emit_updated)

        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        row2.setSpacing(6)
        label2 = QLabel("Separator:")
        label2.setFixedWidth(self.LABEL_WIDTH)
        label2.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row2.addWidget(label2)
        row2.addWidget(self.sep_dropdown)
        row2.addStretch()
        layout.addLayout(row2)

        # Row 3: Greeklish
        row3 = QHBoxLayout()
        self.checkbox = QCheckBox("Greek to Greeklish")
        self.checkbox.setFixedWidth(self.LABEL_WIDTH + self.DROPDOWN_WIDTH)
        self.checkbox.setLayoutDirection(Qt.RightToLeft)
        self.checkbox.toggled.connect(self._emit_updated)
        row3.addWidget(self.checkbox)
        row3.addStretch()
        layout.addLayout(row3)

        layout.addStretch()

    def _emit_updated(self) -> None:
        logger.debug("[OriginalNameWidget] Emitting updated signal")
        self.updated.emit(self)

    def get_data(self) -> dict:
        return {
            "type": "original_name",
            "case": self.case_dropdown.currentText(),
            "separator": self.sep_dropdown.currentText(),
            "greeklish": self.checkbox.isChecked()
        }
