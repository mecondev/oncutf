"""
Module: specified_text_module.py

Author: Michael Economou
Date: 2025-05-02

This module defines a rename module that inserts user-specified text
into filenames. It allows users to prepend, append, or inject static
text at a defined position within the filename.

Used in the oncutf application as one of the modular renaming components.
"""
import os
from typing import Optional
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit
from PyQt5.QtCore import pyqtSignal
from modules.base_module import BaseRenameModule
from utils.validation import is_valid_filename_text

# initialize logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)


class SpecifiedTextModule(BaseRenameModule):
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
        self._last_text = ""
        self.text_input.textChanged.connect(self.validate_input)

        layout.addWidget(self.text_label)
        layout.addWidget(self.text_input)


    def validate_input(self, text: str) -> None:
        """Validate and emit only on changes.

        Args:
            text (str): The text entered by the user.
        """
        if self._is_validating:
            return

        self._is_validating = True

        def apply_style():
            if is_valid_filename_text(text):
                self.text_input.setStyleSheet("")
            else:
                self.text_input.setStyleSheet("border: 1px solid red;")

        self.block_signals_while(self.text_input, apply_style)
        self.emit_if_changed(text)

        self._is_validating = False


    def get_data(self) -> dict:
        """
        Retrieves the current configuration of the specified text module.

        :return: A dictionary containing the type and the user-specified text.
        """

        return {
            "type": "specified_text",
            "text": self.text_input.text()
        }

    def reset(self) -> None:
        self.text_input.clear()
        self.text_input.setStyleSheet("")

    def apply(self, file_item, index=0, metadata_cache=None) -> str:
        return self.apply_from_data(self.get_data(), file_item, index, metadata_cache)

    @staticmethod
    def apply_from_data(data: dict, file_item, index: int = 0, metadata_cache: Optional[dict] = None) -> str:
        logger.debug(f"[SpecifiedTextModule] Called with data={data}, index={index}")
        text = data.get("text", "")

        if not text:
            logger.debug("[SpecifiedTextModule] Empty text input, returning original filename.")
            return os.path.splitext(file_item.filename)[0]

        if not is_valid_filename_text(text):
            logger.warning(f"[SpecifiedTextModule] Invalid filename text: '{text}'")
            return "invalid"

        # Always return only the basename (remove extension if user typed it)
        return os.path.splitext(text)[0]

    @staticmethod
    def is_effective(data: dict) -> bool:
        return bool(data.get('text', ''))




