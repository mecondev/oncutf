"""
metadata_edit_dialog.py

Author: Michael Economou
Date: 2025-06-07

This module provides a dialog for editing metadata values.
It supports validation based on field type and shows appropriate error messages.
"""

from typing import Tuple

from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from utils.logger_helper import get_logger
from utils.metadata_validators import get_validator_for_key

logger = get_logger(__name__)

class MetadataEditDialog(QDialog):
    """
    Dialog for editing metadata values with validation.
    """

    def __init__(self, parent=None, key_path: str = "", current_value: str = ""):
        super().__init__(parent)

        self.key_path = key_path
        self.current_value = str(current_value)
        self.new_value = None
        self.validator = get_validator_for_key(key_path)

        self.setWindowTitle("Edit Value")
        self.resize(350, 150)

        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI elements."""
        layout = QVBoxLayout(self)

        # Field name
        key_label = QLabel(f"Field: {self.key_path}")
        key_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(key_label)

        # Current value
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("Current value:"))
        current_value_label = QLabel(self.current_value)
        current_value_label.setStyleSheet("font-style: italic;")
        current_layout.addWidget(current_value_label)
        current_layout.addStretch()
        layout.addLayout(current_layout)

        # New value input - combo box for rotation, line edit for others
        value_layout = QHBoxLayout()
        value_layout.addWidget(QLabel("New value:"))

        if "Rotation" in self.key_path:
            self.value_input = QComboBox()
            self.value_input.addItems(["0", "90", "180", "270"])
            self.value_input.setCurrentText(self.current_value if self.current_value in ["0", "90", "180", "270"] else "0")
        else:
            self.value_input = QLineEdit(self.current_value)

        value_layout.addWidget(self.value_input)
        layout.addLayout(value_layout)

        # Error message (initially hidden)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def validate_and_accept(self):
        """Validate the input and accept if valid."""
        if isinstance(self.value_input, QComboBox):
            value = self.value_input.currentText()
            self.new_value = value
            self.accept()
            return

        value = self.value_input.text()

        if self.validator:
            is_valid, normalized_value, error_msg = self.validator(value)

            if is_valid:
                self.new_value = normalized_value
                self.accept()
            else:
                self.error_label.setText(error_msg)
                self.error_label.setVisible(True)
        else:
            # No validator, accept as is
            self.new_value = value
            self.accept()

    @staticmethod
    def get_value(parent=None, key_path: str = "", current_value: str = "") -> Tuple[bool, str]:
        """
        Static method to create the dialog and return the result.

        Args:
            parent: Parent widget
            key_path: The metadata key path (e.g. "EXIF/Rotation")
            current_value: The current value of the field

        Returns:
            Tuple containing:
            - bool: True if user accepted, False if canceled
            - str: The new value if accepted, empty string if canceled
        """
        dialog = MetadataEditDialog(parent, key_path, current_value)
        result = dialog.exec_()

        if result == QDialog.Accepted and dialog.new_value is not None:
            return True, dialog.new_value

        return False, ""
