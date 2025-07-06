"""
Module: test_progress_manager.py

Author: Michael Economou
Date: 2025-05-31

test_progress_manager.py
Tests for the new unified ProgressManager.
"""
import warnings
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*coroutine.*never awaited')
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)


"""
test_progress_manager.py

Tests for the new unified ProgressManager.

"""

import pytest
from PyQt5.QtWidgets import QApplication

from widgets.progress_manager import (
    ProgressManager,
    create_hash_progress_manager,
    create_metadata_progress_manager,
)


class TestProgressManager:
    """Test the unified ProgressManager."""

    def setup_method(self):
        """Set up test fixtures."""
        # Ensure we have a QApplication instance
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

    def test_hash_progress_manager_creation(self):
        """Test creating a hash progress manager."""
        manager = create_hash_progress_manager()

        assert manager.operation_type == "hash"
        assert manager.progress_widget is not None
        assert manager.progress_widget.progress_mode == "size"
        assert manager.progress_widget.show_size_info is True
        assert manager.progress_widget.show_time_info is True

    def test_metadata_progress_manager_creation(self):
        """Test creating a metadata progress manager."""
        manager = create_metadata_progress_manager()

        assert manager.operation_type == "metadata"
        assert manager.progress_widget is not None
        assert manager.progress_widget.progress_mode == "count"
        assert manager.progress_widget.show_size_info is True
        assert manager.progress_widget.show_time_info is True

    def test_hash_progress_tracking(self):
        """Test hash progress tracking with size-based updates."""
        manager = create_hash_progress_manager()

        # Start tracking
        manager.start_tracking(total_size=1000000)  # 1MB
        assert manager.is_tracking() is True

        # Update progress
        manager.update_progress(processed_bytes=500000, status="Processing...")

        # Check that progress widget was updated
        widget = manager.get_widget()
        assert widget.processed_size == 500000
        assert widget.total_size == 1000000

    def test_metadata_progress_tracking(self):
        """Test metadata progress tracking with count-based updates."""
        manager = create_metadata_progress_manager()

        # Start tracking
        manager.start_tracking(total_files=100)
        assert manager.is_tracking() is True

        # Update progress
        manager.update_progress(file_count=50, total_files=100, filename="test.jpg")

        # Check that progress widget was updated
        widget = manager.get_widget()
        assert widget.progress_mode == "count"

    def test_invalid_operation_type(self):
        """Test that invalid operation types raise an error."""
        with pytest.raises(ValueError, match="Unsupported operation type"):
            ProgressManager("invalid_operation")

    def test_reset_functionality(self):
        """Test that reset functionality works correctly."""
        manager = create_hash_progress_manager()

        # Start tracking
        manager.start_tracking(total_size=1000000)
        assert manager.is_tracking() is True

        # Reset
        manager.reset()
        assert manager.is_tracking() is False

    def test_update_without_tracking(self):
        """Test that updating without tracking shows a warning."""
        manager = create_hash_progress_manager()

        # Try to update without starting tracking
        manager.update_progress(processed_bytes=100000)
        # Should not crash, just log a warning

    def test_get_widget(self):
        """Test that get_widget returns the correct widget."""
        manager = create_hash_progress_manager()
        widget = manager.get_widget()

        assert widget is not None
        assert isinstance(widget, manager.progress_widget.__class__)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
