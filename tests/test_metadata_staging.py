
from unittest.mock import MagicMock

from oncutf.core.metadata_staging_manager import MetadataStagingManager


class TestMetadataStagingManager:
    def test_initialization(self):
        manager = MetadataStagingManager()
        assert manager._staged_changes == {}

    def test_stage_change(self):
        manager = MetadataStagingManager()
        file_path = "/path/to/file.jpg"

        # Test staging a new change
        manager.stage_change(file_path, "Rotation", "90")
        assert manager.has_staged_changes(file_path)
        changes = manager.get_staged_changes(file_path)
        assert changes["Rotation"] == "90"

        # Test updating an existing change
        manager.stage_change(file_path, "Rotation", "180")
        changes = manager.get_staged_changes(file_path)
        assert changes["Rotation"] == "180"

        # Test adding another field
        manager.stage_change(file_path, "Title", "Test Image")
        changes = manager.get_staged_changes(file_path)
        assert changes["Rotation"] == "180"
        assert changes["Title"] == "Test Image"

    def test_clear_staged_changes(self):
        manager = MetadataStagingManager()
        file_path = "/path/to/file.jpg"

        manager.stage_change(file_path, "Rotation", "90")
        assert manager.has_staged_changes(file_path)

        manager.clear_staged_changes(file_path)
        assert not manager.has_staged_changes(file_path)
        assert manager.get_staged_changes(file_path) == {}

    def test_clear_all(self):
        manager = MetadataStagingManager()
        file1 = "/path/to/file1.jpg"
        file2 = "/path/to/file2.jpg"

        manager.stage_change(file1, "Rotation", "90")
        manager.stage_change(file2, "Title", "Test")

        assert manager.has_staged_changes(file1)
        assert manager.has_staged_changes(file2)

        manager.clear_all()

        assert not manager.has_staged_changes(file1)
        assert not manager.has_staged_changes(file2)
        assert manager.get_all_staged_changes() == {}

    def test_signals(self):
        manager = MetadataStagingManager()
        file_path = "/path/to/file.jpg"

        # Mock signal slots
        mock_staged = MagicMock()
        mock_cleared = MagicMock()
        mock_all_cleared = MagicMock()

        manager.change_staged.connect(mock_staged)
        manager.file_cleared.connect(mock_cleared)
        manager.all_cleared.connect(mock_all_cleared)

        # Test stage signal
        manager.stage_change(file_path, "Rotation", "90")
        mock_staged.assert_called_with(file_path, "Rotation", "90")

        # Test file clear signal
        manager.clear_staged_changes(file_path)
        mock_cleared.assert_called_with(file_path)

        # Test all clear signal
        manager.clear_all()
        mock_all_cleared.assert_called_once()

    def test_path_normalization(self):
        manager = MetadataStagingManager()
        # Simulate different path separators if possible, or just check consistency
        # Since normalize_path handles OS differences, we just check that it works
        # consistently for the same logical path

        path1 = "/path/to/file.jpg"
        path2 = "/path/to/file.jpg" # Same path

        manager.stage_change(path1, "Key", "Value")
        assert manager.has_staged_changes(path2)
        assert manager.get_staged_changes(path2)["Key"] == "Value"
