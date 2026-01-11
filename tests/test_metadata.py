"""Module: test_metadata.py

Author: Michael Economou
Date: 2025-05-12

This module provides functionality for the oncutf batch file renaming application.
Tests work cross-platform with Greek characters and Windows/Linux paths.
"""

import warnings

from oncutf.modules.metadata_module import MetadataModule
from oncutf.utils.filesystem.path_normalizer import normalize_path
from tests.mocks import MockFileItem

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)


def test_metadata_from_date_attr():
    file_item = MockFileItem()
    normalized = normalize_path(file_item.full_path)
    metadata_cache = {normalized: {"date": "2024-05-12 14:23:10"}}

    data = {"type": "metadata", "field": "date", "category": "metadata_keys"}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    # Spaces are replaced with underscores for filename safety
    assert result == "2024-05-12_14_23_10"


def test_metadata_from_metadata_field():
    file_item = MockFileItem()
    normalized = normalize_path(file_item.full_path)
    metadata_cache = {normalized: {"FileModifyDate": "2024:05:12 14:23:10+03:00"}}

    data = {"type": "metadata", "field": "FileModifyDate", "category": "metadata_keys"}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    # Colons and spaces are replaced with underscores, colons in timezone are also replaced
    assert result == "2024_05_12_14_23_10+03_00"
