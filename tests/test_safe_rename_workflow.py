"""Test module for safe rename workflow functionality.

This module tests the enhanced rename workflow that prevents Qt object lifecycle crashes
while ensuring proper UI state restoration after rename operations.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

from oncutf.models.file_item import FileItem
from oncutf.ui.managers.rename_manager import RenameManager


class TestSafeRenameWorkflow:
    """Test suite for safe rename workflow functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock main window
        self.mock_main_window = MagicMock()
        self.mock_main_window.last_action = None

        # Setup mock context
        self.mock_context = MagicMock()
        self.mock_context.get_current_folder.return_value = "/test/folder"
        self.mock_main_window.context = self.mock_context

        # Setup file model
        self.mock_file_model = MagicMock()
        self.mock_file_model.files = []
        self.mock_file_model.rowCount.return_value = 0
        self.mock_main_window.file_model = self.mock_file_model

        # Setup file table view
        self.mock_file_table_view = MagicMock()
        self.mock_main_window.file_table_view = self.mock_file_table_view

        # Setup metadata cache
        self.mock_metadata_cache = MagicMock()
        self.mock_metadata_cache.has.return_value = False
        self.mock_main_window.metadata_cache = self.mock_metadata_cache

        # Create RenameManager instance
        self.rename_manager = RenameManager(self.mock_main_window)

    def test_safe_post_rename_workflow_execution(self):
        """Test that the safe post-rename workflow executes all steps properly."""
        checked_paths = {"/test/folder/file1.txt", "/test/folder/file2.txt"}

        with patch("oncutf.utils.shared.timer_manager.get_timer_manager") as mock_timer_manager:
            mock_timer = MagicMock()
            mock_timer_manager.return_value = mock_timer

            # Call the safe post-rename workflow
            self.rename_manager._execute_post_rename_workflow_safe(checked_paths)

            # Verify main window state was updated
            assert self.mock_main_window.last_action == "rename"

            # Verify folder reload was called
            self.mock_main_window.load_files_from_folder.assert_called_once_with("/test/folder")

            # Verify timer was scheduled for state restoration (debounced/safety variants allowed)
            assert mock_timer.schedule.called
            # Collect scheduled timer_ids from all calls
            timer_ids = [kwargs.get("timer_id") for (_args, kwargs) in mock_timer.schedule.call_args_list]
            # Expect at least one timer related to post-rename state restoration
            assert any(
                (tid and "post_rename_state_restore" in tid) or tid in (
                    "post_rename_state_restore_debounced",
                    "post_rename_state_restore_fallback",
                    "post_rename_state_restore_safety",
                )
                for tid in timer_ids
            )

    def test_safe_post_rename_workflow_with_invalid_main_window(self):
        """Test workflow handles invalid main window gracefully."""
        # Test with None main window
        rename_manager = RenameManager(None)
        checked_paths = {"/test/folder/file1.txt"}

        # Should not raise exception
        rename_manager._execute_post_rename_workflow_safe(checked_paths)

        # Test with main window missing context
        mock_main_window = MagicMock()
        del mock_main_window.context

        rename_manager = RenameManager(mock_main_window)

        # Should not raise exception
        rename_manager._execute_post_rename_workflow_safe(checked_paths)

    def test_safe_post_rename_workflow_with_no_folder(self):
        """Test workflow handles missing folder path gracefully."""
        self.mock_context.get_current_folder.return_value = None
        checked_paths = {"/test/folder/file1.txt"}

        # Should not raise exception and should return early
        self.rename_manager._execute_post_rename_workflow_safe(checked_paths)

        # Verify no folder reload was attempted
        self.mock_main_window.load_files_from_folder.assert_not_called()

    def test_restore_checked_state_safe_success(self):
        """Test safe restoration of checked state for valid files."""
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

        self.mock_main_window.find_fileitem_by_path = mock_find_file

        # Test data
        checked_paths = {"/test/folder/file1.txt", "/test/folder/file2.txt"}

        # Call safe restore
        restored_count = self.rename_manager._restore_checked_state_safe(checked_paths)

        # Verify results
        assert restored_count == 2
        assert file1.checked is True
        assert file2.checked is True

    def test_restore_checked_state_safe_with_missing_files(self):
        """Test safe restoration handles missing files gracefully."""

        # Mock find_fileitem_by_path to return None for some files
        def mock_find_file(path):
            if path == "/test/folder/file1.txt":
                return FileItem("/test/folder/file1.txt", "txt", datetime.now())
            return None  # file2.txt not found

        self.mock_main_window.find_fileitem_by_path = mock_find_file

        # Test data
        checked_paths = {"/test/folder/file1.txt", "/test/folder/file2.txt"}

        # Call safe restore
        restored_count = self.rename_manager._restore_checked_state_safe(checked_paths)

        # Should only restore one file
        assert restored_count == 1

    def test_restore_checked_state_safe_with_invalid_main_window(self):
        """Test safe restoration handles invalid main window gracefully."""
        # Test with None main window
        rename_manager = RenameManager(None)
        checked_paths = {"/test/folder/file1.txt"}

        restored_count = rename_manager._restore_checked_state_safe(checked_paths)
        assert restored_count == 0

        # Test with main window missing find_fileitem_by_path
        mock_main_window = MagicMock()
        del mock_main_window.find_fileitem_by_path

        rename_manager = RenameManager(mock_main_window)
        restored_count = rename_manager._restore_checked_state_safe(checked_paths)
        assert restored_count == 0

    def test_update_info_icons_safe_success(self):
        """Test safe update of info icons with valid UI elements."""
        # Setup mock files
        file1 = FileItem("/test/folder/file1.txt", "txt", datetime.now())
        file2 = FileItem("/test/folder/file2.txt", "txt", datetime.now())

        self.mock_file_model.rowCount.return_value = 2
        self.mock_file_model.files = [file1, file2]
        self.mock_file_model.index.return_value = MagicMock()

        # Setup metadata cache to return True for has()
        self.mock_metadata_cache.has.return_value = True

        # Call safe update icons
        self.rename_manager._update_info_icons_safe()

        # Verify model index was called for each file
        assert self.mock_file_model.index.call_count == 2

        # Verify viewport update was called
        self.mock_file_table_view.viewport().update.assert_called()

    def test_update_info_icons_safe_with_invalid_main_window(self):
        """Test safe icon update handles invalid main window gracefully."""
        # Test with None main window
        rename_manager = RenameManager(None)

        # Should not raise exception
        rename_manager._update_info_icons_safe()

        # Test with main window missing file_model
        mock_main_window = MagicMock()
        del mock_main_window.file_model

        rename_manager = RenameManager(mock_main_window)

        # Should not raise exception
        rename_manager._update_info_icons_safe()

    def test_update_info_icons_safe_with_invalid_file_model(self):
        """Test safe icon update handles invalid file model gracefully."""
        # Test with file model missing required attributes
        mock_file_model = MagicMock()
        del mock_file_model.files

        self.mock_main_window.file_model = mock_file_model

        # Should not raise exception
        self.rename_manager._update_info_icons_safe()

    def test_rename_files_schedules_safe_workflow(self):
        """Test that rename_files schedules the safe workflow when files are renamed."""
        # Setup mock dependencies
        self.mock_main_window.get_selected_files.return_value = []
        self.mock_main_window.rename_modules_area.get_all_data.return_value = {"modules": []}
        self.mock_main_window.final_transform_container.get_data.return_value = {}
        self.mock_main_window.file_operations_manager.rename_files.return_value = (
            2  # 2 files renamed
        )

        with patch("oncutf.utils.shared.timer_manager.get_timer_manager") as mock_timer_manager:
            mock_timer = MagicMock()
            mock_timer_manager.return_value = mock_timer

            # Call rename_files
            self.rename_manager.rename_files()

            # Verify timer was scheduled for post-rename workflow
            assert mock_timer.schedule.called
            schedule_call = mock_timer.schedule.call_args
            assert schedule_call[1]["delay"] == 100
            assert schedule_call[1]["timer_id"] == "post_rename_workflow"

    def test_rename_files_skips_workflow_when_no_files_renamed(self):
        """Test that rename_files skips workflow when no files are renamed."""
        # Setup mock dependencies
        self.mock_main_window.get_selected_files.return_value = []
        self.mock_main_window.rename_modules_area.get_all_data.return_value = {"modules": []}
        self.mock_main_window.final_transform_container.get_data.return_value = {}
        self.mock_main_window.file_operations_manager.rename_files.return_value = (
            0  # No files renamed
        )

        with patch("oncutf.utils.shared.timer_manager.get_timer_manager") as mock_timer_manager:
            mock_timer = MagicMock()
            mock_timer_manager.return_value = mock_timer

            # Call rename_files
            self.rename_manager.rename_files()

            # Verify no timer was scheduled
            mock_timer.schedule.assert_not_called()

    def test_safe_workflow_error_handling(self):
        """Test that the safe workflow handles errors gracefully."""
        # Setup main window to raise exception during load_files_from_folder
        self.mock_main_window.load_files_from_folder.side_effect = Exception("Test error")

        checked_paths = {"/test/folder/file1.txt"}

        # Should not raise exception
        self.rename_manager._execute_post_rename_workflow_safe(checked_paths)

        # Verify the error was handled (no exception raised)
        assert True  # If we get here, the exception was handled
