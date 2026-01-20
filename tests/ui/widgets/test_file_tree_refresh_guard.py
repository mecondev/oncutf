"""Tests for Windows-specific file tree refresh behavior.

Author: Michael Economou
Date: 2024-12-31

Tests the fix for infinite loop in directory change refresh.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from PyQt5.QtWidgets import QApplication

from oncutf.ui.widgets.file_tree import FileTreeView


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def file_tree_view(qtbot):
    """Create a FileTreeView instance for testing."""
    view = FileTreeView()
    qtbot.addWidget(view)
    return view


class TestFileTreeRefreshGuard:
    """Test the refresh guard mechanism that prevents infinite loops."""

    def test_refresh_flag_prevents_recursive_calls(self, file_tree_view, temp_dir):
        """Test that _refresh_in_progress flag prevents recursive directory change events."""
        from oncutf.ui.widgets.custom_file_system_model import CustomFileSystemModel

        # Setup: create a real model and properly set it
        model = CustomFileSystemModel()
        model.setRootPath(temp_dir)
        file_tree_view.setModel(model)

        # Track how many times refresh is called
        refresh_call_count = 0
        original_refresh = model.refresh

        def mock_refresh(*args, **kwargs):
            nonlocal refresh_call_count
            refresh_call_count += 1
            # Simulate Windows behavior: trigger another directory change during refresh
            if refresh_call_count == 1:
                file_tree_view._on_directory_changed(temp_dir)
            return original_refresh(*args, **kwargs)

        model.refresh = mock_refresh

        # Trigger directory change
        file_tree_view._on_directory_changed(temp_dir)

        # Assert: refresh should only be called once (not twice due to recursion)
        assert refresh_call_count == 1, "Refresh was called recursively despite guard flag"

    def test_refresh_flag_resets_after_success(self, file_tree_view, temp_dir):
        """Test that _refresh_in_progress flag is reset after successful refresh."""
        from oncutf.ui.widgets.custom_file_system_model import CustomFileSystemModel

        model = CustomFileSystemModel()
        model.setRootPath(temp_dir)
        file_tree_view.setModel(model)

        # Initially flag should be False
        assert file_tree_view._refresh_in_progress is False

        # Trigger directory change
        file_tree_view._on_directory_changed(temp_dir)

        # After refresh completes, flag should be False again
        assert file_tree_view._refresh_in_progress is False

    def test_refresh_flag_resets_after_exception(self, file_tree_view, temp_dir):
        """Test that _refresh_in_progress flag is reset even if refresh fails."""
        from oncutf.ui.widgets.custom_file_system_model import CustomFileSystemModel

        model = CustomFileSystemModel()
        model.setRootPath(temp_dir)
        file_tree_view.setModel(model)

        # Replace refresh with version that raises exception
        def failing_refresh(*_args, **_kwargs):
            raise RuntimeError("Simulated refresh error")

        model.refresh = failing_refresh

        # Initially flag should be False
        assert file_tree_view._refresh_in_progress is False

        # Trigger directory change (will fail due to exception)
        file_tree_view._on_directory_changed(temp_dir)

        # Even after exception, flag should be False (finally block works)
        assert file_tree_view._refresh_in_progress is False

    def test_multiple_rapid_directory_changes(self, file_tree_view, temp_dir):
        """Test that multiple rapid directory changes are handled correctly."""
        from oncutf.ui.widgets.custom_file_system_model import CustomFileSystemModel

        model = CustomFileSystemModel()
        model.setRootPath(temp_dir)
        file_tree_view.setModel(model)

        refresh_count = 0
        original_refresh = model.refresh

        def count_refresh(*args, **kwargs):
            nonlocal refresh_count
            refresh_count += 1
            return original_refresh(*args, **kwargs)

        model.refresh = count_refresh

        # Simulate rapid directory changes (Windows QFileSystemWatcher behavior)
        paths = [temp_dir, temp_dir, temp_dir]
        for path in paths:
            file_tree_view._on_directory_changed(path)
            QApplication.processEvents()  # Process pending events

        # All changes should be processed (no infinite loop)
        assert refresh_count == 3, f"Expected 3 refreshes, got {refresh_count}"


@pytest.mark.integration
class TestFileTreeRefreshIntegration:
    """Integration tests for file tree refresh with real filesystem."""

    def test_real_directory_change_no_infinite_loop(self, file_tree_view, temp_dir, qtbot):
        """Test that real directory changes don't cause infinite loops."""
        from oncutf.ui.widgets.custom_file_system_model import CustomFileSystemModel

        # Use real model
        model = CustomFileSystemModel()
        model.setRootPath(temp_dir)
        file_tree_view.setModel(model)

        # Wait for model to initialize
        qtbot.waitUntil(lambda: model.rowCount(model.index(temp_dir)) >= 0, timeout=1000)

        # Create a file to trigger directory change
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content")

        # Give filesystem monitor time to detect change
        qtbot.wait(500)

        # Manually trigger directory change (simulates what monitor would do)
        file_tree_view._on_directory_changed(temp_dir)

        # Wait for refresh to complete
        qtbot.wait(200)

        # If we got here without hanging, test passes
        assert file_tree_view._refresh_in_progress is False

        # Cleanup
        test_file.unlink()

    def test_rapid_file_creation_no_hang(self, file_tree_view, temp_dir, qtbot):
        """Test that rapid file creation doesn't hang the UI."""
        from oncutf.ui.widgets.custom_file_system_model import CustomFileSystemModel

        model = CustomFileSystemModel()
        model.setRootPath(temp_dir)
        file_tree_view.setModel(model)

        qtbot.waitUntil(lambda: model.rowCount(model.index(temp_dir)) >= 0, timeout=1000)

        # Create multiple files rapidly
        for i in range(5):
            test_file = Path(temp_dir) / f"test_{i}.txt"
            test_file.write_text(f"test content {i}")
            file_tree_view._on_directory_changed(temp_dir)
            QApplication.processEvents()

        # Wait for all changes to process
        qtbot.wait(500)

        # UI should still be responsive
        assert file_tree_view._refresh_in_progress is False

        # Cleanup
        for i in range(5):
            (Path(temp_dir) / f"test_{i}.txt").unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
