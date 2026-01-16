"""Integration test for Thumbnail Viewport (Phase 3).

Author: Michael Economou
Date: 2026-01-17

Tests the integration of:
- ThumbnailDelegate rendering
- ThumbnailViewportWidget with FileTableModel
- Order mode switching (manual/sorted)
- Zoom and selection
- DB persistence (mock)

Run with: python -m pytest tests/integration/test_thumbnail_viewport_phase3.py -v
"""

import sys
from unittest.mock import Mock, patch

import pytest
from PyQt5.QtWidgets import QApplication

from oncutf.models.file_item import FileItem
from oncutf.models.file_table.file_table_model import FileTableModel
from oncutf.ui.delegates.thumbnail_delegate import ThumbnailDelegate
from oncutf.ui.widgets.thumbnail_viewport import ThumbnailViewportWidget


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def sample_files():
    """Create sample FileItem objects for testing."""
    from datetime import datetime

    files = [
        FileItem("/path/to/image1.jpg", "jpg", datetime.now()),
        FileItem("/path/to/image2.png", "png", datetime.now()),
        FileItem("/path/to/video1.mp4", "mp4", datetime.now()),
        FileItem("/path/to/image3.gif", "gif", datetime.now()),
    ]

    # Set some properties
    files[0].color = "red"
    files[2].duration = 125.5  # Video duration in seconds

    return files


@pytest.fixture
def mock_db_manager():
    """Mock database manager for testing."""
    db_manager = Mock()
    thumbnail_store = Mock()

    # Mock methods
    thumbnail_store.get_folder_order.return_value = None
    thumbnail_store.save_folder_order.return_value = True
    thumbnail_store.clear_folder_order.return_value = True

    db_manager.thumbnail_store = thumbnail_store
    return db_manager


@pytest.fixture
def file_model(sample_files, mock_db_manager):
    """Create FileTableModel with sample files."""
    # Patch get_app_context before creating model
    with patch("oncutf.core.application_context.ApplicationContext.get_instance") as mock_instance:
        mock_app_context = Mock()
        mock_app_context.get_manager.return_value = mock_db_manager
        mock_instance.return_value = mock_app_context

        model = FileTableModel()
        model.files = sample_files.copy()
        model.set_current_folder("/path/to")

        yield model


class TestThumbnailDelegate:
    """Test ThumbnailDelegate rendering."""

    def test_delegate_creation(self, qapp):
        """Test delegate can be created."""
        delegate = ThumbnailDelegate()
        assert delegate is not None
        assert delegate._thumbnail_size == 128  # Default size

    def test_set_thumbnail_size(self, qapp):
        """Test thumbnail size setting."""
        delegate = ThumbnailDelegate()

        delegate.set_thumbnail_size(256)
        assert delegate._thumbnail_size == 256

        delegate.set_thumbnail_size(64)
        assert delegate._thumbnail_size == 64

    def test_size_hint(self, qapp):
        """Test sizeHint calculation."""
        delegate = ThumbnailDelegate()
        delegate.set_thumbnail_size(128)

        # Mock index
        index = Mock()
        option = Mock()

        size = delegate.sizeHint(option, index)

        # Size should include frame + padding + thumbnail + filename
        assert size.width() > 128
        assert size.height() > 128


class TestThumbnailViewportWidget:
    """Test ThumbnailViewportWidget functionality."""

    def test_viewport_creation(self, qapp, file_model):
        """Test viewport widget can be created."""
        viewport = ThumbnailViewportWidget(file_model)
        assert viewport is not None
        assert viewport._model == file_model
        assert viewport._thumbnail_size == viewport.DEFAULT_THUMBNAIL_SIZE

    def test_zoom_in_out(self, qapp, file_model):
        """Test zoom functionality."""
        viewport = ThumbnailViewportWidget(file_model)

        initial_size = viewport.get_thumbnail_size()

        # Zoom in
        viewport.zoom_in()
        assert viewport.get_thumbnail_size() == initial_size + viewport.ZOOM_STEP

        # Zoom out
        viewport.zoom_out()
        assert viewport.get_thumbnail_size() == initial_size

    def test_zoom_limits(self, qapp, file_model):
        """Test zoom respects min/max limits."""
        viewport = ThumbnailViewportWidget(file_model)

        # Zoom to minimum
        viewport.set_thumbnail_size(viewport.MIN_THUMBNAIL_SIZE - 10)
        assert viewport.get_thumbnail_size() == viewport.MIN_THUMBNAIL_SIZE

        # Zoom to maximum
        viewport.set_thumbnail_size(viewport.MAX_THUMBNAIL_SIZE + 10)
        assert viewport.get_thumbnail_size() == viewport.MAX_THUMBNAIL_SIZE

    def test_reset_zoom(self, qapp, file_model):
        """Test zoom reset."""
        viewport = ThumbnailViewportWidget(file_model)

        viewport.set_thumbnail_size(200)
        viewport.reset_zoom()
        assert viewport.get_thumbnail_size() == viewport.DEFAULT_THUMBNAIL_SIZE

    def test_order_mode_delegation(self, qapp, file_model):
        """Test order mode is delegated to model."""
        viewport = ThumbnailViewportWidget(file_model)

        # Initially sorted (model default)
        assert viewport.get_order_mode() == "sorted"

        # Switch to manual
        viewport.set_order_mode("manual")
        assert file_model.order_mode == "manual"

    def test_selection_sync(self, qapp, file_model):
        """Test file selection."""
        viewport = ThumbnailViewportWidget(file_model)

        # Note: Selection won't work fully without proper view/model setup
        # This test just verifies the methods don't crash
        file_paths = ["/path/to/image1.jpg", "/path/to/image2.png"]
        viewport.select_files(file_paths)

        # Can call get_selected_files without crashing
        selected = viewport.get_selected_files()
        assert isinstance(selected, list)

    def test_clear_selection(self, qapp, file_model):
        """Test clearing selection."""
        viewport = ThumbnailViewportWidget(file_model)

        # Select files
        viewport.select_files(["/path/to/image1.jpg"])
        viewport.clear_selection()

        selected = viewport.get_selected_files()
        assert len(selected) == 0


class TestFileTableModelOrderMode:
    """Test FileTableModel order_mode functionality."""

    def test_default_order_mode(self, file_model):
        """Test default order mode is sorted."""
        assert file_model.order_mode == "sorted"

    def test_set_manual_mode(self, file_model, mock_db_manager):
        """Test switching to manual mode."""
        # Note: DB calls will fail gracefully (ApplicationContext not initialized)
        # but order_mode should still change
        file_model.set_order_mode("manual")
        assert file_model.order_mode == "manual"

    def test_set_sorted_mode(self, file_model, mock_db_manager):
        """Test switching to sorted mode."""
        # Note: DB calls will fail gracefully, but sorting should work
        file_model.set_order_mode("sorted", sort_key="filename", reverse=False)
        assert file_model.order_mode == "sorted"

        # Files should be sorted
        filenames = [f.filename for f in file_model.files]
        assert filenames == sorted(filenames)

    def test_save_manual_order(self, file_model, mock_db_manager):
        """Test saving manual order to DB."""
        # Set to manual mode first
        file_model.set_order_mode("manual")

        # Save order (will fail gracefully without ApplicationContext)
        file_model.save_manual_order()

        # No assertion - just verify it doesn't crash

    def test_set_current_folder(self, file_model):
        """Test setting current folder."""
        file_model.set_current_folder("/new/folder")
        assert file_model._current_folder_path == "/new/folder"


class TestIntegration:
    """Integration tests combining viewport + model + delegate."""

    def test_full_workflow(self, qapp, file_model, mock_db_manager):
        """Test complete workflow: create viewport, zoom, change order mode."""
        # Create viewport
        viewport = ThumbnailViewportWidget(file_model)

        # Test zoom
        viewport.zoom_in()
        assert viewport.get_thumbnail_size() == 144

        # Switch to manual mode
        viewport.set_order_mode("manual")
        assert file_model.order_mode == "manual"

        # Simulate drag reorder (trigger layoutChanged)
        file_model.layoutChanged.emit()

        # Verify no crashes (DB save will fail gracefully)

    def test_viewport_with_empty_model(self, qapp, mock_db_manager):
        """Test viewport works with empty model."""
        model = FileTableModel()
        model.files = []

        viewport = ThumbnailViewportWidget(model)
        assert viewport is not None

        # Should handle empty selection
        selected = viewport.get_selected_files()
        assert len(selected) == 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
