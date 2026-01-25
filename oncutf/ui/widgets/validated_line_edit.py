"""Module: validated_line_edit.py.

Author: Michael Economou
Date: 2025-05-31

This module provides a custom QLineEdit widget with built-in filename
validation, input filtering, and tooltip feedback. It prevents invalid
characters from being entered and provides visual feedback to the user.
Contains:
- ValidatedLineEdit: Enhanced QLineEdit with validation and tooltip support
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QLineEdit, QWidget

from oncutf.config import INVALID_FILENAME_CHARS
from oncutf.ui.widgets.base_validated_input import BaseValidatedInput
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.naming.filename_validator import (
    get_validation_error_message,
    is_validation_error_marker,
    validate_filename_part,
)

logger = get_cached_logger(__name__)


class ValidatedLineEdit(QLineEdit, BaseValidatedInput):
    """Custom QLineEdit with filename validation and input filtering.

    Features:
    - Blocks invalid characters on input
    - Shows error tooltips for invalid characters
    - Provides visual feedback with border styling
    - Cleans pasted text automatically
    """

    # Signal emitted when validation state changes
    validation_changed = pyqtSignal(bool)  # True if valid, False if invalid

    def __init__(self, parent: QWidget | None = None):
        """Initialize the validated line edit with filename validation."""
        QLineEdit.__init__(self, parent)
        BaseValidatedInput.__init__(self)

    def _setup_validation_signals(self) -> None:
        """Setup internal signal connections."""
        self.textChanged.connect(self._on_text_changed)

    def emit_validation_changed(self, is_valid: bool) -> None:
        """Emit validation changed signal."""
        self.validation_changed.emit(is_valid)

    def get_blocked_characters(self) -> set[str]:
        """Get set of characters that should be blocked for filename input.

        Returns:
            Set of characters to block

        """
        return set(INVALID_FILENAME_CHARS)

    def validate_text_content(self, text: str) -> tuple[bool, str]:
        """Validate text content using filename validation.

        Args:
            text: Text to validate

        Returns:
            Tuple of (is_valid, error_message)

        """
        if not text:
            return True, ""  # Empty text is valid

        # Check for validation error marker
        if is_validation_error_marker(text):
            return False, "Invalid filename"

        # Use filename validation
        is_valid, _result = validate_filename_part(text)
        if not is_valid:
            return False, get_validation_error_message(text)

        return True, ""

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events with validation."""
        if self.handle_key_press_validation(event):
            super().keyPressEvent(event)

    def insertFromMimeData(self, source) -> None:
        """Handle paste operations with validation and cleaning."""
        try:
            if source.hasText():
                original_text = source.text()
                cleaned_text = self.handle_paste_validation(original_text)

                # Insert the cleaned text
                self.insert(cleaned_text)
            else:
                super().insertFromMimeData(source)

        except Exception as e:
            logger.error("[ValidatedLineEdit] Error in insertFromMimeData: %s", e)
            super().insertFromMimeData(source)

    def _on_text_changed(self, text: str) -> None:
        """Handle text changes and update validation state."""
        self.update_validation_state(text)
