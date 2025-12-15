"""
Module: test_rename_integration.py

Author: Michael Economou
Date: 2025-05-31

Integration tests for the enhanced rename workflow with validation
"""

import warnings
from datetime import datetime
from unittest.mock import MagicMock, patch

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

from oncutf.config import INVALID_FILENAME_MARKER
from oncutf.core.rename_manager import RenameManager
from oncutf.models.file_item import FileItem
from oncutf.modules.specified_text_module import SpecifiedTextModule
from tests.mocks import MockFileItem
from oncutf.utils.filename_validator import is_validation_error_marker


class TestRenameIntegration:
    """Integration tests for the complete rename workflow"""

    def test_valid_input_workflow(self):
        """Test complete workflow with valid input"""
        data = {"type": "specified_text", "text": "valid_prefix"}
        file_item = MockFileItem(filename="test.txt")
        result = SpecifiedTextModule.apply_from_data(data, file_item)
        assert result == "valid_prefix"
        assert not is_validation_error_marker(result)

    def test_invalid_input_workflow(self):
        """Test complete workflow with invalid input"""
        data = {"type": "specified_text", "text": "invalid<text>"}
        file_item = MockFileItem(filename="test.txt")
        result = SpecifiedTextModule.apply_from_data(data, file_item)
        assert is_validation_error_marker(result)
        assert result == INVALID_FILENAME_MARKER

    def test_reserved_filename_workflow(self):
        """Test workflow with Windows reserved names"""
        reserved_names = ["CON", "PRN", "AUX", "NUL"]
        for reserved_name in reserved_names:
            data = {"type": "specified_text", "text": reserved_name}
            file_item = MockFileItem(filename="test.txt")
            result = SpecifiedTextModule.apply_from_data(data, file_item)
            assert is_validation_error_marker(result)

    def test_safe_post_rename_workflow(self):
        """Test that the safe post-rename workflow executes properly."""
        # Create mock main window
        mock_main_window = MagicMock()
        mock_main_window.current_folder_path = "/test/folder"
        mock_main_window.last_action = None
        mock_main_window.file_model = MagicMock()
        mock_main_window.file_model.files = []

        # Create RenameManager instance
        rename_manager = RenameManager(mock_main_window)

        # Test data
        checked_paths = {"/test/folder/file1.txt", "/test/folder/file2.txt"}

        # Mock the timer manager
        with patch("oncutf.utils.timer_manager.get_timer_manager") as mock_timer_manager:
            mock_timer = MagicMock()
            mock_timer_manager.return_value = mock_timer

            # Call the safe post-rename workflow
            rename_manager._execute_post_rename_workflow_safe(checked_paths)

            # Verify timer was scheduled for state restoration
            assert mock_timer.schedule.called
            schedule_call = mock_timer.schedule.call_args
            assert schedule_call[1]["delay"] == 50
            assert schedule_call[1]["timer_id"] == "post_rename_state_restore"

            # Verify main window methods were called
            assert mock_main_window.last_action == "rename"
            mock_main_window.load_files_from_folder.assert_called_once_with("/test/folder")

    def test_restore_checked_state_safe(self):
        """Test safe restoration of checked state."""
        # Create mock main window with files
        mock_main_window = MagicMock()

        # Create mock files
        file1 = FileItem("/test/folder/file1.txt", "txt", datetime.now())
        file2 = FileItem("/test/folder/file2.txt", "txt", datetime.now())

        # Mock find_fileitem_by_path to return files
        def mock_find_file(path):
            if path == "/test/folder/file1.txt":
                return file1
            elif path == "/test/folder/file2.txt":
                return file2
            return None

        mock_main_window.find_fileitem_by_path = mock_find_file

        # Create RenameManager instance
        rename_manager = RenameManager(mock_main_window)

        # Test data
        checked_paths = {"/test/folder/file1.txt", "/test/folder/file2.txt"}

        # Call safe restore
        restored_count = rename_manager._restore_checked_state_safe(checked_paths)

        # Verify results
        assert restored_count == 2
        assert file1.checked is True
        assert file2.checked is True

    def test_update_info_icons_safe(self):
        """Test safe update of info icons."""
        # Create mock main window
        mock_main_window = MagicMock()
        mock_file_model = MagicMock()
        mock_file_table_view = MagicMock()

        # Setup mock file model
        mock_file_model.rowCount.return_value = 2
        mock_file_model.files = [
            FileItem("/test/folder/file1.txt", "txt", datetime.now()),
            FileItem("/test/folder/file2.txt", "txt", datetime.now()),
        ]
        mock_file_model.index.return_value = MagicMock()

        # Setup mock main window
        mock_main_window.file_model = mock_file_model
        mock_main_window.file_table_view = mock_file_table_view
        mock_main_window.metadata_cache = MagicMock()
        mock_main_window.metadata_cache.has.return_value = True

        # Create RenameManager instance
        rename_manager = RenameManager(mock_main_window)

        # Call safe update icons
        rename_manager._update_info_icons_safe()

        # Verify viewport update was called
        mock_file_table_view.viewport().update.assert_called()

    def test_safe_post_rename_workflow_with_invalid_window(self):
        """Test safe post-rename workflow handles invalid main window gracefully."""
        # Create RenameManager with None main window
        rename_manager = RenameManager(None)

        # Test data
        checked_paths = {"/test/folder/file1.txt"}

        # Should not raise exception
        rename_manager._execute_post_rename_workflow_safe(checked_paths)

        # Test with main window missing current_folder_path
        mock_main_window = MagicMock()
        del mock_main_window.current_folder_path

        rename_manager = RenameManager(mock_main_window)

        # Should not raise exception
        rename_manager._execute_post_rename_workflow_safe(checked_paths)

    def test_rename_files_schedules_safe_workflow(self):
        """Test that rename_files schedules the safe workflow properly."""
        # Create mock main window
        mock_main_window = MagicMock()
        mock_main_window.get_selected_files.return_value = []
        mock_main_window.rename_modules_area.get_all_data.return_value = {"modules": []}
        mock_main_window.final_transform_container.get_data.return_value = {}
        mock_main_window.file_model.files = []
        mock_main_window.file_operations_manager.rename_files.return_value = 2  # 2 files renamed

        # Create RenameManager instance
        rename_manager = RenameManager(mock_main_window)

        # Mock the timer manager
        with patch("oncutf.utils.timer_manager.get_timer_manager") as mock_timer_manager:
            mock_timer = MagicMock()
            mock_timer_manager.return_value = mock_timer

            # Call rename_files
            rename_manager.rename_files()

            # Verify timer was scheduled for post-rename workflow
            assert mock_timer.schedule.called
            schedule_call = mock_timer.schedule.call_args
            assert schedule_call[1]["delay"] == 100
            assert schedule_call[1]["timer_id"] == "post_rename_workflow"
