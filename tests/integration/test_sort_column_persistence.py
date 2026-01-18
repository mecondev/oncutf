"""Integration tests for sort column persistence feature.

Author: Michael Economou
Date: 2026-01-15

Tests that sort column and order are properly saved and restored across sessions.
Now uses database (SessionStateStore) instead of JSON for ACID guarantees.
"""

from unittest.mock import Mock

import pytest
from PyQt5.QtCore import Qt

from oncutf.core.session_state_manager import get_session_state_manager
from oncutf.core.ui_managers.window_config_manager import WindowConfigManager


@pytest.fixture
def mock_main_window():
    """Create a mock main window with necessary attributes."""
    window = Mock()
    window.context = Mock()
    window.context.get_current_folder.return_value = "/test/folder"
    window.context.is_recursive_mode.return_value = False
    window.current_sort_column = 2
    window.current_sort_order = Qt.AscendingOrder
    window.isMaximized.return_value = False
    window.isMinimized.return_value = False

    # Mock splitters
    window.horizontal_splitter = Mock()
    window.horizontal_splitter.sizes.return_value = [250, 674, 250]
    window.vertical_splitter = Mock()
    window.vertical_splitter.sizes.return_value = [500, 300]
    window.lower_section_splitter = Mock()
    window.lower_section_splitter.sizes.return_value = [868, 867]

    # Mock geometry
    window.saveGeometry.return_value = b'mock_geometry'
    window.restoreGeometry.return_value = True

    return window


@pytest.fixture
def session_manager():
    """Get the session state manager and reset to defaults."""
    manager = get_session_state_manager()
    # Reset to defaults for testing
    manager.set_sort_column(2)
    manager.set_sort_order(0)
    return manager


class TestSortColumnPersistence:
    """Test suite for sort column persistence feature."""

    def test_save_sort_state(self, mock_main_window, session_manager):
        """Test that sort state is saved to database."""
        # Set custom sort state
        mock_main_window.current_sort_column = 3  # Custom column
        mock_main_window.current_sort_order = Qt.DescendingOrder

        # Create manager and save config
        manager = WindowConfigManager(mock_main_window)
        manager.save_window_config()

        # Verify sort state was saved to database
        assert session_manager.get_sort_column() == 3
        assert session_manager.get_sort_order() == int(Qt.DescendingOrder)

    def test_load_sort_state(self, mock_main_window, session_manager):
        """Test that sort state is loaded from database."""
        # Set saved sort state in database
        session_manager.set_sort_column(4)
        session_manager.set_sort_order(int(Qt.DescendingOrder))

        # Create manager and apply config
        manager = WindowConfigManager(mock_main_window)
        manager.apply_loaded_config()

        # Verify sort state was loaded and applied
        assert mock_main_window.current_sort_column == 4
        assert mock_main_window.current_sort_order == Qt.DescendingOrder

    def test_default_sort_state_on_first_run(self, mock_main_window, session_manager):
        """Test that default sort state (column 2, ascending) is used on first run."""
        # Reset to defaults
        session_manager.set_sort_column(2)
        session_manager.set_sort_order(0)

        # Create manager and apply config
        manager = WindowConfigManager(mock_main_window)
        manager.apply_loaded_config()

        # Verify defaults are used (column 2 = filename, ascending)
        assert mock_main_window.current_sort_column == 2
        assert mock_main_window.current_sort_order == Qt.AscendingOrder

    def test_sort_state_persists_after_clear(self, mock_main_window):
        """Test that sort state is preserved when clearing file table."""
        from oncutf.core.ui_managers.shortcut_manager import ShortcutManager

        # Set custom sort state
        mock_main_window.current_sort_column = 5
        mock_main_window.current_sort_order = Qt.DescendingOrder
        mock_main_window.file_model = Mock()
        mock_main_window.file_model.rowCount.return_value = 10
        mock_main_window.status_manager = Mock()
        mock_main_window.context = Mock()

        # Create shortcut manager
        manager = ShortcutManager(mock_main_window)

        # Store initial state
        initial_column = mock_main_window.current_sort_column
        initial_order = mock_main_window.current_sort_order

        # Manually call the clear shortcut handler
        manager.clear_file_table_shortcut()

        # Verify sort state was preserved
        assert mock_main_window.current_sort_column == initial_column
        assert mock_main_window.current_sort_order == initial_order


@pytest.mark.integration
class TestSortColumnIntegration:
    """Integration tests for sort column persistence workflow."""

    def test_full_persistence_workflow(self, mock_main_window, session_manager):
        """Test complete save -> load workflow using database."""
        # Step 1: Set custom sort state and save
        mock_main_window.current_sort_column = 3
        mock_main_window.current_sort_order = Qt.DescendingOrder

        save_manager = WindowConfigManager(mock_main_window)
        save_manager.save_window_config()

        # Verify it was saved to database
        assert session_manager.get_sort_column() == 3
        assert session_manager.get_sort_order() == int(Qt.DescendingOrder)

        # Step 2: Create new window (simulate restart)
        new_window = Mock()
        new_window.context = Mock()
        new_window.context.get_current_folder.return_value = "/test/folder"
        new_window.context.is_recursive_mode.return_value = False
        new_window.isMaximized.return_value = False
        new_window.isMinimized.return_value = False

        # Mock splitters
        new_window.horizontal_splitter = Mock()
        new_window.horizontal_splitter.sizes.return_value = [250, 674, 250]
        new_window.vertical_splitter = Mock()
        new_window.vertical_splitter.sizes.return_value = [500, 300]
        new_window.lower_section_splitter = Mock()
        new_window.lower_section_splitter.sizes.return_value = [868, 867]
        new_window.restoreGeometry.return_value = True

        # Step 3: Load config into new window from database
        load_manager = WindowConfigManager(new_window)
        load_manager.apply_loaded_config()

        # Step 4: Verify sort state was restored
        assert new_window.current_sort_column == 3
        assert new_window.current_sort_order == Qt.DescendingOrder

