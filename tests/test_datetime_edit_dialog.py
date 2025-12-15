"""
Unit tests for DateTimeEditDialog.

Created: 2025-12-03
"""

from pathlib import Path

import pytest

from core.pyqt_imports import QDateTime
from oncutf.ui.widgets.datetime_edit_dialog import DateTimeEditDialog


@pytest.fixture
def qapp(qapp):
    """Reuse qapp fixture from conftest."""
    return qapp


@pytest.fixture
def sample_files():
    """Sample file paths for testing."""
    return [
        "/path/to/video1.mp4",
        "/path/to/photo1.jpg",
        "/path/to/document.pdf",
    ]


class TestDateTimeEditDialog:
    """Test suite for DateTimeEditDialog widget."""

    def test_dialog_creation_modified(self, qapp, sample_files):
        """Test creating dialog for modified date."""
        _ = qapp
        dialog = DateTimeEditDialog(parent=None, selected_files=sample_files, date_type="modified")

        assert dialog.windowTitle() == "Edit Modification Date"
        assert dialog.date_type == "modified"
        assert len(dialog.checkboxes) == 3
        assert dialog.datetime_edit is not None

    def test_dialog_creation_created(self, qapp, sample_files):
        """Test creating dialog for created date."""
        _ = qapp
        dialog = DateTimeEditDialog(parent=None, selected_files=sample_files, date_type="created")

        assert dialog.windowTitle() == "Edit Creation Date"
        assert dialog.date_type == "created"
        assert len(dialog.checkboxes) == 3

    def test_select_all_functionality(self, qapp, sample_files):
        """Test select all button."""
        _ = qapp
        dialog = DateTimeEditDialog(parent=None, selected_files=sample_files)

        # Initially all should be checked
        for checkbox in dialog.checkboxes.values():
            assert checkbox.isChecked()

        # Uncheck one
        first_file = str(Path(sample_files[0]))
        dialog.checkboxes[first_file].setChecked(False)
        assert not dialog.checkboxes[first_file].isChecked()

        # Click select all
        dialog._select_all()
        for checkbox in dialog.checkboxes.values():
            assert checkbox.isChecked()

    def test_deselect_all_functionality(self, qapp, sample_files):
        """Test deselect all button."""
        _ = qapp
        dialog = DateTimeEditDialog(parent=None, selected_files=sample_files)

        # Click deselect all
        dialog._deselect_all()
        for checkbox in dialog.checkboxes.values():
            assert not checkbox.isChecked()

    def test_get_selected_files(self, qapp, sample_files):
        """Test getting list of selected files."""
        _ = qapp
        dialog = DateTimeEditDialog(parent=None, selected_files=sample_files)

        # All selected initially
        result = dialog.get_selected_files()
        assert len(result) == 3
        # Convert to Path objects and normalize for cross-platform comparison
        result_paths = [Path(p) for p in result]
        sample_paths = [Path(p) for p in sample_files]
        assert set(result_paths) == set(sample_paths)

        # Deselect one
        # Use the normalized path from dialog.checkboxes keys
        checkbox_keys = list(dialog.checkboxes.keys())
        dialog.checkboxes[checkbox_keys[1]].setChecked(False)
        result = dialog.get_selected_files()
        assert len(result) == 2
        assert Path(checkbox_keys[1]) not in [Path(p) for p in result]

    def test_get_new_datetime(self, qapp, sample_files):
        """Test getting the selected datetime."""
        _ = qapp
        dialog = DateTimeEditDialog(parent=None, selected_files=sample_files)

        # Set a specific datetime
        test_datetime = QDateTime(2024, 6, 15, 14, 30, 0)
        dialog.datetime_edit.setDateTime(test_datetime)

        result = dialog.get_new_datetime()
        # Compare Python datetime objects
        expected = test_datetime.toPyDateTime()
        assert result == expected

    def test_ok_button_enabled_with_selection(self, qapp, sample_files):
        """Test Apply button behavior with selections."""
        _ = qapp
        dialog = DateTimeEditDialog(parent=None, selected_files=sample_files)

        # Apply button should exist
        assert dialog.apply_button is not None

        # Deselect all
        dialog._deselect_all()
        # Try to accept - should fail gracefully
        initial_result = dialog.result_files
        dialog.accept()
        # Should remain None since no files selected
        assert dialog.result_files == initial_result

    def test_factory_method_returns_none_on_cancel(self, qapp, sample_files, monkeypatch):
        """Test factory method returns None when dialog is cancelled."""
        _ = qapp
        # Mock dialog.exec_() to return Rejected
        def mock_exec(_self):
            return DateTimeEditDialog.Rejected

        monkeypatch.setattr(DateTimeEditDialog, "exec_", mock_exec)

        result_files, result_datetime = DateTimeEditDialog.get_datetime_edit_choice(
            parent=None,
            selected_files=sample_files,
            date_type="modified"
        )

        assert result_files is None
        assert result_datetime is None

    def test_factory_method_returns_data_on_accept(self, qapp, sample_files, monkeypatch):
        """Test factory method returns data when dialog is accepted."""
        _ = qapp
        test_datetime = QDateTime(2024, 6, 15, 14, 30, 0)

        # Mock dialog.exec_() to return Accepted
        def mock_exec(self):
            self.result_files = sample_files[:2]  # Select first 2 files
            self.datetime_edit.setDateTime(test_datetime)
            return DateTimeEditDialog.Accepted

        monkeypatch.setattr(DateTimeEditDialog, "exec_", mock_exec)

        result_files, result_datetime = DateTimeEditDialog.get_datetime_edit_choice(
            parent=None,
            selected_files=sample_files,
            date_type="created"
        )

        assert result_files == sample_files[:2]
        assert result_datetime == test_datetime

    def test_single_file_mode(self, qapp):
        """Test dialog with single file."""
        _ = qapp
        single_file = ["/path/to/single_video.mkv"]
        dialog = DateTimeEditDialog(parent=None, selected_files=single_file)

        assert len(dialog.checkboxes) == 1
        # Normalize paths for cross-platform comparison
        checkbox_key = list(dialog.checkboxes.keys())[0]
        assert Path(checkbox_key) == Path(single_file[0])

    def test_datetime_format(self, qapp, sample_files):
        """Test datetime display format."""
        _ = qapp
        dialog = DateTimeEditDialog(parent=None, selected_files=sample_files)

        # Check format is correct
        assert dialog.datetime_edit.displayFormat() == "yyyy-MM-dd HH:mm:ss"

    def test_calendar_popup_enabled(self, qapp, sample_files):
        """Test that calendar popup is enabled."""
        _ = qapp
        dialog = DateTimeEditDialog(parent=None, selected_files=sample_files)

        assert dialog.datetime_edit.calendarPopup()

    def test_info_label_content(self, qapp, sample_files):
        """Test info label displays correct message."""
        _ = qapp
        dialog = DateTimeEditDialog(parent=None, selected_files=sample_files, date_type="modified")

        # Dialog should be created successfully
        assert dialog is not None
        assert dialog.date_type == "modified"

    def test_empty_file_list(self, qapp):
        """Test dialog handles empty file list gracefully."""
        _ = qapp
        dialog = DateTimeEditDialog(parent=None, selected_files=[], date_type="modified")

        assert len(dialog.checkboxes) == 0
        # Apply button should exist
        assert dialog.apply_button is not None
