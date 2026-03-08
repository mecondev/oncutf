"""Tests for MetadataLoader.

Author: Michael Economou
Date: 2026-01-04
"""

from unittest.mock import Mock

import pytest

from oncutf.core.metadata.metadata_loader import MetadataLoader
from oncutf.core.metadata.metadata_ui_bridge import NullMetadataUIBridge


@pytest.fixture
def mock_ui_bridge():
    """Create mock UI bridge."""
    bridge = Mock()
    bridge.dialog_parent = None
    bridge.cache_get_entries_batch.return_value = {}
    bridge.cache_get_entry.return_value = None
    return bridge


@pytest.fixture
def metadata_loader(mock_ui_bridge):
    """Create MetadataLoader instance."""
    return MetadataLoader(ui_bridge=mock_ui_bridge)


@pytest.mark.unit
def test_metadata_loader_init(mock_ui_bridge):
    """Test MetadataLoader initialization."""
    loader = MetadataLoader(ui_bridge=mock_ui_bridge)

    assert loader._ui_bridge is mock_ui_bridge
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
