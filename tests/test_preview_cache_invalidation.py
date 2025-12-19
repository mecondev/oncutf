"""Unit tests for preview cache invalidation behavior.

This module tests that preview caching properly invalidates when:
- Rename module data changes
- Metadata field selection changes
- Files are added/removed from selection

Author: Michael Economou
Date: December 19, 2025
"""

from unittest.mock import MagicMock, patch

import pytest

from oncutf.core.preview_manager import PreviewManager
from oncutf.models.file_item import FileItem


@pytest.fixture
def preview_manager():
    """Create a PreviewManager instance for testing."""
    manager = PreviewManager(parent_window=None)
    return manager


@pytest.fixture
def mock_file_items():
    """Create mock FileItem objects for testing."""
    files = []
    for i in range(3):
        file = MagicMock(spec=FileItem)
        file.full_path = f"/test/path/file{i}.txt"
        file.filename = f"file{i}.txt"
        files.append(file)
    return files


class TestCacheKeyGeneration:
    """Test _generate_cache_key method."""

    def test_cache_key_changes_with_file_paths(self, preview_manager, mock_file_items):
        """Test that cache key changes when file paths change."""
        rename_data = {"modules": [], "post_transform": {}}

        key1 = preview_manager._generate_cache_key(mock_file_items[:2], rename_data)
        key2 = preview_manager._generate_cache_key(mock_file_items, rename_data)

        assert key1 != key2, "Cache key should differ when file list changes"

    def test_cache_key_changes_with_rename_data(self, preview_manager, mock_file_items):
        """Test that cache key changes when rename data changes."""
        data1 = {
            "modules": [{"type": "metadata", "field": "last_modified_yymmdd"}],
            "post_transform": {},
        }
        data2 = {
            "modules": [{"type": "metadata", "field": "DateTimeOriginal"}],
            "post_transform": {},
        }

        key1 = preview_manager._generate_cache_key(mock_file_items, data1)
        key2 = preview_manager._generate_cache_key(mock_file_items, data2)

        assert key1 != key2, "Cache key should differ when metadata field changes"

    def test_cache_key_changes_with_post_transform(self, preview_manager, mock_file_items):
        """Test that cache key changes when post_transform changes."""
        data1 = {"modules": [], "post_transform": {"case": "lower"}}
        data2 = {"modules": [], "post_transform": {"case": "upper"}}

        key1 = preview_manager._generate_cache_key(mock_file_items, data1)
        key2 = preview_manager._generate_cache_key(mock_file_items, data2)

        assert key1 != key2, "Cache key should differ when post_transform changes"

    def test_cache_key_same_for_identical_data(self, preview_manager, mock_file_items):
        """Test that cache key is consistent for identical inputs."""
        rename_data = {"modules": [{"type": "counter", "start": 1}], "post_transform": {}}

        key1 = preview_manager._generate_cache_key(mock_file_items, rename_data)
        key2 = preview_manager._generate_cache_key(mock_file_items, rename_data)

        assert key1 == key2, "Cache key should be same for identical inputs"


class TestCacheClearing:
    """Test cache clearing functionality."""

    def test_clear_cache_empties_preview_cache(self, preview_manager):
        """Test that clear_cache empties the internal cache."""
        # Manually add an entry to the cache
        preview_manager._preview_cache["test_key"] = ([], False, 0.0)

        assert len(preview_manager._preview_cache) == 1

        preview_manager.clear_cache()

        assert len(preview_manager._preview_cache) == 0

    def test_clear_all_caches_clears_everything(self, preview_manager):
        """Test that clear_all_caches clears preview cache and related caches."""
        # Add entry to preview cache
        preview_manager._preview_cache["test_key"] = ([], False, 0.0)

        with (
            patch("oncutf.utils.preview_engine.clear_module_cache") as mock_clear_module,
            patch("oncutf.modules.metadata_module.MetadataModule.clear_cache") as mock_clear_meta,
        ):
            preview_manager.clear_all_caches()

            mock_clear_module.assert_called_once()
            mock_clear_meta.assert_called_once()

        assert len(preview_manager._preview_cache) == 0


class TestCacheInvalidationOnModuleChange:
    """Test that cache properly invalidates when module config changes."""

    def test_metadata_field_change_invalidates_cache(self, preview_manager, mock_file_items):
        """Test that changing metadata field produces different cache key."""
        # Simulate metadata module with file_dates category
        data_file_dates = {
            "modules": [
                {
                    "type": "metadata",
                    "category": "file_dates",
                    "field": "last_modified_yymmdd",
                }
            ],
            "post_transform": {},
        }

        # Simulate metadata module with metadata_keys category
        data_exif = {
            "modules": [
                {
                    "type": "metadata",
                    "category": "metadata_keys",
                    "field": "DateTimeOriginal",
                }
            ],
            "post_transform": {},
        }

        key1 = preview_manager._generate_cache_key(mock_file_items, data_file_dates)
        key2 = preview_manager._generate_cache_key(mock_file_items, data_exif)

        assert key1 != key2, "Changing metadata category/field should produce different cache key"

    def test_module_order_change_invalidates_cache(self, preview_manager, mock_file_items):
        """Test that changing module order produces different cache key."""
        modules_order1 = [
            {"type": "counter", "start": 1},
            {"type": "specified_text", "text": "prefix"},
        ]
        modules_order2 = [
            {"type": "specified_text", "text": "prefix"},
            {"type": "counter", "start": 1},
        ]

        data1 = {"modules": modules_order1, "post_transform": {}}
        data2 = {"modules": modules_order2, "post_transform": {}}

        key1 = preview_manager._generate_cache_key(mock_file_items, data1)
        key2 = preview_manager._generate_cache_key(mock_file_items, data2)

        assert key1 != key2, "Changing module order should produce different cache key"
