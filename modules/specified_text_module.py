# modules/specified_text_module.py
# Author: Michael Economou
# Date: 2025-05-02
# Description: Module for inserting specified text in filenames.

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
        if re.match(ALLOWED_FILENAME_CHARS, text):
            self.text_input.setStyleSheet("")
        else:
            self.text_input.setStyleSheet("border: 1px solid red;")
        self.updated.emit()

    def get_data(self) -> dict:
        return {
            "type": "specified_text",
            "text": self.text_input.text().strip()
        }
