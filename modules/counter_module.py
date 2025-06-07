"""
Module: counter_module.py

Author: Michael Economou
Date: 2025-05-02

This module defines a rename module that inserts an incrementing counter
into filenames. It is used within the oncutf application to generate
sequential file names based on configurable start value, step, and padding.
"""

from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from modules.base_module import BaseRenameModule

# initialize logger
from utils.logger_helper import get_logger

logger = get_logger(__name__)


class CounterModule(BaseRenameModule):
    """
    A widget for inserting an incrementing counter in filenames.
    Displays each row as: [Label (fixed width, right-aligned)] [input field] [btn_minus] [btn_plus]
    """

    updated = pyqtSignal(object)

    LABEL_WIDTH = 100  # pixels

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

        # Connect inputs to update signal (debounced)
        self.start_input.textChanged.connect(self._on_value_change)
        self.padding_input.textChanged.connect(self._on_value_change)
        self.increment_input.textChanged.connect(self._on_value_change)

        # Initialize _last_value to prevent duplicate signals
        self._last_value = str(self.get_data())



    def _on_value_change(self) -> None:
        """
        Triggered when any of the spinboxes change.
        Emits update only if data has truly changed.
        """
        self.emit_if_changed(str(self.get_data()))

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
            self.updated.emit(self)

        # Connect signals
        btn_minus.clicked.connect(lambda: adjust(-1))
        btn_plus.clicked.connect(lambda: adjust(1))
        input_field.textChanged.connect(lambda _: self.updated.emit(self))

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
        Applies a counter-based transformation using the given config and index.

        Parameters
        ----------
        data : dict
            Configuration dictionary with keys:
                - 'type': 'counter'
                - 'start': int, the starting number
                - 'padding': int, number of digits (e.g. 4 -> 0001)
                - 'step': int, increment step
        file_item : FileItem
            The file to rename (not used by counter).
        index : int, optional
            The position of the file in the list (used for offsetting).
        metadata_cache : dict, optional
            Not used in this module but accepted for API compatibility.

        Returns
        -------
        str
            The stringified counter value with proper padding.
        """
        try:
            start = int(data.get("start", 1))
            step = int(data.get("step", 1))
            padding = int(data.get("padding", 4))

            value = start + index * step
            result = f"{value:0{padding}d}"
            logger.debug(f"[CounterModule] index: {index}, value: {value}, padded: {result}")
            return result
        except Exception as e:
            logger.exception(f"[CounterModule] Failed to apply counter logic: {e}")
            return "####"

    @staticmethod
    def is_effective(data: dict) -> bool:
        return True
