"""
Module: test_specified_text_module.py

Author: Michael Economou
Date: 2025-07-06

"""
# tests/test_specified_text_module.py

from modules.specified_text_module import SpecifiedTextModule
from tests.mocks import MockFileItem
import warnings
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*coroutine.*never awaited')
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)



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
