"""
Module: test_metadata_module.py

Author: Michael Economou
Date: 2025-05-12

Cross-platform metadata module tests - Windows/Linux/Greek compatible.
"""

import warnings

from oncutf.modules.metadata_module import MetadataModule
from tests.mocks import MockFileItem
from oncutf.utils.path_normalizer import normalize_path

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)


# Clear metadata cache before each test to avoid interference
def setup_function(function):  # noqa: ARG001
    MetadataModule.clear_cache()


def test_metadata_module_basic():
    file_item = MockFileItem()
    normalized = normalize_path(file_item.full_path)
    metadata_cache = {normalized: {"date": "2024-01-01 15:30:00"}}

    data = {"type": "metadata", "field": "date", "category": "metadata_keys"}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    assert result == "2024-01-01_15_30_00"


def test_metadata_module_missing_field():
    file_item = MockFileItem()
    normalized = normalize_path(file_item.full_path)
    metadata_cache = {normalized: {"date": "2024-01-01"}}

    data = {"type": "metadata", "field": "location", "category": "metadata_keys"}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    # When metadata field is missing, fallback to original filename (without extension)
    assert result == "mockfile"


def test_metadata_module_metadata_dict():
    file_item = MockFileItem()
    normalized = normalize_path(file_item.full_path)
    metadata_cache = {
        normalized: {
            "FileModifyDate": "2024:01:01 15:30:00",
            "date": "2024-01-01 15:30:00",
        },
    }

    data = {"type": "metadata", "field": "date", "category": "metadata_keys"}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    assert result == "2024-01-01_15_30_00"


def test_metadata_module_exif_style_date():
    file_item = MockFileItem()
    normalized = normalize_path(file_item.full_path)
    metadata_cache = {normalized: {"DateTimeOriginal": "2024:05:12 10:00:00"}}

    data = {"type": "metadata", "field": "DateTimeOriginal", "category": "metadata_keys"}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    assert result == "2024_05_12_10_00_00"


def test_metadata_module_invalid_date_format():
    file_item = MockFileItem()
    normalized = normalize_path(file_item.full_path)
    metadata_cache = {normalized: {"FileModifyDate": "12-05-2024 10:00"}}

    data = {"type": "metadata", "field": "FileModifyDate", "category": "metadata_keys"}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    assert result == "12-05-2024_10_00"


def test_metadata_module_date_with_timezone():
    file_item = MockFileItem()
    normalized = normalize_path(file_item.full_path)
    metadata_cache = {normalized: {"FileModifyDate": "2024-05-12 10:00:00+03:00"}}

    data = {"type": "metadata", "field": "FileModifyDate", "category": "metadata_keys"}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    assert result == "2024-05-12_10_00_00+03_00"


def test_metadata_module_unknown_field_type():
    file_item = MockFileItem()
    normalized = normalize_path(file_item.full_path)
    metadata_cache = {normalized: {"Model": "Canon"}}

    data = {"type": "metadata", "field": "Model", "category": "metadata_keys"}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    assert result == "Canon"


def test_metadata_module_with_cache_priority():
    file_item = MockFileItem(filename="cached.mp3")
    normalized = normalize_path(file_item.full_path)
    cache = {normalized: {"FileModifyDate": "2023:12:25 11:22:33"}}

    data = {"type": "metadata", "field": "FileModifyDate", "category": "metadata_keys"}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=cache)
    assert result == "2023_12_25_11_22_33"


def test_metadata_module_cache_fallback_to_file_metadata():
    file_item = MockFileItem(filename="uncached.mp3")
    cache = {}

    data = {"type": "metadata", "field": "FileModifyDate", "category": "metadata_keys"}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=cache)
    assert result == "uncached"
