# tests/test_specified_text_module.py

from modules.specified_text_module import SpecifiedTextModule
from tests.mocks import MockFileItem


def test_specified_text_valid():
    data = {"type": "specified_text", "text": "Project_"}
    file_item = MockFileItem(filename="example.txt")
    result = SpecifiedTextModule.apply_from_data(data, file_item)
    assert result == "Project_"


def test_specified_text_trims_whitespace():
    data = {"type": "specified_text", "text": "  MyPrefix  "}
    file_item = MockFileItem(filename="example.txt")
    result = SpecifiedTextModule.apply_from_data(data, file_item)
    assert result == "  MyPrefix  "


def test_specified_text_invalid_characters():
    data = {"type": "specified_text", "text": "Bad/Name"}
    file_item = MockFileItem(filename="example.txt")
    result = SpecifiedTextModule.apply_from_data(data, file_item)
    from config import INVALID_FILENAME_MARKER
    assert result == INVALID_FILENAME_MARKER


def test_specified_text_empty():
    """Test that empty text returns empty string (correct behavior)."""
    data = {"type": "specified_text", "text": ""}
    file_item = MockFileItem(filename="example.txt")
    result = SpecifiedTextModule.apply_from_data(data, file_item)
    assert result == ""  # Empty text should return empty string, not original filename
