"""Tests for MainWindowController.

Author: Michael Economou
Date: 2025-12-16
"""

from unittest.mock import MagicMock, patch

import pytest

from oncutf.controllers.main_window_controller import MainWindowController


@pytest.fixture
def mock_app_context():
    """Create mock ApplicationContext."""
    context = MagicMock()
    context.file_store = MagicMock()
    context.file_store.get_loaded_files = MagicMock(return_value=[])
    return context


@pytest.fixture
def mock_controllers():
    """Create mock sub-controllers."""
    file_load = MagicMock()
    file_load.load_folder = MagicMock(
        return_value={"success": True, "loaded_count": 5, "errors": []}
    )

    metadata = MagicMock()
    metadata.load_metadata = MagicMock(
        return_value={"success": True, "loaded_count": 5, "errors": []}
    )

    rename = MagicMock()

    return file_load, metadata, rename


@pytest.fixture
def controller(mock_app_context, mock_controllers):
    """Create MainWindowController with mocks."""
    file_load, metadata, rename = mock_controllers

    return MainWindowController(
        app_context=mock_app_context,
        file_load_controller=file_load,
        metadata_controller=metadata,
        rename_controller=rename,
    )


class TestMainWindowControllerInit:
    """Tests for MainWindowController initialization."""

    def test_initialization(self, mock_app_context, mock_controllers):
        """Test controller initializes correctly."""
        file_load, metadata, rename = mock_controllers

        controller = MainWindowController(
            app_context=mock_app_context,
            file_load_controller=file_load,
            metadata_controller=metadata,
            rename_controller=rename,
        )

        assert controller._app_context is mock_app_context
        assert controller._file_load_controller is file_load
        assert controller._metadata_controller is metadata
        assert controller._rename_controller is rename


class TestRestoreLastSessionWorkflow:
    """Tests for restore_last_session_workflow method."""

    def test_no_last_folder(self, controller):
        """Test with no last folder to restore."""
        result = controller.restore_last_session_workflow(last_folder=None)

        assert result["success"] is True
        assert result["folder_restored"] is False
        assert result["folder_path"] is None
        assert result["files_loaded"] == 0
        assert result["metadata_loaded"] == 0
        assert len(result["errors"]) == 0

    def test_nonexistent_folder(self, controller):
        """Test with nonexistent folder."""
        result = controller.restore_last_session_workflow(last_folder="/nonexistent/folder")

        assert result["success"] is False
        assert result["folder_restored"] is False
        assert result["folder_path"] is None
        assert result["files_loaded"] == 0
        assert len(result["errors"]) == 1
        assert "no longer exists" in result["errors"][0]

    @patch("os.path.exists")
    def test_successful_folder_restoration(self, mock_exists, controller, mock_controllers):
        """Test successful folder restoration without metadata."""
        mock_exists.return_value = True
        file_load, _, _ = mock_controllers

        # Use os.path.join for cross-platform path
        import os

        test_folder = os.path.join("test", "folder")

        result = controller.restore_last_session_workflow(
            last_folder=test_folder, recursive=False, load_metadata=False
        )

        # Verify FileLoadController was called
        file_load.load_folder.assert_called_once()
        call_args = file_load.load_folder.call_args
        # Check path components exist (cross-platform)
        path_str = str(call_args[0][0])
        assert "test" in path_str and "folder" in path_str
        assert call_args[1]["merge"] is False
        assert call_args[1]["recursive"] is False

        # Verify result
        assert result["success"] is True
        assert result["folder_restored"] is True
        # Check path components in result (cross-platform)
        assert "test" in result["folder_path"] and "folder" in result["folder_path"]
        assert result["files_loaded"] == 5
        assert result["metadata_loaded"] == 0
        assert len(result["errors"]) == 0

    @patch("os.path.exists")
    def test_successful_folder_with_metadata(
        self, mock_exists, controller, mock_controllers, mock_app_context
    ):
        """Test successful folder restoration with metadata loading."""
        mock_exists.return_value = True
        file_load, metadata, _ = mock_controllers

        # Mock loaded files
        mock_file1 = MagicMock()
        mock_file2 = MagicMock()
        mock_app_context.file_store.get_loaded_files.return_value = [mock_file1, mock_file2]

        result = controller.restore_last_session_workflow(
            last_folder="/test/folder", recursive=True, load_metadata=True
        )

        # Verify FileLoadController was called
        file_load.load_folder.assert_called_once()
        call_args = file_load.load_folder.call_args
        assert call_args[1]["recursive"] is True

        # Verify MetadataController was called
        metadata.load_metadata.assert_called_once()
        meta_call_args = metadata.load_metadata.call_args
        assert meta_call_args[1]["items"] == [mock_file1, mock_file2]
        assert meta_call_args[1]["use_extended"] is False
        assert meta_call_args[1]["source"] == "session_restore"

        # Verify result
        assert result["success"] is True
        assert result["folder_restored"] is True
        assert result["files_loaded"] == 5
        assert result["metadata_loaded"] == 5
        assert len(result["errors"]) == 0

    @patch("os.path.exists")
    def test_folder_load_failure(self, mock_exists, controller, mock_controllers):
        """Test folder load failure."""
        mock_exists.return_value = True
        file_load, _, _ = mock_controllers

        # Mock failed folder load
        file_load.load_folder.return_value = {
            "success": False,
            "loaded_count": 0,
            "errors": ["Failed to load folder"],
        }

        result = controller.restore_last_session_workflow(last_folder="/test/folder")

        assert result["success"] is False
        assert result["folder_restored"] is False
        assert result["files_loaded"] == 0
        assert len(result["errors"]) == 1
        assert "Failed to load folder" in result["errors"][0]

    @patch("os.path.exists")
    def test_metadata_load_failure_not_critical(
        self, mock_exists, controller, mock_controllers, mock_app_context
    ):
        """Test that metadata loading failure doesn't fail the whole workflow."""
        mock_exists.return_value = True
        file_load, metadata, _ = mock_controllers

        # Mock loaded files
        mock_app_context.file_store.get_loaded_files.return_value = [MagicMock()]

        # Mock failed metadata load
        metadata.load_metadata.return_value = {
            "success": False,
            "loaded_count": 0,
            "errors": ["Metadata load failed"],
        }

        result = controller.restore_last_session_workflow(
            last_folder="/test/folder", load_metadata=True
        )

        # Folder should still be considered successfully restored
        assert result["success"] is True
        assert result["folder_restored"] is True
        assert result["files_loaded"] == 5
        assert result["metadata_loaded"] == 0
        # Error should be logged but not critical
        assert "Metadata load failed" in result["errors"][0]

    @patch("os.path.exists")
    def test_with_sort_configuration(self, mock_exists, controller):
        """Test that sort configuration is preserved in result."""
        mock_exists.return_value = True

        result = controller.restore_last_session_workflow(
            last_folder="/test/folder", sort_column=2, sort_order=1  # Descending
        )

        assert result["success"] is True
        assert result["sort_column"] == 2
        assert result["sort_order"] == 1

    @patch("os.path.exists")
    def test_exception_during_file_load(self, mock_exists, controller, mock_controllers):
        """Test exception handling during file load."""
        mock_exists.return_value = True
        file_load, _, _ = mock_controllers

        # Mock exception during load
        file_load.load_folder.side_effect = Exception("Unexpected error")

        result = controller.restore_last_session_workflow(last_folder="/test/folder")

        assert result["success"] is False
        assert result["folder_restored"] is False
        assert len(result["errors"]) == 1
        assert "Error loading folder" in result["errors"][0]

    @patch("os.path.exists")
    def test_exception_during_metadata_load(
        self, mock_exists, controller, mock_controllers, mock_app_context
    ):
        """Test exception handling during metadata load."""
        mock_exists.return_value = True
        _, metadata, _ = mock_controllers

        # Mock loaded files
        mock_app_context.file_store.get_loaded_files.return_value = [MagicMock()]

        # Mock exception during metadata load
        metadata.load_metadata.side_effect = Exception("Metadata error")

        result = controller.restore_last_session_workflow(
            last_folder="/test/folder", load_metadata=True
        )

        # Folder should still be considered restored (metadata not critical)
        assert result["success"] is True
        assert result["folder_restored"] is True
        assert result["files_loaded"] == 5
        assert len(result["errors"]) == 1
        assert "Error loading metadata" in result["errors"][0]

    @patch("os.path.exists")
    def test_no_files_loaded_skips_metadata(self, mock_exists, controller, mock_controllers):
        """Test that metadata loading is skipped if no files were loaded."""
        mock_exists.return_value = True
        file_load, metadata, _ = mock_controllers

        # Mock empty folder
        file_load.load_folder.return_value = {"success": True, "loaded_count": 0, "errors": []}

        result = controller.restore_last_session_workflow(
            last_folder="/test/folder", load_metadata=True
        )

        # Metadata should not be loaded if no files
        metadata.load_metadata.assert_not_called()

        assert result["success"] is True
        assert result["files_loaded"] == 0
        assert result["metadata_loaded"] == 0


class TestCoordinateShutdownWorkflow:
    """Test coordinate_shutdown_workflow orchestration method."""

    @patch("oncutf.utils.json_config_manager.get_app_config_manager")
    def test_successful_shutdown_all_steps(self, mock_config_manager, controller):
        """Test successful shutdown with all cleanup steps."""
        # Mock config manager
        config_mgr = MagicMock()
        mock_config_manager.return_value = config_mgr

        # Mock main window with all managers
        main_window = MagicMock()
        main_window.backup_manager = MagicMock()
        main_window.window_config_manager = MagicMock()
        main_window.batch_manager = MagicMock()
        main_window.batch_manager.flush_operations = MagicMock()
        main_window.drag_manager = MagicMock()
        main_window.dialog_manager = MagicMock()
        main_window.shutdown_coordinator = MagicMock()
        main_window.shutdown_coordinator.execute_shutdown = MagicMock(return_value=True)
        main_window.shutdown_coordinator.get_summary = MagicMock(return_value={"test": "summary"})

        result = controller.coordinate_shutdown_workflow(main_window)

        # Verify all cleanup steps were called
        config_mgr.save_immediate.assert_called_once()
        main_window.backup_manager.create_backup.assert_called_once_with(reason="auto")
        main_window.window_config_manager.save_window_config.assert_called_once()
        main_window.batch_manager.flush_operations.assert_called_once()
        main_window.drag_manager.force_cleanup.assert_called_once()
        main_window.dialog_manager.cleanup.assert_called_once()
        main_window.shutdown_coordinator.execute_shutdown.assert_called_once()

        # Verify result
        assert result["success"] is True
        assert result["config_saved"] is True
        assert result["backup_created"] is True
        assert result["operations_flushed"] is True
        assert result["coordinator_success"] is True
        assert len(result["errors"]) == 0
        assert result["summary"] == {"test": "summary"}

    @patch("oncutf.utils.json_config_manager.get_app_config_manager")
    def test_shutdown_with_missing_managers(self, mock_config_manager, controller):
        """Test shutdown handles missing optional managers gracefully."""
        config_mgr = MagicMock()
        mock_config_manager.return_value = config_mgr

        # Main window with only required components
        main_window = MagicMock()
        main_window.backup_manager = None
        main_window.window_config_manager = None
        main_window.batch_manager = None
        main_window.drag_manager = None
        main_window.dialog_manager = None
        main_window.shutdown_coordinator = MagicMock()
        main_window.shutdown_coordinator.execute_shutdown = MagicMock(return_value=True)
        main_window.shutdown_coordinator.get_summary = MagicMock(return_value={})

        result = controller.coordinate_shutdown_workflow(main_window)

        # Should still succeed with config save and coordinator
        assert result["success"] is True
        assert result["config_saved"] is True
        assert result["backup_created"] is False  # Manager was None
        assert result["coordinator_success"] is True

    @patch("oncutf.utils.json_config_manager.get_app_config_manager")
    def test_shutdown_config_save_failure(self, mock_config_manager, controller):
        """Test shutdown handles config save failure."""
        config_mgr = MagicMock()
        config_mgr.save_immediate.side_effect = Exception("Config save error")
        mock_config_manager.return_value = config_mgr

        main_window = MagicMock()
        main_window.shutdown_coordinator = MagicMock()
        main_window.shutdown_coordinator.execute_shutdown = MagicMock(return_value=True)
        main_window.shutdown_coordinator.get_summary = MagicMock(return_value={})

        result = controller.coordinate_shutdown_workflow(main_window)

        # Should continue despite config save failure
        assert result["config_saved"] is False
        assert len(result["errors"]) == 1
        assert "Failed to save configuration" in result["errors"][0]
        # Overall success depends on coordinator
        assert result["coordinator_success"] is True

    @patch("oncutf.utils.json_config_manager.get_app_config_manager")
    def test_shutdown_progress_callback(self, mock_config_manager, controller):
        """Test shutdown calls progress callback correctly."""
        config_mgr = MagicMock()
        mock_config_manager.return_value = config_mgr

        main_window = MagicMock()
        main_window.shutdown_coordinator = MagicMock()
        main_window.shutdown_coordinator.execute_shutdown = MagicMock(return_value=True)
        main_window.shutdown_coordinator.get_summary = MagicMock(return_value={})

        # Track progress callbacks
        progress_calls = []

        def track_progress(msg, prog):
            progress_calls.append((msg, prog))

        result = controller.coordinate_shutdown_workflow(
            main_window, progress_callback=track_progress
        )

        # Should have progress updates
        assert len(progress_calls) > 0
        assert progress_calls[0][1] == 0.1  # First update at 10%
        assert progress_calls[-1][1] == 1.0  # Last update at 100%
        assert result["success"] is True

    @patch("oncutf.utils.json_config_manager.get_app_config_manager")
    def test_shutdown_coordinator_failure(self, mock_config_manager, controller):
        """Test shutdown handles coordinator failure."""
        config_mgr = MagicMock()
        mock_config_manager.return_value = config_mgr

        main_window = MagicMock()
        main_window.shutdown_coordinator = MagicMock()
        main_window.shutdown_coordinator.execute_shutdown = MagicMock(return_value=False)
        main_window.shutdown_coordinator.get_summary = MagicMock(return_value={"error": "failed"})

        result = controller.coordinate_shutdown_workflow(main_window)

        # Should report coordinator failure
        assert result["coordinator_success"] is False
        assert result["success"] is False  # Overall failure
        assert result["summary"] == {"error": "failed"}

    @patch("oncutf.utils.json_config_manager.get_app_config_manager")
    def test_shutdown_unexpected_exception(self, mock_config_manager, controller):
        """Test shutdown handles unexpected exceptions."""
        config_mgr = MagicMock()
        config_mgr.save_immediate.side_effect = RuntimeError("Catastrophic failure")
        mock_config_manager.return_value = config_mgr

        main_window = MagicMock()

        result = controller.coordinate_shutdown_workflow(main_window)

        # Should catch and report exception
        assert result["success"] is False
        assert len(result["errors"]) >= 1
        assert any(
            "Catastrophic failure" in err or "Unexpected error" in err for err in result["errors"]
        )
