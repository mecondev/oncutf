"""
Module: test_validated_line_edit.py

Author: Michael Economou
Date: 2025-05-31

Tests for ValidatedLineEdit widget
"""

import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

import pytest

from config import INVALID_FILENAME_CHARS
from widgets.validated_line_edit import ValidatedLineEdit


class TestValidatedLineEdit:
    """Test suite for ValidatedLineEdit widget"""

    @pytest.fixture(autouse=True)
    def setup_widget(self, qtbot):
        """Setup ValidatedLineEdit widget for each test"""
        self.widget = ValidatedLineEdit()
        qtbot.addWidget(self.widget)
        yield

    def test_valid_character_input(self, qtbot):
        """Test that valid characters are accepted"""
        valid_text = "hello_world123"
        qtbot.keyClicks(self.widget, valid_text)
        assert self.widget.text() == valid_text
        assert self.widget.is_valid() is True

    def test_invalid_character_blocked(self, qtbot):
        """Test that invalid characters are blocked"""
        # Type valid text first
        qtbot.keyClicks(self.widget, "hello")

        # Try to type invalid characters - they should be blocked
        for char in INVALID_FILENAME_CHARS:
            initial_text = self.widget.text()
            qtbot.keyClick(self.widget, char)
            # Text should remain unchanged
            assert self.widget.text() == initial_text

    def test_paste_cleaning(self, qtbot):
        """Test that pasted text with invalid characters is cleaned"""
        # This test would require mocking clipboard operations
        # For now, we'll test the method directly
        from PyQt5.QtCore import QMimeData

        mime_data = QMimeData()
        mime_data.setText("hello<world>")

        # Manually call the method (in real usage this would be called automatically)
        self.widget.insertFromMimeData(mime_data)

        # Should have cleaned the invalid characters
        assert self.widget.text() == "helloworld"

    def test_validation_state_tracking(self, qtbot):
        """Test validation state changes are tracked correctly"""
        # Test that validation state tracking works
        # Note: Signal connection might not work due to inheritance complexity
        # So we test the validation state directly

        # Start with valid text
        qtbot.keyClicks(self.widget, "valid")
        assert self.widget.is_valid() is True

        # Clear to empty (should still be valid for filename input)
        self.widget.clear()
        assert self.widget.is_valid() is True

        # Test that has_had_content tracking works
        qtbot.keyClicks(self.widget, "test")
        self.widget.update_validation_state("test")
        assert self.widget.has_had_content() is True

    def test_reset_validation_state(self, qtbot):
        """Test that validation state is properly reset"""
        # Enter some text and then reset
        qtbot.keyClicks(self.widget, "test")
        self.widget.reset_validation_state()

        assert self.widget.text() == "test"  # Text should remain
        assert self.widget.is_valid() is True
        assert not hasattr(self.widget, "_has_had_content") or not self.widget._has_had_content

    def test_validation_error_message(self, qtbot):
        """Test validation error message generation"""
        # Valid text should have no error message
        qtbot.keyClicks(self.widget, "valid_text")
        assert self.widget.get_validation_error_message() == ""

        # Note: We can't easily test invalid text since it's blocked at input level
        # This would require directly setting the text which bypasses our validation

    def test_max_length_styling(self, qtbot):
        """Test styling when at character limit"""
        self.widget.setMaxLength(5)

        # Type exactly max length
        qtbot.keyClicks(self.widget, "12345")

        # Should have special styling for max length
        style = self.widget.styleSheet()
        assert "#808080" in style  # Should have the gray border for max length

    def test_empty_after_content_styling(self, qtbot):
        """Test styling when field becomes empty after having content"""
        # Type some text
        qtbot.keyClicks(self.widget, "test")

        # Clear the text
        self.widget.clear()

        # Should have orange styling for empty after content
        style = self.widget.styleSheet()
        assert "#FFA500" in style  # Should have orange border
