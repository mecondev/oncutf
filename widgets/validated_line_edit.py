"""
Module: validated_line_edit.py

Author: Michael Economou
Date: 2025-01-01

This module provides a custom QLineEdit widget with built-in filename
validation, input filtering, and tooltip feedback. It prevents invalid
characters from being entered and provides visual feedback to the user.

Contains:
- ValidatedLineEdit: Enhanced QLineEdit with validation and tooltip support
"""

from typing import Optional
from PyQt5.QtWidgets import QLineEdit, QWidget
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QKeyEvent

from utils.tooltip_helper import show_error_tooltip, TooltipType
from utils.filename_validator import (
    should_allow_character_input,
    get_validation_error_message,
    clean_filename_text,
    is_validation_error_marker
)
from config import INVALID_FILENAME_MARKER
import logging

logger = logging.getLogger(__name__)


class ValidatedLineEdit(QLineEdit):
    """
    Custom QLineEdit with filename validation and input filtering.

    Features:
    - Blocks invalid characters on input
    - Shows error tooltips for invalid characters
    - Provides visual feedback with border styling
    - Cleans pasted text automatically
    """

    # Signal emitted when validation state changes
    validation_changed = pyqtSignal(bool)  # True if valid, False if invalid

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Validation state tracking
        self._is_valid = True
        self._has_had_content = False

        # Setup initial state
        self._setup_signals()

    def _setup_signals(self) -> None:
        """Setup internal signal connections"""
        self.textChanged.connect(self._on_text_changed)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Handle key press events with validation

        Args:
            event: The key press event
        """
        try:
            # Allow control characters (backspace, delete, arrow keys, etc.)
            if event.text() == '' or len(event.text()) == 0:
                super().keyPressEvent(event)
                return

            # Check if character is allowed
            if not should_allow_character_input(event.text()):
                # Show error tooltip for invalid character
                error_msg = f"Character '{event.text()}' is not allowed in filenames"
                show_error_tooltip(self, error_msg)

                # Also apply error styling temporarily
                self._apply_temporary_error_style()

                logger.debug(f"[ValidatedLineEdit] Blocked invalid character: '{event.text()}'")
                return  # Don't call super() - character is blocked

            # Allow the character
            super().keyPressEvent(event)

        except Exception as e:
            logger.error(f"[ValidatedLineEdit] Error in keyPressEvent: {e}")
            super().keyPressEvent(event)

    def insertFromMimeData(self, source) -> None:
        """
        Handle paste operations with validation and cleaning

        Args:
            source: The mime data source
        """
        try:
            if source.hasText():
                text = source.text()
                cleaned_text = clean_filename_text(text)

                if cleaned_text != text:
                    # Show tooltip about cleaned characters
                    removed_chars = ''.join(set(text) - set(cleaned_text))
                    if removed_chars:
                        error_msg = f"Removed invalid characters: {removed_chars}"
                        show_error_tooltip(self, error_msg)

                    logger.debug(f"[ValidatedLineEdit] Cleaned pasted text: '{text}' → '{cleaned_text}'")

                # Insert the cleaned text
                self.insert(cleaned_text)
            else:
                super().insertFromMimeData(source)

        except Exception as e:
            logger.error(f"[ValidatedLineEdit] Error in insertFromMimeData: {e}")
            super().insertFromMimeData(source)

    def _on_text_changed(self, text: str) -> None:
        """
        Handle text changes and update validation state

        Args:
            text: The new text content
        """
        try:
            # Track if field has ever had content
            if text and not self._has_had_content:
                self._has_had_content = True

            # Validate the text
            old_valid_state = self._is_valid
            self._is_valid = self._validate_text(text)

            # Update styling
            self._update_styling(text)

            # Emit signal if validation state changed
            if old_valid_state != self._is_valid:
                self.validation_changed.emit(self._is_valid)
                logger.debug(f"[ValidatedLineEdit] Validation state changed: {self._is_valid}")

        except Exception as e:
            logger.error(f"[ValidatedLineEdit] Error in _on_text_changed: {e}")

    def _validate_text(self, text: str) -> bool:
        """
        Validate the current text content

        Args:
            text: Text to validate

        Returns:
            bool: True if text is valid
        """
        if not text:
            return True  # Empty text is considered valid

        # Check for validation error marker
        if is_validation_error_marker(text):
            return False

        # Use existing validation logic
        from utils.validation import is_valid_filename_text
        return is_valid_filename_text(text)

    def _update_styling(self, text: str) -> None:
        """
        Update widget styling based on validation state

        Args:
            text: Current text content
        """
        try:
            if len(text) >= self.maxLength() and self.maxLength() > 0:
                # At character limit - darker gray styling
                self.setStyleSheet("border: 2px solid #555555; background-color: #3a3a3a; color: #bbbbbb;")
            elif not text and self._has_had_content:
                # Empty after having content - darker orange styling
                self.setStyleSheet("border: 2px solid #cc6600;")
            elif not text:
                # Empty initially - no special styling
                self.setStyleSheet("")
            elif not self._is_valid:
                # Invalid text - red styling
                self.setStyleSheet("border: 2px solid #ff0000;")
            else:
                # Valid - default styling
                self.setStyleSheet("")

        except Exception as e:
            logger.error(f"[ValidatedLineEdit] Error in _update_styling: {e}")

    def _apply_temporary_error_style(self) -> None:
        """Apply temporary error styling for blocked characters"""
        try:
            from PyQt5.QtCore import QTimer

            # Apply error style
            self.setStyleSheet("border: 2px solid #ff4444; background-color: #3a2222;")

            # Reset style after a short delay
            QTimer.singleShot(500, lambda: self._update_styling(self.text()))

        except Exception as e:
            logger.error(f"[ValidatedLineEdit] Error in _apply_temporary_error_style: {e}")

    def is_valid(self) -> bool:
        """
        Get current validation state

        Returns:
            bool: True if current text is valid
        """
        return self._is_valid

    def reset_validation_state(self) -> None:
        """Reset validation tracking state"""
        self._has_had_content = False
        self._is_valid = True
        self.setStyleSheet("")

    def get_validation_error_message(self) -> str:
        """
        Get validation error message for current text

        Returns:
            str: Error message, empty if valid
        """
        if self._is_valid:
            return ""

        return get_validation_error_message(self.text())
