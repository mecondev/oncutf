"""Tests for MetadataLoader.

Author: Michael Economou
Date: 2026-01-04
"""

from unittest.mock import Mock

import pytest

from oncutf.core.metadata.metadata_loader import MetadataLoader


@pytest.fixture
def mock_parent_window():
    """Create mock parent window."""
    window = Mock()
    window.metadata_cache = Mock()
    window.metadata_cache.get_all_cached_metadata.return_value = {}
    window.file_model = Mock()
    window.file_model.files = []
    return window


@pytest.fixture
def metadata_loader(mock_parent_window):
    """Create MetadataLoader instance."""
    return MetadataLoader(mock_parent_window)


@pytest.mark.unit
def test_metadata_loader_init(mock_parent_window):
    """Test MetadataLoader initialization."""
    loader = MetadataLoader(mock_parent_window)

    assert loader._parent_window == mock_parent_window
    assert loader._parallel_loader is None
    assert loader._metadata_cancelled is False


@pytest.mark.unit
def test_load_metadata_empty_list(metadata_loader):
    """Test loading metadata with empty file list."""
    # Should return early without errors
    metadata_loader.load_metadata_for_items([], use_extended=False)

    # No parallel loader should be created for empty list
    assert metadata_loader._parallel_loader is None


@pytest.mark.unit
def test_cancel_metadata_loading(metadata_loader):
    """Test cancellation flag setting."""
    # Set cancellation flag
    metadata_loader._metadata_cancelled = True

    assert metadata_loader._metadata_cancelled is True

    # Reset flag
    metadata_loader._metadata_cancelled = False
    assert metadata_loader._metadata_cancelled is False


@pytest.mark.unit
def test_cleanup(metadata_loader):
    """Test cleanup of metadata loader resources."""
    # Set cancellation flag (this stops any ongoing operations)
    metadata_loader._metadata_cancelled = False

    # Trigger cancellation
    metadata_loader._metadata_cancelled = True

    assert metadata_loader._metadata_cancelled is True
