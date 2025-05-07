"""
Module: counter_module.py

Author: Michael Economou
Date: 2025-05-02

This module defines a rename module that inserts an incrementing counter
into filenames. It is used within the oncutf application to generate
sequential file names based on configurable start value, step, and padding.
"""


from typing import Optional
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import pyqtSignal, Qt

class CounterModule(QWidget):
    """
    A widget for inserting an incrementing counter in filenames.
    Displays each row as: [Label (fixed width, right-aligned)] [input field] [btn_minus] [btn_plus]
    """

    updated = pyqtSignal()

    LABEL_WIDTH = 120  # pixels

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setProperty("module", True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Row 1: Start Number
        self.start_input, row1 = self._create_row(
            "Start Number", initial_value=1, min_val=0
        )
        layout.addLayout(row1)

        # Row 2: Number of Digits
        self.padding_input, row2 = self._create_row(
            "Number of Digits", initial_value=4, min_val=1
        )
        layout.addLayout(row2)

        # Row 3: Increment By
        self.increment_input, row3 = self._create_row(
            "Increment By", initial_value=1, min_val=1
        )
        layout.addLayout(row3)

    def _create_row(
        self,
        label_text: str,
        initial_value: int = 1,
        min_val: int = 0,
        max_val: int = 999999
    ) -> tuple[QLineEdit, QHBoxLayout]:
        """
        Create a row layout with:
        [QLabel(label_text)] [QLineEdit] [btn_minus] [btn_plus]
        Returns the input field and the layout.
        """
        # Label with fixed width and right alignment
        label = QLabel(label_text)
        label.setFixedWidth(self.LABEL_WIDTH)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Input field with integer validator
        input_field = QLineEdit(str(initial_value))
        input_field.setFixedWidth(60)
        validator = QIntValidator(min_val, max_val, self)
        input_field.setValidator(validator)

        # Buttons
        btn_minus = QPushButton("-")
        btn_plus = QPushButton("+")
        btn_minus.setFixedSize(24, 24)
        btn_plus.setFixedSize(24, 24)

        # Adjust helper
        def adjust(delta: int) -> None:
            """
            Adjusts the value in the input field by the specified delta,
            ensuring it remains within the specified minimum and maximum bounds.

            Emits the 'updated' signal after updating the value.

            :param delta: The amount to adjust the current value by.
            """

            try:
                val = int(input_field.text())
            except ValueError:
                val = min_val
            val = max(min_val, min(val + delta, max_val))
            input_field.setText(str(val))
            self.updated.emit()

        # Connect signals
        btn_minus.clicked.connect(lambda: adjust(-1))
        btn_plus.clicked.connect(lambda: adjust(1))
        input_field.textChanged.connect(self.updated.emit)

        # Build row layout
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)
        row_layout.addWidget(label)
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
            "padding": int(self.padding_input.text() or "0"),
            "step": int(self.increment_input.text() or "0")
        }
