"""
Module: base_validated_input.py

Author: Michael Economou
Date: 2025-06-01

Base class for validated input widgets providing common validation functionality.
This module serves as the foundation for both filename and metadata input validation,
offering real-time character blocking, paste cleaning, and visual feedback.
Contains:
- BaseValidatedInput: Abstract base class for validated input widgets
"""

import logging
from typing import Set, Tuple

from config import (
    QLABEL_DARK_BG,
    QLABEL_DARK_BORDER,
    QLABEL_INFO_TEXT,
)
from core.pyqt_imports import QKeyEvent
from utils.tooltip_helper import show_error_tooltip

logger = logging.getLogger(__name__)


class BaseValidatedInput:
    """
    Abstract base class for validated input widgets.

    Provides common validation functionality including:
    - Real-time character validation and blocking
    - Paste content cleaning
    - Visual feedback with color-coded styling
    - State tracking for validation and content history
    """

    def __init__(self):
        # Validation state tracking
        self._is_valid = True
        self._has_had_content = False
        self._max_length = 0

        # Setup initial state
        self._setup_validation_signals()

    def _setup_validation_signals(self) -> None:
        """Setup internal signal connections. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _setup_validation_signals")

    def text(self) -> str:
        """Get current text content. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement text")

    def setText(self, text: str) -> None:
        """Set text content. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement setText")

    def insert(self, text: str) -> None:
        """Insert text at current position. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement insert")

    def setStyleSheet(self, style: str) -> None:
        """Set widget stylesheet. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement setStyleSheet")

    def maxLength(self) -> int:
        """Get maximum length. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement maxLength")

    def emit_validation_changed(self, is_valid: bool) -> None:
        """Emit validation changed signal. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement emit_validation_changed")

    def get_blocked_characters(self) -> Set[str]:
        """
        Get set of characters that should be blocked from input.
        Override in subclasses for field-specific blocking.

        Returns:
            Set of characters to block
        """
        return set()

    def should_block_character(self, char: str) -> bool:
        """
        Check if a character should be blocked from input.

        Args:
            char: Character to check

        Returns:
            bool: True if character should be blocked
        """
        blocked_chars = self.get_blocked_characters()
        return char in blocked_chars

    def clean_text_for_paste(self, text: str) -> Tuple[str, Set[str]]:
        """
        Clean text for paste operations by removing blocked characters.

        Args:
            text: Original text to clean

        Returns:
            Tuple of (cleaned_text, removed_characters)
        """
        blocked_chars = self.get_blocked_characters()
        if not blocked_chars:
            return text, set()

        cleaned_text = ''.join(char for char in text if char not in blocked_chars)
        removed_chars = set(text) - set(cleaned_text)

        return cleaned_text, removed_chars

    def validate_text_content(self, text: str) -> Tuple[bool, str]:
        """
        Validate text content according to field-specific rules.
        Override in subclasses for custom validation logic.

        Args:
            text: Text to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not text:
            return True, ""  # Empty text is generally valid

        # Check length limits
        max_len = self.maxLength()
        if max_len > 0 and len(text) > max_len:
            return False, f"Text exceeds maximum length of {max_len} characters"

        return True, ""

    def handle_key_press_validation(self, event: QKeyEvent) -> bool:
        """
        Handle key press events with validation.

        Args:
            event: The key press event

        Returns:
            bool: True if event should be processed, False if blocked
        """
        try:
            # Allow control characters (backspace, delete, arrow keys, etc.)
            if event.text() == '' or len(event.text()) == 0:
                return True

            # Check if character should be blocked
            if self.should_block_character(event.text()):
                # Show error tooltip for blocked character
                error_msg = f"Character '{event.text()}' is not allowed in this field"
                # Cast self to QWidget for tooltip (safe since concrete classes inherit from QWidget)
                show_error_tooltip(self, error_msg)  # type: ignore

                # Apply temporary error styling
                self._apply_temporary_error_style()

                logger.debug(f"[BaseValidatedInput] Blocked character: '{event.text()}'")
                return False  # Block the character

            return True  # Allow the character

        except Exception as e:
            logger.error(f"[BaseValidatedInput] Error in handle_key_press_validation: {e}")
            return True  # Allow on error to prevent blocking valid input

    def handle_paste_validation(self, text: str) -> str:
        """
        Handle paste operations with validation and cleaning.

        Args:
            text: Text being pasted

        Returns:
            str: Cleaned text to insert
        """
        try:
            cleaned_text, removed_chars = self.clean_text_for_paste(text)

            # Show notification about removed characters
            if removed_chars:
                char_list = ', '.join(f"'{char}'" for char in sorted(removed_chars))
                error_msg = f"Removed invalid characters: {char_list}"
                # Cast self to QWidget for tooltip (safe since concrete classes inherit from QWidget)
                show_error_tooltip(self, error_msg)  # type: ignore

                logger.debug(f"[BaseValidatedInput] Cleaned paste content. Removed: {removed_chars}")

            return cleaned_text

        except Exception as e:
            logger.error(f"[BaseValidatedInput] Error in handle_paste_validation: {e}")
            return text  # Return original text on error

    def update_validation_state(self, text: str) -> None:
        """
        Update validation state and visual styling based on current text.

        Args:
            text: Current text content
        """
        try:
            # Track content history
            if text and not self._has_had_content:
                self._has_had_content = True

            # Validate text content
            is_valid, error_message = self.validate_text_content(text)

            # Update state if changed
            if self._is_valid != is_valid:
                self._is_valid = is_valid
                self.emit_validation_changed(is_valid)

            # Update visual styling
            self._update_visual_styling(text)

        except Exception as e:
            logger.error(f"[BaseValidatedInput] Error in update_validation_state: {e}")

    def _update_visual_styling(self, text: str) -> None:
        """
        Update visual styling based on validation state and content.

        Args:
            text: Current text content
        """
        try:
            # Determine styling based on state
            if not self._is_valid:
                # Invalid state - red border only, normal background
                style = f"""
                    border: 2px solid #ff4444;
                    background-color: {QLABEL_DARK_BG};
                    color: {QLABEL_INFO_TEXT};
                    font-weight: normal;
                """
            elif not text and self._has_had_content:
                # Empty after having content - orange/warning styling
                style = f"""
                    border: 2px solid #FFA500;
                    background-color: {QLABEL_DARK_BG};
                    color: {QLABEL_INFO_TEXT};
                    font-weight: normal;
                """
            elif self.maxLength() > 0 and len(text) >= self.maxLength():
                # At character limit - gray styling
                style = f"""
                    border: 2px solid #808080;
                    background-color: {QLABEL_DARK_BG};
                    color: {QLABEL_INFO_TEXT};
                    font-weight: normal;
                """
            else:
                # Valid state - default styling
                style = f"""
                    border: 1px solid {QLABEL_DARK_BORDER};
                    background-color: {QLABEL_DARK_BG};
                    color: {QLABEL_INFO_TEXT};
                    font-weight: normal;
                """

            self.setStyleSheet(style)

        except Exception as e:
            logger.error(f"[BaseValidatedInput] Error in _update_visual_styling: {e}")

    def _apply_temporary_error_style(self) -> None:
        """Apply temporary error styling for blocked characters."""
        try:
            from utils.timer_manager import schedule_ui_update

            # Apply error style immediately - red border only
            error_style = f"""
                border: 2px solid #ff4444;
                background-color: {QLABEL_DARK_BG};
                color: {QLABEL_INFO_TEXT};
                font-weight: normal;
            """
            self.setStyleSheet(error_style)

            # Revert to normal styling after a short delay
            def revert_style():
                self._update_visual_styling(self.text())

            schedule_ui_update(revert_style, 500)

        except Exception as e:
            logger.error(f"[BaseValidatedInput] Error in _apply_temporary_error_style: {e}")

    def is_valid(self) -> bool:
        """
        Check if current content is valid.

        Returns:
            bool: True if content is valid
        """
        return self._is_valid

    def has_had_content(self) -> bool:
        """
        Check if widget has ever had content (for styling purposes).

        Returns:
            bool: True if widget has had content
        """
        return self._has_had_content

    def reset_validation_state(self) -> None:
        """Reset validation state to initial values."""
        self._is_valid = True
        self._has_had_content = False

    def get_validation_error_message(self) -> str:
        """
        Get current validation error message.

        Returns:
            str: Error message or empty string if valid
        """
        _, error_message = self.validate_text_content(self.text())
        return error_message
