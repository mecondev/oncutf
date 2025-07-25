"""
Module: test_metadata.py

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


def test_metadata_from_date_attr():
    data = {"type": "metadata", "field": "date", "category": "metadata_keys"}
    file_item = MockFileItem()
    metadata_cache = {"/mock/path/mockfile.mp3": {"date": "2024-05-12 14:23:10"}}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    # Spaces are replaced with underscores for filename safety
    assert result == "2024-05-12_14_23_10"


def test_metadata_from_metadata_field():
    data = {"type": "metadata", "field": "FileModifyDate", "category": "metadata_keys"}
    file_item = MockFileItem()
    metadata_cache = {"/mock/path/mockfile.mp3": {"FileModifyDate": "2024:05:12 14:23:10+03:00"}}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    # Colons and spaces are replaced with underscores, colons in timezone are also replaced
    assert result == "2024_05_12_14_23_10+03_00"
