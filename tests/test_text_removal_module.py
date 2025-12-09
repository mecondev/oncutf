"""
Test module for TextRemovalModule.

Author: Michael Economou
Date: 2025-05-01
"""

from unittest.mock import Mock

import pytest

from modules.text_removal_module import TextRemovalModule


class TestTextRemovalModule:
    """Test cases for TextRemovalModule."""

    def test_remove_from_end(self):
        """Test removing text from the end of filename."""
        # Create a mock file item
        file_item = Mock()
        file_item.filename = "document_copy.txt"

        # Test data for removing "_copy" from end
        data = {"text_to_remove": "_copy", "position": "End of name", "case_sensitive": False}

        result = TextRemovalModule.apply_from_data(data, file_item, 0)
        assert result == "document.txt"

    def test_remove_from_start(self):
        """Test removing text from the start of filename."""
        file_item = Mock()
        file_item.filename = "backup_document.txt"

        data = {"text_to_remove": "backup_", "position": "Start of name", "case_sensitive": False}

        result = TextRemovalModule.apply_from_data(data, file_item, 0)
        assert result == "document.txt"

    def test_remove_anywhere_first(self):
        """Test removing first occurrence anywhere in filename."""
        file_item = Mock()
        file_item.filename = "test_old_file_old.txt"

        data = {"text_to_remove": "_old", "position": "Anywhere (first)", "case_sensitive": False}

        result = TextRemovalModule.apply_from_data(data, file_item, 0)
        assert result == "test_file_old.txt"

    def test_remove_anywhere_all(self):
        """Test removing all occurrences anywhere in filename."""
        file_item = Mock()
        file_item.filename = "test_old_file_old.txt"

        data = {"text_to_remove": "_old", "position": "Anywhere (all)", "case_sensitive": False}

        result = TextRemovalModule.apply_from_data(data, file_item, 0)
        assert result == "test_file.txt"

    def test_case_sensitive(self):
        """Test case sensitive removal."""
        file_item = Mock()
        file_item.filename = "Document_COPY.txt"

        # Case sensitive - should not match
        data = {"text_to_remove": "_copy", "position": "End of name", "case_sensitive": True}

        result = TextRemovalModule.apply_from_data(data, file_item, 0)
        assert result == "Document_COPY.txt"  # Unchanged

        # Case insensitive - should match
        data["case_sensitive"] = False
        result = TextRemovalModule.apply_from_data(data, file_item, 0)
        assert result == "Document.txt"

    def test_text_not_found(self):
        """Test when text to remove is not found."""
        file_item = Mock()
        file_item.filename = "document.txt"

        data = {"text_to_remove": "_copy", "position": "End of name", "case_sensitive": False}

        result = TextRemovalModule.apply_from_data(data, file_item, 0)
        assert result == "document.txt"  # Unchanged

    def test_empty_text_to_remove(self):
        """Test with empty text to remove."""
        file_item = Mock()
        file_item.filename = "document_copy.txt"

        data = {"text_to_remove": "", "position": "End of name", "case_sensitive": False}

        result = TextRemovalModule.apply_from_data(data, file_item, 0)
        assert result == "document_copy.txt"  # Unchanged

    def test_is_effective(self):
        """Test is_effective method."""
        # Effective - has text to remove
        data = {"text_to_remove": "_copy"}
        assert TextRemovalModule.is_effective(data)

        # Not effective - empty text
        data = {"text_to_remove": ""}
        assert not TextRemovalModule.is_effective(data)

        # Not effective - only spaces
        data = {"text_to_remove": "   "}
        assert not TextRemovalModule.is_effective(data)

    def test_no_extension(self):
        """Test with filename without extension."""
        file_item = Mock()
        file_item.filename = "document_copy"

        data = {"text_to_remove": "_copy", "position": "End of name", "case_sensitive": False}

        result = TextRemovalModule.apply_from_data(data, file_item, 0)
        assert result == "document"

    def test_complex_patterns(self):
        """Test with complex patterns like numbers."""
        file_item = Mock()
        file_item.filename = "document_001.txt"

        data = {"text_to_remove": "_001", "position": "End of name", "case_sensitive": False}

        result = TextRemovalModule.apply_from_data(data, file_item, 0)
        assert result == "document.txt"


if __name__ == "__main__":
    pytest.main([__file__])
