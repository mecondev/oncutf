"""
Tests for MainWindowController.

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
    file_load.load_folder = MagicMock(return_value={
        'success': True,
        'loaded_count': 5,
        'errors': []
    })

    metadata = MagicMock()
    metadata.load_metadata = MagicMock(return_value={
        'success': True,
        'loaded_count': 5,
        'errors': []
    })

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
        rename_controller=rename
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
            rename_controller=rename
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

        assert result['success'] is True
        assert result['folder_restored'] is False
        assert result['folder_path'] is None
        assert result['files_loaded'] == 0
        assert result['metadata_loaded'] == 0
        assert len(result['errors']) == 0

    def test_nonexistent_folder(self, controller):
        """Test with nonexistent folder."""
        result = controller.restore_last_session_workflow(
            last_folder="/nonexistent/folder"
        )

        assert result['success'] is False
        assert result['folder_restored'] is False
        assert result['folder_path'] is None
        assert result['files_loaded'] == 0
        assert len(result['errors']) == 1
        assert "no longer exists" in result['errors'][0]

    @patch('os.path.exists')
    def test_successful_folder_restoration(
        self, mock_exists, controller, mock_controllers
    ):
        """Test successful folder restoration without metadata."""
        mock_exists.return_value = True
        file_load, _, _ = mock_controllers

        result = controller.restore_last_session_workflow(
            last_folder="/test/folder",
            recursive=False,
            load_metadata=False
        )

        # Verify FileLoadController was called
        file_load.load_folder.assert_called_once()
        call_args = file_load.load_folder.call_args
        assert str(call_args[0][0]) == "/test/folder"
        assert call_args[1]['merge'] is False
        assert call_args[1]['recursive'] is False

        # Verify result
        assert result['success'] is True
        assert result['folder_restored'] is True
        assert result['folder_path'] == "/test/folder"
        assert result['files_loaded'] == 5
        assert result['metadata_loaded'] == 0
        assert len(result['errors']) == 0

    @patch('os.path.exists')
    def test_successful_folder_with_metadata(
        self, mock_exists, controller, mock_controllers, mock_app_context
    ):
        """Test successful folder restoration with metadata loading."""
        mock_exists.return_value = True
        file_load, metadata, _ = mock_controllers

        # Mock loaded files
        mock_file1 = MagicMock()
        mock_file2 = MagicMock()
        mock_app_context.file_store.get_loaded_files.return_value = [
            mock_file1,
            mock_file2
        ]

        result = controller.restore_last_session_workflow(
            last_folder="/test/folder",
            recursive=True,
            load_metadata=True
        )

        # Verify FileLoadController was called
        file_load.load_folder.assert_called_once()
        call_args = file_load.load_folder.call_args
        assert call_args[1]['recursive'] is True

        # Verify MetadataController was called
        metadata.load_metadata.assert_called_once()
        meta_call_args = metadata.load_metadata.call_args
        assert meta_call_args[1]['items'] == [mock_file1, mock_file2]
        assert meta_call_args[1]['use_extended'] is False
        assert meta_call_args[1]['source'] == "session_restore"

        # Verify result
        assert result['success'] is True
        assert result['folder_restored'] is True
        assert result['files_loaded'] == 5
        assert result['metadata_loaded'] == 5
        assert len(result['errors']) == 0

    @patch('os.path.exists')
    def test_folder_load_failure(self, mock_exists, controller, mock_controllers):
        """Test folder load failure."""
        mock_exists.return_value = True
        file_load, _, _ = mock_controllers

        # Mock failed folder load
        file_load.load_folder.return_value = {
            'success': False,
            'loaded_count': 0,
            'errors': ['Failed to load folder']
        }

        result = controller.restore_last_session_workflow(
            last_folder="/test/folder"
        )

        assert result['success'] is False
        assert result['folder_restored'] is False
        assert result['files_loaded'] == 0
        assert len(result['errors']) == 1
        assert 'Failed to load folder' in result['errors'][0]

    @patch('os.path.exists')
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
            'success': False,
            'loaded_count': 0,
            'errors': ['Metadata load failed']
        }

        result = controller.restore_last_session_workflow(
            last_folder="/test/folder",
            load_metadata=True
        )

        # Folder should still be considered successfully restored
        assert result['success'] is True
        assert result['folder_restored'] is True
        assert result['files_loaded'] == 5
        assert result['metadata_loaded'] == 0
        # Error should be logged but not critical
        assert 'Metadata load failed' in result['errors'][0]

    @patch('os.path.exists')
    def test_with_sort_configuration(self, mock_exists, controller):
        """Test that sort configuration is preserved in result."""
        mock_exists.return_value = True

        result = controller.restore_last_session_workflow(
            last_folder="/test/folder",
            sort_column=2,
            sort_order=1  # Descending
        )

        assert result['success'] is True
        assert result['sort_column'] == 2
        assert result['sort_order'] == 1

    @patch('os.path.exists')
    def test_exception_during_file_load(
        self, mock_exists, controller, mock_controllers
    ):
        """Test exception handling during file load."""
        mock_exists.return_value = True
        file_load, _, _ = mock_controllers

        # Mock exception during load
        file_load.load_folder.side_effect = Exception("Unexpected error")

        result = controller.restore_last_session_workflow(
            last_folder="/test/folder"
        )

        assert result['success'] is False
        assert result['folder_restored'] is False
        assert len(result['errors']) == 1
        assert "Error loading folder" in result['errors'][0]

    @patch('os.path.exists')
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
            last_folder="/test/folder",
            load_metadata=True
        )

        # Folder should still be considered restored (metadata not critical)
        assert result['success'] is True
        assert result['folder_restored'] is True
        assert result['files_loaded'] == 5
        assert len(result['errors']) == 1
        assert "Error loading metadata" in result['errors'][0]

    @patch('os.path.exists')
    def test_no_files_loaded_skips_metadata(
        self, mock_exists, controller, mock_controllers
    ):
        """Test that metadata loading is skipped if no files were loaded."""
        mock_exists.return_value = True
        file_load, metadata, _ = mock_controllers

        # Mock empty folder
        file_load.load_folder.return_value = {
            'success': True,
            'loaded_count': 0,
            'errors': []
        }

        result = controller.restore_last_session_workflow(
            last_folder="/test/folder",
            load_metadata=True
        )

        # Metadata should not be loaded if no files
        metadata.load_metadata.assert_not_called()

        assert result['success'] is True
        assert result['files_loaded'] == 0
        assert result['metadata_loaded'] == 0
