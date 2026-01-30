"""Tests for HashLoadingService.

Author: Michael Economou
Date: 2026-01-04
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from oncutf.models.file_item import FileItem
from oncutf.ui.managers.hash_loading_service import HashLoadingService


@pytest.fixture
def mock_parent_window():
    """Create mock parent window."""
    window = Mock()
    window.file_model = Mock()
    window.file_model.files = []
    window.file_model.refresh_icon_for_file = Mock()
    return window


@pytest.fixture
def hash_service(mock_parent_window):
    """Create HashLoadingService instance."""
    return HashLoadingService(mock_parent_window, cache_service=None)


@pytest.mark.unit
def test_hash_service_init(mock_parent_window):
    """Test HashLoadingService initialization."""
    service = HashLoadingService(mock_parent_window, cache_service=None)

    assert service.parent_window == mock_parent_window
    assert service._cache_service is None
    assert service._currently_loading == set()
    assert service._hash_worker is None
    assert service._hash_progress_dialog is None


@pytest.mark.unit
def test_load_hashes_empty_list(hash_service):
    """Test loading hashes with empty file list."""
    # Should return early without error
    hash_service.load_hashes_for_files([])

    assert len(hash_service._currently_loading) == 0


@pytest.mark.unit
def test_load_hashes_callbacks_stored(hash_service):
    """Test that callbacks are stored correctly."""
    file_item = FileItem("/test/file.txt", "txt", datetime.now())

    on_finished = Mock()
    on_file_hash = Mock()
    on_progress = Mock()

    with (
        patch.object(hash_service, "_show_hash_progress_dialog"),
        patch.object(hash_service, "_start_hash_loading"),
    ):
        hash_service.load_hashes_for_files(
            [file_item],
            on_finished_callback=on_finished,
            on_file_hash_callback=on_file_hash,
            on_progress_callback=on_progress,
        )

    assert hash_service._on_finished_callback == on_finished
    assert hash_service._on_file_hash_callback == on_file_hash
    assert hash_service._on_progress_callback == on_progress


@pytest.mark.unit
def test_cancel_loading(hash_service):
    """Test cancellation of hash loading."""
    mock_worker = Mock()
    hash_service._hash_worker = mock_worker

    hash_service.cancel_loading()

    mock_worker.cancel.assert_called_once()


@pytest.mark.unit
def test_cleanup(hash_service):
    """Test cleanup of hash service resources."""
    mock_worker = Mock()
    mock_dialog = Mock()

    hash_service._hash_worker = mock_worker
    hash_service._hash_progress_dialog = mock_dialog
    hash_service._currently_loading = {"/test/file1.txt", "/test/file2.txt"}

    hash_service.cleanup()

    # Worker is cleaned up
    assert hash_service._hash_worker is None
    # Currently loading is cleared
    assert len(hash_service._currently_loading) == 0
    # Dialog stays in memory (this is by design - UI owns it)


@pytest.mark.unit
def test_on_file_hash_calculated_with_callback(hash_service):
    """Test file hash calculated with custom callback."""
    callback = Mock()
    hash_service._on_file_hash_callback = callback
    hash_service._currently_loading = {"/test/file.txt"}

    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.getsize", return_value=1024),
    ):
        hash_service._on_file_hash_calculated("/test/file.txt", "abc123")

    callback.assert_called_once_with("/test/file.txt", "abc123", 1024)
    assert "/test/file.txt" not in hash_service._currently_loading


@pytest.mark.unit
def test_update_hash_dialog_with_progress_callback(hash_service):
    """Test update hash dialog with custom progress callback."""
    callback = Mock()
    hash_service._on_progress_callback = callback

    mock_dialog = Mock()

    hash_service._update_hash_dialog(mock_dialog, 5, 10, "file.txt")

    mock_dialog.update_progress.assert_called_once_with(file_count=5, total_files=10)
    mock_dialog.set_count.assert_called_once_with(5, 10)
    mock_dialog.set_filename.assert_called_once_with("file.txt")
    callback.assert_called_once_with(5, 10, "file.txt")


@pytest.mark.unit
def test_on_hash_finished_with_callback(hash_service):
    """Test hash finished with custom callback."""
    callback = Mock()
    hash_service._on_finished_callback = callback
    hash_service._hash_worker = Mock()
    hash_service._hash_progress_dialog = Mock()

    hash_service._on_hash_finished()

    callback.assert_called_once()
    assert hash_service._hash_worker is None
