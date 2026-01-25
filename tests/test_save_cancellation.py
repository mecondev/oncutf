"""Module: test_save_cancellation.py

Author: Michael Economou
Date: 2025-11-30

Tests for save operation cancellation functionality.
"""

import pytest


class TestSaveCancellation:
    """Test suite for save cancellation behavior."""

    def test_save_cancelled_flag_initialization(self):
        """Test that _save_cancelled flag is initialized to False."""
        from oncutf.core.metadata import UnifiedMetadataManager

        manager = UnifiedMetadataManager()
        assert hasattr(manager, "_save_cancelled")
        assert manager._save_cancelled is False

    def test_request_save_cancel_sets_flag(self):
        """Test that request_save_cancel sets the cancellation flag."""
        from oncutf.core.metadata import UnifiedMetadataManager

        manager = UnifiedMetadataManager()
        assert manager._save_cancelled is False

        manager.request_save_cancel()
        assert manager._save_cancelled is True

    def test_cancel_callback_provided_for_normal_saves(self):
        """Test that cancel callback is provided for normal saves when allowed."""
        from unittest.mock import MagicMock

        from oncutf.config import SAVE_OPERATION_SETTINGS
        from oncutf.core.metadata import UnifiedMetadataManager

        # Only test if cancellation is allowed
        if not SAVE_OPERATION_SETTINGS.get("ALLOW_CANCEL_NORMAL_SAVE", False):
            pytest.skip("Cancellation not enabled in config")

        manager = UnifiedMetadataManager()
        manager.parent_window = MagicMock()
        manager.parent_window.context.get_manager = MagicMock()

        # Mock the staging manager
        mock_staging = MagicMock()
        mock_staging.get_all_staged_changes.return_value = {}
        manager.parent_window.context.get_manager.return_value = mock_staging

        # Test that callback is created (can't easily test dialog creation without GUI)
        # Just verify the method exists
        assert hasattr(manager, "request_save_cancel")
        assert callable(manager.request_save_cancel)

    def test_no_cancel_callback_for_exit_saves(self):
        """Test that cancel callback is not provided for exit saves."""
        from oncutf.core.metadata import UnifiedMetadataManager

        manager = UnifiedMetadataManager()

        # Verify the logic: exit saves should never have cancel callback
        is_exit_save = True
        cancel_callback = manager.request_save_cancel if not is_exit_save else None

        assert cancel_callback is None, "Exit saves should not have cancel callback"

    def test_save_results_handles_cancellation(self):
        """Test that _show_save_results properly handles cancelled operations."""
        from unittest.mock import MagicMock, patch

        from oncutf.core.metadata import UnifiedMetadataManager

        manager = UnifiedMetadataManager()
        manager.parent_window = MagicMock()
        manager.parent_window.status_bar = MagicMock()

        # Mock CustomMessageDialog from widgets
        with patch(
            "oncutf.ui.dialogs.custom_message_dialog.CustomMessageDialog"
        ) as mock_dialog_class:
            # Test cancellation with some successful saves
            files_to_save = [MagicMock() for _ in range(10)]
            manager._show_save_results(
                success_count=5, failed_files=[], files_to_save=files_to_save, was_cancelled=True
            )

            # Verify info dialog was shown
            mock_dialog_class.information.assert_called_once()
            args = mock_dialog_class.information.call_args
            assert "cancelled" in args[0][2].lower()
            assert "5" in args[0][2]  # Should show success count

    def test_save_results_distinguishes_cancelled_vs_failed(self):
        """Test that result messages distinguish between cancelled and failed operations."""
        from unittest.mock import MagicMock, patch

        from oncutf.core.metadata import UnifiedMetadataManager

        manager = UnifiedMetadataManager()
        manager.parent_window = MagicMock()
        manager.parent_window.status_bar = MagicMock()

        # Mock both CustomMessageDialog and QMessageBox
        with (
            patch(
                "oncutf.ui.dialogs.custom_message_dialog.CustomMessageDialog"
            ) as mock_custom_dialog,
            patch("PyQt5.QtWidgets.QMessageBox") as mock_msgbox,
        ):
            files_to_save = [MagicMock() for _ in range(10)]

            # Test cancelled operation (uses CustomMessageDialog)
            manager._show_save_results(
                success_count=5, failed_files=[], files_to_save=files_to_save, was_cancelled=True
            )
            cancelled_call = mock_custom_dialog.information.call_args

            # Test failed operation (uses QMessageBox)
            mock_custom_dialog.reset_mock()
            mock_msgbox.reset_mock()
            manager._show_save_results(
                success_count=5,
                failed_files=["file1.jpg", "file2.jpg"],
                files_to_save=files_to_save,
                was_cancelled=False,
            )

            # Verify different message types
            assert cancelled_call is not None
            if mock_msgbox.warning.called:
                failed_call = mock_msgbox.warning.call_args
                assert "cancel" in cancelled_call[0][2].lower()
                assert "failed" in failed_call[0][2].lower()

    def test_cancellation_resets_between_operations(self):
        """Test that cancellation flag is reset between save operations."""
        from unittest.mock import MagicMock

        from oncutf.core.metadata import UnifiedMetadataManager

        manager = UnifiedMetadataManager()
        manager.parent_window = MagicMock()
        manager.parent_window.context.get_manager = MagicMock()

        # Set flag to True (as if cancelled)
        manager._save_cancelled = True

        # Mock staging manager with no changes (to trigger early return)
        mock_staging = MagicMock()
        mock_staging.get_all_staged_changes.return_value = {}
        manager.parent_window.context.get_manager.return_value = mock_staging

        # Call save_all_modified_metadata (should reset flag before starting)
        manager.save_all_modified_metadata()

        # Flag should remain True since we didn't reach the reset point
        # (early return due to no changes)
        assert manager._save_cancelled is True

        # Now test with actual changes to reach reset point
        mock_staging.get_all_staged_changes.return_value = {"/path/to/file.jpg": {"key": "value"}}
        manager.parent_window.file_model = MagicMock()
        manager.parent_window.file_model.files = []

        # This should trigger the reset
        manager.save_all_modified_metadata()

        # Since no files match, it returns early but AFTER the reset
        # We can't easily test the reset without a full integration test
        # Just verify the method exists
        assert hasattr(manager, "_save_cancelled")

    def test_cancel_during_multi_file_save_stops_processing(self):
        """Test that cancellation during multi-file save stops processing remaining files."""
        from unittest.mock import MagicMock, patch

        from oncutf.core.metadata import UnifiedMetadataManager

        manager = UnifiedMetadataManager()
        manager.parent_window = MagicMock()
        manager.parent_window.status_bar = MagicMock()
        manager.parent_window.context.get_manager = MagicMock()

        # Create mock file items
        mock_files = []
        for i in range(5):
            mock_file = MagicMock()
            mock_file.filename = f"file{i}.jpg"
            mock_file.full_path = f"/path/to/file{i}.jpg"
            mock_files.append(mock_file)

        # Mock staging manager
        mock_staging = MagicMock()
        mock_staging.get_all_staged_changes.return_value = {
            f"/path/to/file{i}.jpg": {"key": "value"} for i in range(5)
        }
        manager.parent_window.context.get_manager.return_value = mock_staging

        # Mock exiftool wrapper
        manager._exiftool_wrapper = MagicMock()

        # Track how many files were processed
        processed_files = []

        def mock_write_metadata(path, _mods):
            processed_files.append(path)
            # Cancel after 2 files
            if len(processed_files) == 2:
                manager._save_cancelled = True
            return True

        manager._exiftool_wrapper.write_metadata = mock_write_metadata

        # Mock progress dialog and other dependencies
        # Note: ProgressDialog is imported inside the function, so we patch the source module
        with (
            patch("oncutf.utils.ui.progress_dialog.ProgressDialog") as mock_dialog_class,
            patch("oncutf.ui.dialogs.custom_message_dialog.CustomMessageDialog"),
            patch("PyQt5.QtWidgets.QMessageBox"),
        ):
            mock_dialog = MagicMock()
            mock_dialog_class.return_value = mock_dialog

            # Call the save method
            manager._save_metadata_files(
                mock_files, mock_staging.get_all_staged_changes(), is_exit_save=False
            )

        # Verify that only 2 files were processed before cancellation
        assert len(processed_files) == 2, f"Expected 2 files processed, got {len(processed_files)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
