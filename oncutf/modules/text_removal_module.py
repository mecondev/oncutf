"""
Module: text_removal_module.py

Author: Michael Economou
Date: 2025-05-01

This module provides functionality to remove specific text patterns from filenames.
It supports removing text from the start, end, or anywhere in the filename,
with case-sensitive or case-insensitive matching.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from oncutf.core.pyqt_imports import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    Qt,
    QVBoxLayout,
    QWidget,
)
from oncutf.modules.base_module import BaseRenameModule

logger = logging.getLogger(__name__)


@dataclass
class TextRemovalMatch:
    """Represents a matched text region for removal."""

    start: int
    end: int
    matched_text: str


class TextRemovalModule(BaseRenameModule):
    """
    Module for removing specific text patterns from filenames.

    This module allows users to remove text from different positions in filenames:
    - From the end of the filename
    - From the start of the filename
    - First occurrence anywhere in the filename
    - All occurrences anywhere in the filename

    It supports both case-sensitive and case-insensitive matching.
    """

    def __init__(self, parent: QWidget | None = None):
        """Initialize the text removal module."""
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface for text removal."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # First row: Text to remove
        text_row = QHBoxLayout()
        text_row.setContentsMargins(0, 0, 0, 0)
        text_row.setSpacing(6)

        text_label = QLabel("Remove:")
        text_label.setFixedWidth(80)
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter text to remove (e.g., _copy, _backup)")
        self.text_input.textChanged.connect(self.on_text_changed)

        text_row.addWidget(text_label)
        text_row.addWidget(self.text_input)
        layout.addLayout(text_row)

        # Second row: Position and case sensitivity
        options_row = QHBoxLayout()
        options_row.setContentsMargins(0, 0, 0, 0)
        options_row.setSpacing(6)

        position_label = QLabel("From:")
        position_label.setFixedWidth(80)
        self.position_combo = QComboBox()
        self.position_combo.addItems(
            ["End of name", "Start of name", "Anywhere (first)", "Anywhere (all)"]
        )
        self.position_combo.setCurrentText("End of name")

        # Apply theme styling
        from oncutf.ui.widgets.ui_delegates import ComboBoxItemDelegate
        from oncutf.utils.theme_engine import ThemeEngine
        theme = ThemeEngine()
        self.position_combo.setFixedHeight(theme.get_constant("combo_height"))
        self.position_combo.setItemDelegate(ComboBoxItemDelegate(self.position_combo, theme))

        # Ensure combo box drops down instead of popping up
        self.position_combo.view().window().setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.position_combo.currentTextChanged.connect(self.on_position_changed)

        self.case_sensitive_check = QCheckBox("Case sensitive")
        self.case_sensitive_check.setChecked(False)
        self.case_sensitive_check.toggled.connect(self.on_case_changed)

        options_row.addWidget(position_label)
        options_row.addWidget(self.position_combo)
        options_row.addStretch()
        options_row.addWidget(self.case_sensitive_check)
        layout.addLayout(options_row)

    def on_text_changed(self):
        """Handle text input changes."""
        text = self.text_input.text()
        logger.debug("[TextRemoval] Text changed to: '%s'", text, extra={"dev_only": True})
        self.updated.emit(self)

    def on_position_changed(self):
        """Handle position combo changes."""
        position = self.position_combo.currentText()
        logger.debug("[TextRemoval] Position changed to: '%s'", position, extra={"dev_only": True})
        self.updated.emit(self)

    def on_case_changed(self):
        """Handle case sensitivity changes."""
        case_sensitive = self.case_sensitive_check.isChecked()
        logger.debug(
            "[TextRemoval] Case sensitivity changed to: %s",
            case_sensitive,
            extra={"dev_only": True},
        )
        self.updated.emit(self)

    def get_data(self) -> dict:
        """
        Get the current configuration data.

        Returns:
            Dictionary containing text removal configuration
        """
        return {
            "text_to_remove": self.text_input.text(),
            "position": self.position_combo.currentText(),
            "case_sensitive": self.case_sensitive_check.isChecked(),
        }

    def set_data(self, data: dict):
        """
        Set the configuration data.

        Args:
            data: Dictionary containing text removal configuration
        """
        self.text_input.setText(data.get("text_to_remove", ""))
        position = data.get("position", "End of name")
        if position in ["End of name", "Start of name", "Anywhere (first)", "Anywhere (all)"]:
            self.position_combo.setCurrentText(position)
        self.case_sensitive_check.setChecked(data.get("case_sensitive", False))

    @staticmethod
    def find_matches(
        text: str,
        pattern: str,
        position: str = "End of name",
        case_sensitive: bool = False,
    ) -> list[TextRemovalMatch]:
        """
        Find all matches of pattern in text based on position and case sensitivity.

        Args:
            text: Text to search in
            pattern: Pattern to search for
            position: Where to search (\"End of name\", \"Start of name\", \"Anywhere (first)\", \"Anywhere (all)\")
            case_sensitive: Whether to use case-sensitive matching

        Returns:
            List of TextRemovalMatch objects representing matched regions
        """
        if not pattern:
            return []

        matches: list[TextRemovalMatch] = []

        search_text = pattern if case_sensitive else pattern.lower()
        target_text = text if case_sensitive else text.lower()

        if position == "End of name":
            if target_text.endswith(search_text):
                start = len(text) - len(pattern)
                end = len(text)
                matches.append(TextRemovalMatch(start, end, text[start:end]))

        elif position == "Start of name":
            if target_text.startswith(search_text):
                matches.append(TextRemovalMatch(0, len(pattern), text[0:len(pattern)]))

        elif position == "Anywhere (first)":
            if case_sensitive:
                idx = text.find(pattern)
                if idx != -1:
                    matches.append(TextRemovalMatch(idx, idx + len(pattern), text[idx:idx + len(pattern)]))
            else:
                regex_pattern = re.escape(pattern)
                match = re.search(regex_pattern, text, flags=re.IGNORECASE)
                if match:
                    matches.append(TextRemovalMatch(match.start(), match.end(), match.group()))

        elif position == "Anywhere (all)":
            if case_sensitive:
                start = 0
                while True:
                    idx = text.find(pattern, start)
                    if idx == -1:
                        break
                    matches.append(TextRemovalMatch(idx, idx + len(pattern), text[idx:idx + len(pattern)]))
                    start = idx + len(pattern)
            else:
                regex_pattern = re.escape(pattern)
                for match in re.finditer(regex_pattern, text, flags=re.IGNORECASE):
                    matches.append(TextRemovalMatch(match.start(), match.end(), match.group()))

        return matches

    @staticmethod
    def apply_removal(text: str, matches: list[TextRemovalMatch]) -> str:
        """
        Apply removal of matched text regions.

        Args:
            text: Original text
            matches: List of matches to remove

        Returns:
            Text with matched regions removed
        """
        if not matches:
            return text

        result_parts: list[str] = []
        last_end = 0

        for match in sorted(matches, key=lambda m: m.start):
            result_parts.append(text[last_end:match.start])
            last_end = match.end

        result_parts.append(text[last_end:])
        return "".join(result_parts)

    @staticmethod
    def is_effective(data: dict) -> bool:
        """
        Check if this module configuration is effective.

        Args:
            data: Configuration data

        Returns:
            True if the module will modify filenames
        """
        text_to_remove = data.get("text_to_remove", "").strip()
        return len(text_to_remove) > 0

    @staticmethod
    def apply_from_data(data: dict, file_item, _index: int, _metadata_cache=None) -> str:
        """
        Apply text removal to a filename based on configuration data.

        Args:
            data: Configuration data
            file_item: File item with original filename
            index: File index (unused in this module)
            metadata_cache: Metadata cache (unused in this module)

        Returns:
            Modified filename with text removed
        """
        import os

        original_name = file_item.filename
        name_without_ext, ext = os.path.splitext(original_name)

        text_to_remove = data.get("text_to_remove", "").strip()
        if not text_to_remove:
            return original_name

        position = data.get("position", "End of name")
        case_sensitive = data.get("case_sensitive", False)

        matches = TextRemovalModule.find_matches(
            name_without_ext, text_to_remove, position, case_sensitive
        )
        result_name = TextRemovalModule.apply_removal(name_without_ext, matches)

        return f"{result_name}{ext}"

    def get_preview_text(self, file_item, index: int, metadata_cache=None) -> str:
        """
        Get preview text for this module.

        Args:
            file_item: File item to preview
            index: File index
            metadata_cache: Metadata cache

        Returns:
            Preview text showing the result
        """
        data = self.get_data()
        if not self.is_effective(data):
            return file_item.filename

        return self.apply_from_data(data, file_item, index, metadata_cache)
