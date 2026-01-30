"""Module: test_file_load_manager.py

Author: Michael Economou
Date: 2026-01-04

Test module for FileLoadManager - I/O layer for file loading operations.

Coverage:
- Folder scanning (recursive and non-recursive)
- File loading from paths
- Extension filtering
- FileItem conversion
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        # Create test files
        (tmpdir / "image1.jpg").write_text("fake jpg")
        (tmpdir / "image2.png").write_text("fake png")
        (tmpdir / "video.mp4").write_text("fake video")
        (tmpdir / "document.pdf").write_text("fake pdf")
        (tmpdir / "text.txt").write_text("text file")

        # Create a subdirectory with more files
        subdir = tmpdir / "subdir"
        subdir.mkdir()
        (subdir / "nested1.jpg").write_text("nested jpg")
        (subdir / "nested2.png").write_text("nested png")

        # Create companion files (.xmp)
        (tmpdir / "image1.xmp").write_text("xmp metadata")

        yield tmpdir


@pytest.fixture
def mock_parent_window():
    """Create a mock parent window with required attributes."""
    window = Mock()
    window.context = Mock()
    window.context.set_recursive_mode = Mock()
    window.context.get_recursive_mode = Mock(return_value=False)
    window.context.set_current_folder = Mock()
    window.context.get_current_folder = Mock(return_value=None)
    window.context.file_store = Mock()

    # Mock drag_state port
    window.context.get_manager = Mock(return_value=None)  # Will use injected drag_state

    window.file_model = Mock()
    window.file_table = Mock()
    window.metadata_tree = Mock()
    return window


@pytest.fixture
def mock_drag_state():
    """Create a mock drag state adapter."""
    drag_state = Mock()
    drag_state.is_dragging = Mock(return_value=False)
    drag_state.force_cleanup_drag = Mock()
    drag_state.end_drag_visual = Mock()
    drag_state.clear_drag_state = Mock()
    return drag_state


@pytest.fixture
def manager(mock_parent_window, mock_drag_state):
    """Create FileLoadManager instance with mocked dependencies."""
    from oncutf.core.file.load_manager import FileLoadManager

    # Inject mock drag_state to avoid ApplicationContext dependency
    mgr = FileLoadManager(mock_parent_window, drag_state=mock_drag_state)
    return mgr


class TestFileLoadManagerInit:
    """Test FileLoadManager initialization."""

    def test_init_sets_allowed_extensions(self, manager):
        """Test that initialization sets allowed extensions."""
        assert isinstance(manager.allowed_extensions, set)
        assert len(manager.allowed_extensions) > 0

    def test_init_clears_metadata_operation_flag(self, manager):
        """Test that metadata operation flag starts as False."""
        assert manager._metadata_operation_in_progress is False


class TestIsAllowedExtension:
    """Test extension filtering."""

    def test_allowed_extension_jpg(self, manager):
        """Test that .jpg files are allowed."""
        assert manager._is_allowed_extension("/path/to/file.jpg")

    def test_allowed_extension_png(self, manager):
        """Test that .png files are allowed."""
        assert manager._is_allowed_extension("/path/to/file.png")

    def test_allowed_extension_case_insensitive(self, manager):
        """Test that extension check is case-insensitive."""
        assert manager._is_allowed_extension("/path/to/file.JPG")
        assert manager._is_allowed_extension("/path/to/file.Jpg")

    def test_disallowed_extension(self, manager):
        """Test that unknown extensions are rejected."""
        manager.allowed_extensions = {".jpg", ".png"}
        assert not manager._is_allowed_extension("/path/to/file.xyz")

    def test_no_extension(self, manager):
        """Test files with no extension."""
        manager.allowed_extensions = {".jpg", ".png"}
        assert not manager._is_allowed_extension("/path/to/file")


class TestGetFilesFromFolder:
    """Test folder scanning functionality."""

    def test_get_files_non_recursive(self, manager, temp_dir):
        """Test non-recursive folder scanning."""
        files = manager._get_files_from_folder(str(temp_dir), recursive=False)

        # Should only get files from top level
        file_names = {os.path.basename(f) for f in files}
        assert "image1.jpg" in file_names
        assert "image2.png" in file_names
        assert "video.mp4" in file_names

        # Should NOT get nested files
        assert "nested1.jpg" not in file_names

    def test_get_files_recursive(self, manager, temp_dir):
        """Test recursive folder scanning."""
        files = manager._get_files_from_folder(str(temp_dir), recursive=True)

        # Should get files from all levels
        file_names = {os.path.basename(f) for f in files}
        assert "image1.jpg" in file_names
        assert "nested1.jpg" in file_names
        assert "nested2.png" in file_names

    def test_get_files_respects_allowed_extensions(self, manager, temp_dir):
        """Test that only allowed extensions are returned."""
        manager.allowed_extensions = {".jpg", ".png"}
        files = manager._get_files_from_folder(str(temp_dir), recursive=False)

        # Should only get .jpg and .png files
        for file_path in files:
            ext = os.path.splitext(file_path)[1].lower()
            assert ext in {".jpg", ".png"}

    def test_get_files_empty_directory(self, manager):
        """Test scanning empty directory."""
        with tempfile.TemporaryDirectory() as empty_dir:
            files = manager._get_files_from_folder(empty_dir, recursive=False)
            assert len(files) == 0

    def test_get_files_nonexistent_directory(self, manager):
        """Test scanning nonexistent directory."""
        files = manager._get_files_from_folder("/nonexistent/path", recursive=False)
        assert len(files) == 0


class TestGetFileItemsFromFolder:
    """Test FileItem conversion from folder."""

    def test_get_file_items_creates_file_items(self, manager, temp_dir):
        """Test that FileItems are created from file paths."""
        from oncutf.models.file_item import FileItem

        items = manager.get_file_items_from_folder(str(temp_dir), use_cache=False)

        assert isinstance(items, list)
        assert len(items) > 0

        # All items should be FileItem instances
        for item in items:
            assert isinstance(item, FileItem)

    def test_get_file_items_has_valid_attributes(self, manager, temp_dir):
        """Test that FileItems have valid attributes."""
        items = manager.get_file_items_from_folder(str(temp_dir), use_cache=False)

        for item in items:
            assert item.filename
            assert item.full_path
            assert os.path.isfile(item.full_path)


class TestPrepareFolderLoad:
    """Test folder load preparation."""

    def test_prepare_folder_load_returns_file_paths(self, manager, temp_dir):
        """Test that prepare_folder_load returns list of file paths."""
        paths = manager.prepare_folder_load(str(temp_dir))

        assert isinstance(paths, list)
        assert len(paths) > 0

        for path in paths:
            assert isinstance(path, str)
            assert os.path.isfile(path)

    def test_prepare_folder_load_nonexistent(self, manager):
        """Test prepare_folder_load with nonexistent path."""
        paths = manager.prepare_folder_load("/nonexistent/path")
        assert len(paths) == 0


class TestLoadFolder:
    """Test folder loading orchestration."""

    def test_load_folder_stores_recursive_state(self, manager, temp_dir):
        """Test that load_folder stores recursive state in context."""
        with patch.object(manager, "_load_folder_with_wait_cursor"):
            manager.load_folder(str(temp_dir), merge_mode=False, recursive=True)

            manager.parent_window.context.set_recursive_mode.assert_called_with(True)

    def test_load_folder_merge_mode_preserves_recursive(self, manager, temp_dir):
        """Test that merge mode doesn't change recursive state."""
        with patch.object(manager, "_load_folder_with_wait_cursor"):
            manager.load_folder(str(temp_dir), merge_mode=True, recursive=True)

            # Should NOT call set_recursive_mode in merge mode
            manager.parent_window.context.set_recursive_mode.assert_not_called()

    def test_load_folder_invalid_path_logs_error(self, manager):
        """Test that invalid folder path logs error."""
        with patch("oncutf.core.file.load_manager.logger") as mock_logger:
            manager.load_folder("/not/a/directory")

            # Should log error for invalid directory
            assert mock_logger.error.called


class TestSetAllowedExtensions:
    """Test dynamic extension configuration."""

    def test_set_allowed_extensions(self, manager):
        """Test setting allowed extensions."""
        new_extensions = {".jpg", ".png", ".gif"}
        manager.set_allowed_extensions(new_extensions)

        assert manager.allowed_extensions == new_extensions

    def test_set_allowed_extensions_affects_filtering(self, manager, temp_dir):
        """Test that new extensions affect file filtering."""
        # Set to only allow .jpg
        manager.set_allowed_extensions({".jpg"})

        files = manager._get_files_from_folder(str(temp_dir), recursive=False)

        # Should only get .jpg files
        for file_path in files:
            ext = os.path.splitext(file_path)[1].lower()
            assert ext == ".jpg"


class TestMetadataOperationFlag:
    """Test metadata operation flag handling."""

    def test_clear_metadata_operation_flag(self, manager):
        """Test clearing metadata operation flag."""
        manager._metadata_operation_in_progress = True
        manager.clear_metadata_operation_flag()

        assert manager._metadata_operation_in_progress is False


class TestReloadCurrentFolder:
    """Test folder reload functionality."""

    def test_reload_current_folder_exists(self, manager):
        """Test that reload_current_folder method exists and is callable."""
        # reload_current_folder() has minimal implementation
        manager.reload_current_folder()
        # No exception means success


class TestRefreshLoadedFolders:
    """Test folder refresh after external changes."""

    def test_refresh_loaded_folders_with_no_files(self, manager):
        """Test refresh when no files are loaded."""
        mock_file_store = Mock()
        mock_file_store.get_loaded_files.return_value = []

        result = manager.refresh_loaded_folders(file_store=mock_file_store)

        # Should return False when no files loaded
        assert result is False

    def test_refresh_loaded_folders_with_no_filestore(self, manager):
        """Test refresh when FileStore is not available."""
        manager.parent_window.context = None

        result = manager.refresh_loaded_folders(file_store=None)

        # Should return False when no FileStore available
        assert result is False
