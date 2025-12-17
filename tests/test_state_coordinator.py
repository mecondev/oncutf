"""
Tests for StateCoordinator.

Author: Michael Economou
Date: 2025-12-16
"""


from oncutf.controllers.state_coordinator import StateCoordinator
from oncutf.core.file_store import FileStore
from oncutf.models.file_item import FileItem


class TestStateCoordinatorCreation:
    """Test StateCoordinator creation and initialization."""

    def test_create_state_coordinator(self, qtbot):
        """Test creating a StateCoordinator."""
        assert qtbot is not None
        file_store = FileStore()
        coordinator = StateCoordinator(file_store)
        assert coordinator.get_file_store() is file_store

class TestStateCoordinatorFilesChanged:
    """Test StateCoordinator files_changed signal."""

    def test_notify_files_changed_emits_signal(self, qtbot):
        """Test that notify_files_changed emits signal and updates store."""
        file_store = FileStore()
        coordinator = StateCoordinator(file_store)
        # Create test files
        file1 = FileItem.from_path("/test/file1.txt")
        file2 = FileItem.from_path("/test/file2.txt")
        files = [file1, file2]

        # Wait for signals
        with (
            qtbot.waitSignal(coordinator.files_changed, timeout=1000),
            qtbot.waitSignal(coordinator.preview_invalidated, timeout=1000),
        ):
            coordinator.notify_files_changed(files)

        # Verify file store was updated
        assert file_store.get_loaded_files() == files

    def test_files_changed_signal_payload(self, qtbot):
        """Test that files_changed signal carries correct payload."""
        file_store = FileStore()
        coordinator = StateCoordinator(file_store)


        file1 = FileItem.from_path("/test/file1.txt")
        files = [file1]

        received_files = []

        def on_files_changed(files_list):
            received_files.extend(files_list)

        coordinator.files_changed.connect(on_files_changed)

        with qtbot.waitSignal(coordinator.files_changed, timeout=1000):
            coordinator.notify_files_changed(files)

        assert received_files == files

class TestStateCoordinatorSelectionChanged:
    """Test StateCoordinator selection_changed signal."""

    def test_notify_selection_changed_emits_signal(self, qtbot):
        """Test that notify_selection_changed emits signal."""
        file_store = FileStore()
        coordinator = StateCoordinator(file_store)


        selected = {0, 1, 2}

        with qtbot.waitSignal(coordinator.selection_changed, timeout=1000):
            coordinator.notify_selection_changed(selected)

    def test_selection_changed_signal_payload(self, qtbot):
        """Test that selection_changed signal carries correct payload."""
        file_store = FileStore()
        coordinator = StateCoordinator(file_store)


        selected = {0, 1, 2}
        received_selection = None

        def on_selection_changed(selection):
            nonlocal received_selection
            received_selection = selection

        coordinator.selection_changed.connect(on_selection_changed)

        with qtbot.waitSignal(coordinator.selection_changed, timeout=1000):
            coordinator.notify_selection_changed(selected)

        assert received_selection == selected

class TestStateCoordinatorPreviewInvalidated:
    """Test StateCoordinator preview_invalidated signal."""

    def test_notify_preview_invalidated_emits_signal(self, qtbot):
        """Test that notify_preview_invalidated emits signal."""
        file_store = FileStore()
        coordinator = StateCoordinator(file_store)


        with qtbot.waitSignal(coordinator.preview_invalidated, timeout=1000):
            coordinator.notify_preview_invalidated()

    def test_preview_invalidated_on_files_changed(self, qtbot):
        """Test that preview is invalidated when files change."""
        file_store = FileStore()
        coordinator = StateCoordinator(file_store)


        file1 = FileItem.from_path("/test/file1.txt")

        # Both signals should be emitted
        with qtbot.waitSignals(
            [coordinator.files_changed, coordinator.preview_invalidated],
            timeout=1000
        ):
            coordinator.notify_files_changed([file1])

    def test_preview_invalidated_on_metadata_changed(self, qtbot):
        """Test that preview is invalidated when metadata changes."""
        file_store = FileStore()
        coordinator = StateCoordinator(file_store)


        # Both metadata_changed and preview_invalidated should emit
        with qtbot.waitSignals(
            [coordinator.metadata_changed, coordinator.preview_invalidated],
            timeout=1000
        ):
            coordinator.notify_metadata_changed("/test/file1.txt")

class TestStateCoordinatorMetadataChanged:
    """Test StateCoordinator metadata_changed signal."""

    def test_notify_metadata_changed_emits_signal(self, qtbot):
        """Test that notify_metadata_changed emits signal."""
        file_store = FileStore()
        coordinator = StateCoordinator(file_store)


        with qtbot.waitSignal(coordinator.metadata_changed, timeout=1000):
            coordinator.notify_metadata_changed("/test/file1.txt")

    def test_metadata_changed_signal_payload(self, qtbot):
        """Test that metadata_changed signal carries correct payload."""
        file_store = FileStore()
        coordinator = StateCoordinator(file_store)


        file_path = "/test/file1.txt"
        received_path = None

        def on_metadata_changed(path):
            nonlocal received_path
            received_path = path

        coordinator.metadata_changed.connect(on_metadata_changed)

        with qtbot.waitSignal(coordinator.metadata_changed, timeout=1000):
            coordinator.notify_metadata_changed(file_path)

        assert received_path == file_path

class TestStateCoordinatorIntegration:
    """Test StateCoordinator integration scenarios."""

    def test_multiple_signals_coordination(self, qtbot):
        """Test that multiple state changes can be coordinated."""
        file_store = FileStore()
        coordinator = StateCoordinator(file_store)


        file1 = FileItem.from_path("/test/file1.txt")
        files = [file1]

        # Track signal emissions
        signals_received = []

        def on_files_changed(_files):
            signals_received.append("files_changed")

        def on_selection_changed(_selection):
            signals_received.append("selection_changed")

        def on_preview_invalidated():
            signals_received.append("preview_invalidated")

        coordinator.files_changed.connect(on_files_changed)
        coordinator.selection_changed.connect(on_selection_changed)
        coordinator.preview_invalidated.connect(on_preview_invalidated)

        # Change files
        with qtbot.waitSignal(coordinator.files_changed, timeout=1000):
            coordinator.notify_files_changed(files)

        # Change selection
        with qtbot.waitSignal(coordinator.selection_changed, timeout=1000):
            coordinator.notify_selection_changed({0})

        # Invalidate preview
        with qtbot.waitSignal(coordinator.preview_invalidated, timeout=1000):
            coordinator.notify_preview_invalidated()

        # Verify all signals were received
        assert "files_changed" in signals_received
        assert "selection_changed" in signals_received
        assert "preview_invalidated" in signals_received
        # Preview should be invalidated at least twice (files + explicit)
        assert signals_received.count("preview_invalidated") >= 2
