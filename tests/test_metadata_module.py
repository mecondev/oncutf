"""
Module: test_metadata_module.py

Author: Michael Economou
Date: 2025-05-31

This module provides functionality for the OnCutF batch file renaming application.
"""

import warnings

from modules.metadata_module import MetadataModule
from tests.mocks import MockFileItem

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)


# Clear metadata cache before each test to avoid interference
def setup_function(function):  # noqa: ARG001
    MetadataModule.clear_cache()


def test_metadata_module_basic():
    data = {"type": "metadata", "field": "date", "category": "metadata_keys"}
    file_item = MockFileItem()
    metadata_cache = {"/mock/path/mockfile.mp3": {"date": "2024-01-01 15:30:00"}}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    # Spaces are replaced with underscores for filename safety
    assert result == "2024-01-01_15_30_00"


def test_metadata_module_missing_field():
    data = {"type": "metadata", "field": "location", "category": "metadata_keys"}
    file_item = MockFileItem()
    metadata_cache = {"/mock/path/mockfile.mp3": {"date": "2024-01-01"}}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    # When metadata field is missing, fallback to original filename (without extension)
    assert result == "mockfile"


def test_metadata_module_metadata_dict():
    data = {"type": "metadata", "field": "date", "category": "metadata_keys"}
    file_item = MockFileItem()
    metadata_cache = {
        "/mock/path/mockfile.mp3": {
            "FileModifyDate": "2024:01:01 15:30:00",
            "date": "2024-01-01 15:30:00",
        },
    }
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    # Spaces are replaced with underscores for filename safety
    assert result == "2024-01-01_15_30_00"


def test_metadata_module_exif_style_date():
    data = {"type": "metadata", "field": "DateTimeOriginal", "category": "metadata_keys"}
    file_item = MockFileItem()
    metadata_cache = {"/mock/path/mockfile.mp3": {"DateTimeOriginal": "2024:05:12 10:00:00"}}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    # Colons and spaces are replaced with underscores for filename safety
    assert result == "2024_05_12_10_00_00"


def test_metadata_module_invalid_date_format():
    data = {"type": "metadata", "field": "FileModifyDate", "category": "metadata_keys"}
    file_item = MockFileItem()
    metadata_cache = {"/mock/path/mockfile.mp3": {"FileModifyDate": "12-05-2024 10:00"}}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    # Spaces are replaced with underscores for filename safety
    assert result == "12-05-2024_10_00"


def test_metadata_module_date_with_timezone():
    data = {"type": "metadata", "field": "FileModifyDate", "category": "metadata_keys"}
    file_item = MockFileItem()
    metadata_cache = {"/mock/path/mockfile.mp3": {"FileModifyDate": "2024-05-12 10:00:00+03:00"}}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    # Colons and spaces are replaced with underscores for filename safety
    assert result == "2024-05-12_10_00_00+03_00"


def test_metadata_module_unknown_field_type():
    data = {"type": "metadata", "field": "Model", "category": "metadata_keys"}
    file_item = MockFileItem()
    metadata_cache = {"/mock/path/mockfile.mp3": {"Model": "Canon"}}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    # Simple text values should remain unchanged
    assert result == "Canon"


def test_metadata_module_with_cache_priority():
    data = {"type": "metadata", "field": "FileModifyDate", "category": "metadata_keys"}
    file_item = MockFileItem(filename="cached.mp3")
    cache = {"/mock/path/cached.mp3": {"FileModifyDate": "2023:12:25 11:22:33"}}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=cache)
    # Colons and spaces are replaced with underscores for filename safety
    assert result == "2023_12_25_11_22_33"


def test_metadata_module_cache_fallback_to_file_metadata():
    data = {"type": "metadata", "field": "FileModifyDate", "category": "metadata_keys"}
    file_item = MockFileItem(filename="uncached.mp3")
    cache = {}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=cache)
    # When metadata is not cached, fallback to original filename (without extension)
    assert result == "uncached"
