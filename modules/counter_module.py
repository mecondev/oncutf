# counter_module.py
# Author: Michael Economou
# Date: 2025-05-01
# Description: A widget for inserting an incrementing counter in filenames

from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton
)
from PyQt5.QtCore import pyqtSignal


class CounterModule(QWidget):
    """
    A widget for inserting an incrementing counter in filenames.
    Uses line edits with -/+ buttons instead of spin boxes.
    """

    updated = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setProperty("module", True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Row 1: Start Number
        layout.addWidget(QLabel("Start Number:"))
        self.start_input, row1 = self._create_row(initial_value=1)
        layout.addLayout(row1)

        # Row 2: Number of Digits
        layout.addWidget(QLabel("Number of Digits:"))
        self.padding_input, row2 = self._create_row(initial_value=4, min_val=1)
        layout.addLayout(row2)

        # Row 3: Increment By
        layout.addWidget(QLabel("Increment By:"))
        self.increment_input, row3 = self._create_row(initial_value=1, min_val=1)
        layout.addLayout(row3)

    def _create_row(self, initial_value=1, min_val=0, max_val=99999) -> tuple[QLineEdit, QHBoxLayout]:
        """
        Helper method to create a row with a QLineEdit and -/+ buttons.
        """
        input_field = QLineEdit(str(initial_value))
        input_field.setFixedWidth(60)
        input_field.setMaxLength(6)
        input_field.setValidator(None)  # Optional: use QIntValidator here

        btn_minus = QPushButton("-")
        btn_plus = QPushButton("+")
        btn_minus.setFixedSize(18, 18)
        btn_plus.setFixedSize(18, 18)

        def adjust(delta):
            try:
                val = int(input_field.text())
            except ValueError:
                val = min_val
            val = max(min_val, min(val + delta, max_val))
            input_field.setText(str(val))
            self.updated.emit()

        btn_minus.clicked.connect(lambda: adjust(-1))
        btn_plus.clicked.connect(lambda: adjust(+1))
        input_field.textChanged.connect(self.updated.emit)

        row_layout = QHBoxLayout()
        row_layout.addWidget(input_field)
        row_layout.addWidget(btn_minus)
        row_layout.addWidget(btn_plus)
        row_layout.addStretch()

        return input_field, row_layout

    def get_data(self) -> dict:
        """
        Returns the current configuration of the counter module.

        :return: dict with counter info
        """
        return {
            "type": "counter",
            "start": int(self.start_input.text() or "0"),
            "padding": int(self.padding_input.text() or "1"),
            "step": int(self.increment_input.text() or "1")
        }

