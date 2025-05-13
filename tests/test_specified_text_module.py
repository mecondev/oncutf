# tests/test_specified_text_module.py

import pytest
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
    assert result == "MyPrefix"


def test_specified_text_invalid_characters():
    data = {"type": "specified_text", "text": "Bad/Name"}
    file_item = MockFileItem(filename="example.txt")
    result = SpecifiedTextModule.apply_from_data(data, file_item)
    assert result == "invalid"


def test_specified_text_empty():
    data = {"type": "specified_text", "text": ""}
    file_item = MockFileItem(filename="example.txt")
    result = SpecifiedTextModule.apply_from_data(data, file_item)
    assert result == "invalid"
