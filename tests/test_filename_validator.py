"""
Module: test_filename_validator.py

Author: Michael Economou
Date: 2025-05-31

Tests for filename validation utilities
"""
import warnings
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*coroutine.*never awaited')
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)


"""
Tests for filename validation utilities

"""

from config import INVALID_FILENAME_CHARS, INVALID_FILENAME_MARKER
from utils.filename_validator import (
    clean_and_validate,
    clean_filename_text,
    clean_trailing_chars,
    get_validation_error_message,
    is_valid_filename_char,
    is_validation_error_marker,
    prepare_final_filename,
    should_allow_character_input,
    validate_filename_part,
)


class TestFilenameValidator:
    """Test suite for filename validation utilities"""

    def test_is_valid_filename_char(self):
        """Test character validation"""
        # Valid characters
        assert is_valid_filename_char('a') is True
        assert is_valid_filename_char('Z') is True
        assert is_valid_filename_char('1') is True
        assert is_valid_filename_char('_') is True
        assert is_valid_filename_char('-') is True
        assert is_valid_filename_char(' ') is True

        # Invalid characters
        for char in INVALID_FILENAME_CHARS:
            assert is_valid_filename_char(char) is False

    def test_clean_filename_text(self):
        """Test text cleaning functionality"""
        # Clean text should remain unchanged
        assert clean_filename_text("hello_world") == "hello_world"

        # Text with invalid characters should be cleaned
        assert clean_filename_text("hello<world>") == "helloworld"
        assert clean_filename_text("file:name") == "filename"
        assert clean_filename_text("bad/file\\name") == "badfilename"

        # Mixed valid and invalid
        assert clean_filename_text("good_file<bad>name") == "good_filebadname"

    def test_clean_trailing_chars(self):
        """Test trailing character removal"""
        # No trailing chars - should remain unchanged
        assert clean_trailing_chars("filename") == "filename"

        # Trailing spaces
        assert clean_trailing_chars("filename   ") == "filename"

        # Trailing dots
        assert clean_trailing_chars("filename...") == "filename"

        # Mixed trailing chars
        assert clean_trailing_chars("filename . ") == "filename"

        # Internal dots/spaces should remain
        assert clean_trailing_chars("file.name with spaces") == "file.name with spaces"

    def test_validate_filename_part(self):
        """Test complete filename validation"""
        # Valid filename
        is_valid, result = validate_filename_part("valid_filename")
        assert is_valid is True
        assert result == "valid_filename"

        # Invalid characters
        is_valid, result = validate_filename_part("invalid<file>")
        assert is_valid is False
        assert result == INVALID_FILENAME_MARKER

        # Empty filename
        is_valid, result = validate_filename_part("")
        assert is_valid is False
        assert result == INVALID_FILENAME_MARKER

        # Trailing characters that get cleaned
        is_valid, result = validate_filename_part("filename   ")
        assert is_valid is True
        assert result == "filename"

        # Windows reserved names
        for reserved in ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'LPT1']:
            is_valid, result = validate_filename_part(reserved)
            assert is_valid is False
            assert result == INVALID_FILENAME_MARKER

            # Case insensitive
            is_valid, result = validate_filename_part(reserved.lower())
            assert is_valid is False
            assert result == INVALID_FILENAME_MARKER

    def test_should_allow_character_input(self):
        """Test input character filtering"""
        # Should allow valid characters
        assert should_allow_character_input('a') is True
        assert should_allow_character_input('1') is True
        assert should_allow_character_input('_') is True

        # Should block invalid characters
        for char in INVALID_FILENAME_CHARS:
            assert should_allow_character_input(char) is False

    def test_get_validation_error_message(self):
        """Test error message generation"""
        # Valid filename
        assert get_validation_error_message("valid_file") == "Invalid filename"  # Default message for valid

        # Empty filename
        assert "empty" in get_validation_error_message("").lower()

        # Invalid characters
        error_msg = get_validation_error_message("file<name>")
        assert "invalid characters" in error_msg.lower()
        assert "<" in error_msg and ">" in error_msg

        # Trailing characters
        error_msg = get_validation_error_message("filename   ")
        assert "spaces" in error_msg.lower() or "dots" in error_msg.lower()

        # Reserved names
        error_msg = get_validation_error_message("CON")
        assert "reserved" in error_msg.lower()

    def test_is_validation_error_marker(self):
        """Test validation error marker detection"""
        # Should detect the marker
        assert is_validation_error_marker(INVALID_FILENAME_MARKER) is True

        # Should not detect normal text
        assert is_validation_error_marker("normal_filename") is False
        assert is_validation_error_marker("") is False

        # Should detect text ending with marker
        assert is_validation_error_marker("some_text" + INVALID_FILENAME_MARKER) is True

    def test_clean_and_validate(self):
        """Test combined cleaning and validation"""
        # Valid text
        is_valid, result, error = clean_and_validate("valid_text")
        assert is_valid is True
        assert result == "valid_text"
        assert error == ""

        # Text needing cleaning
        is_valid, result, error = clean_and_validate("text<with>invalid")
        assert is_valid is True
        assert result == "textwithinvalid"  # After cleaning should be valid
        assert error == ""

        # Text that's invalid even after cleaning (e.g., becomes empty)
        is_valid, result, error = clean_and_validate("<<<>>>")
        assert is_valid is False
        assert result == INVALID_FILENAME_MARKER
        assert error != ""

    def test_prepare_final_filename(self):
        """Test final filename preparation"""
        # Basic filename with extension
        result = prepare_final_filename("filename", ".txt")
        assert result == "filename.txt"

        # Extension without dot
        result = prepare_final_filename("filename", "jpg")
        assert result == "filename.jpg"

        # No extension
        result = prepare_final_filename("filename", "")
        assert result == "filename"

        # Trailing characters should be cleaned
        result = prepare_final_filename("filename   ", ".txt")
        assert result == "filename.txt"

        # Trailing dots should be cleaned
        result = prepare_final_filename("filename...", ".txt")
        assert result == "filename.txt"
