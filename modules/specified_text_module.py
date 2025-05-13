"""
Module: specified_text_module.py

Author: Michael Economou
Date: 2025-05-02

This module defines a rename module that inserts user-specified text
into filenames. It allows users to prepend, append, or inject static
text at a defined position within the filename.

Used in the oncutf application as one of the modular renaming components.
"""

from typing import Optional
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit
from PyQt5.QtCore import pyqtSignal
from utils.validation import is_valid_filename_text

# initialize logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)


class SpecifiedTextModule(QWidget):
    """
    A module for inserting user-defined text in filenames.
    """
    updated = pyqtSignal(object)

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

    def validate_input(self, text: str) -> None:
        """
        Validates the user input text and updates visual feedback.
        Emits `updated` signal to notify changes.

        Args:
            text (str): The text entered by the user.
        """
        if is_valid_filename_text(text):
            self.text_input.setStyleSheet("")
        else:
            self.text_input.setStyleSheet("border: 1px solid red;")

        logger.info("[SpecifiedTextModule] Emitting 'updated' signal.")
        self.updated.emit(self)

    def get_data(self) -> dict:
        """
        Retrieves the current configuration of the specified text module.

        :return: A dictionary containing the type and the user-specified text.
        """

        return {
            "type": "specified_text",
            "text": self.text_input.text().strip()
        }

    def reset(self) -> None:
        self.text_input.clear()
        self.text_input.setStyleSheet("")

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
        Applies the specified text transformation to the filename.

        Parameters
        ----------
        data : dict
            A dictionary with keys:
                - 'type': should be 'specified_text'
                - 'text': the user-defined static text to insert
        file_item : FileItem
            The file item being renamed (unused in this module).
        index : int, optional
            Index of the file in the batch (not used here).
        metadata_cache : dict, optional
            Not used in this module but accepted for API compatibility.

        Returns
        -------
        str
            The static text to prepend/append in the filename.
        """
        logger.debug(f"[SpecifiedTextModule] Called with data={data}, index={index}")

        text = data.get("text", "").strip()
        if not is_valid_filename_text(text):
            logger.warning("[SpecifiedTextModule] Invalid filename text: '%s'", text)
            return "invalid"

        logger.debug(f"[SpecifiedTextModule] index={index}, text='{text}' → return='{text if is_valid_filename_text(text) else 'invalid'}'")

        return text
