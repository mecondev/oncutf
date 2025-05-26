"""
name_transform_widget.py

UI widget for configuring NameTransformModule.
Provides dropdowns for case and separator transformation options.

Author: Michael Economou
Date: 2025-05-25
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
from PyQt5.QtCore import pyqtSignal


class NameTransformWidget(QWidget):
    """
    UI component for selecting case and separator transformations.
    Used within the RenameModuleWidget container.
    """
    updated = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NameTransformWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # Case transformation
        case_layout = QHBoxLayout()
        case_label = QLabel("Case:")
        self.case_combo = QComboBox()
        self.case_combo.addItems(["original", "lower", "UPPER", "capitalize"])
        self.case_combo.currentTextChanged.connect(lambda _: self.updated.emit(self))
        case_layout.addWidget(case_label)
        case_layout.addWidget(self.case_combo)
        layout.addLayout(case_layout)

        # Separator transformation
        sep_layout = QHBoxLayout()
        sep_label = QLabel("Separator:")
        self.sep_combo = QComboBox()
        self.sep_combo.addItems(["as-is", "snake_case", "kebab-case", "space"])
        self.sep_combo.currentTextChanged.connect(lambda _: self.updated.emit(self))
        sep_layout.addWidget(sep_label)
        sep_layout.addWidget(self.sep_combo)
        layout.addLayout(sep_layout)

    def get_data(self) -> dict:
        return {
            "case": self.case_combo.currentText(),
            "separator": self.sep_combo.currentText(),
        }

    def set_data(self, data: dict) -> None:
        self.case_combo.setCurrentText(data.get("case", "original"))
        self.sep_combo.setCurrentText(data.get("separator", "as-is"))
