"""
Module: specified_text_module.py

Author: Michael Economou
Date: 2025-05-02

This module defines a rename module that inserts user-specified text
into filenames. It allows users to prepend, append, or inject static
text at a defined position within the filename.

Used in the ReNExif application as one of the modular renaming components.
"""


from typing import Optional
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit
from PyQt5.QtCore import pyqtSignal
import re
from config import ALLOWED_FILENAME_CHARS


class SpecifiedTextModule(QWidget):
    """
    A module for inserting user-defined text in filenames.
    """
    updated = pyqtSignal()

    def __init__(self, parent: Optional[QWidget]=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.text_label = QLabel("Text")
        self.text_label.setMaximumHeight(24)
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter custom text")
        self.text_input.setMaxLength(128)
        self.text_input.setMaximumHeight(24)
        self.text_input.textChanged.connect(self.validate_input)

        layout.addWidget(self.text_label)
        layout.addWidget(self.text_input)

        # self.setFixedHeight(90)

    def validate_input(self, text):
        """
        Validates the user input text against allowed filename characters.

        Args:
            text (str): The text entered by the user.

        Emits:
            updated: Signal to indicate that the validation status has changed.
        """

        if re.match(ALLOWED_FILENAME_CHARS, text):
            self.text_input.setStyleSheet("")
        else:
            self.text_input.setStyleSheet("border: 1px solid red;")
        self.updated.emit()

    def get_data(self) -> dict:
        """
        Retrieves the current configuration of the specified text module.

        :return: A dictionary containing the type and the user-specified text.
        """

        return {
            "type": "specified_text",
            "text": self.text_input.text().strip()
        }
