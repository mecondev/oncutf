"""
Module: test_filesystem_monitor.py

Author: Michael Economou
Date: 2025-12-16

Tests for FilesystemMonitor.
"""

import platform
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from oncutf.core.filesystem_monitor import FilesystemMonitor


class TestFilesystemMonitor:
    """Test filesystem monitoring."""

    @pytest.fixture
    def monitor(self):
        """Create FilesystemMonitor instance."""
        mon = FilesystemMonitor()
        yield mon
        # Cleanup
        mon.stop()

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_monitor_creation(self):
        """Test monitor instantiation."""
        monitor = FilesystemMonitor()
        assert monitor is not None
        assert monitor.file_store is None
        monitor.stop()

    def test_monitor_with_file_store(self):
        """Test monitor with FileStore."""
        mock_store = MagicMock()
        monitor = FilesystemMonitor(file_store=mock_store)
        assert monitor.file_store is mock_store
        monitor.stop()

    def test_monitor_start_stop(self, monitor):
        """Test starting and stopping monitor."""
        monitor.start()
        # Check timer is running
        assert monitor._drive_poll_timer.isActive()

        monitor.stop()
        # Check timer stopped
        assert not monitor._drive_poll_timer.isActive()

    def test_add_folder(self, monitor, temp_dir):
        """Test adding folder to monitoring."""
        success = monitor.add_folder(temp_dir)
        assert success
        assert (
            temp_dir in monitor._monitored_folders
            or str(Path(temp_dir).resolve()) in monitor._monitored_folders
        )

    def test_add_nonexistent_folder(self, monitor):
        """Test adding non-existent folder fails."""
        success = monitor.add_folder("/nonexistent/folder")
        assert not success
        assert len(monitor._monitored_folders) == 0

    def test_add_folder_twice(self, monitor, temp_dir):
        """Test adding same folder twice."""
        success1 = monitor.add_folder(temp_dir)
        success2 = monitor.add_folder(temp_dir)
        assert success1
        assert success2
        # Should only be added once
        assert len(monitor._monitored_folders) == 1

    def test_remove_folder(self, monitor, temp_dir):
        """Test removing folder from monitoring."""
        monitor.add_folder(temp_dir)
        success = monitor.remove_folder(temp_dir)
        assert success
        assert temp_dir not in monitor._monitored_folders

    def test_remove_unmonitored_folder(self, monitor):
        """Test removing folder that isn't monitored."""
        success = monitor.remove_folder("/some/path")
        assert success  # Should succeed (no-op)

    def test_clear_folders(self, monitor, temp_dir):
        """Test clearing all monitored folders."""
        # Add multiple folders
        monitor.add_folder(temp_dir)

        # Create second temp dir
        with tempfile.TemporaryDirectory() as tmpdir2:
            monitor.add_folder(tmpdir2)

            # Clear all
            monitor.clear_folders()
            assert len(monitor._monitored_folders) == 0

    def test_get_available_drives(self, monitor):
        """Test getting available drives."""
        drives = monitor._get_available_drives()
        assert isinstance(drives, set)
        # In CI environments, there may be no mount points
        # Just verify the method works and returns a set
        if platform.system() == "Windows":
            # Windows should always have at least C:\
            assert len(drives) >= 1
        # On Linux/macOS, drives may be empty in CI

    @pytest.mark.skipif(platform.system() != "Linux", reason="Linux-specific test")
    def test_get_drives_linux(self, monitor):
        """Test drive detection on Linux."""
        drives = monitor._get_available_drives()
        # On Linux, should check /media and /mnt
        assert isinstance(drives, set)

    def test_drive_added_signal(self, monitor, qtbot):
        """Test drive_added signal emission."""
        # Mock _get_available_drives to simulate drive addition
        monitor._current_drives = {"/existing/drive"}

        with qtbot.waitSignal(monitor.drive_added, timeout=100) as blocker:
            # Simulate new drive
            monitor._current_drives = {"/existing/drive"}
            new_drives = {"/existing/drive", "/new/drive"}

            with patch.object(monitor, "_get_available_drives", return_value=new_drives):
                monitor._poll_drives()

        assert blocker.args[0] == "/new/drive"

    def test_drive_removed_signal(self, monitor, qtbot):
        """Test drive_removed signal emission."""
        # Setup initial state
        monitor._current_drives = {"/drive1", "/drive2"}

        with qtbot.waitSignal(monitor.drive_removed, timeout=100) as blocker:
            # Simulate drive removal
            new_drives = {"/drive1"}

            with patch.object(monitor, "_get_available_drives", return_value=new_drives):
                monitor._poll_drives()

        assert blocker.args[0] == "/drive2"

    def test_directory_changed_signal(self, monitor, temp_dir, qtbot):
        """Test directory_changed signal emission."""
        # Add folder to monitoring
        monitor.add_folder(temp_dir)

        # Wait for signal (with timeout)
        with qtbot.waitSignal(monitor.directory_changed, timeout=2000):
            # Create a file in the directory
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test")

            # Process events to allow watcher to trigger
            import time

            time.sleep(0.1)
            qtbot.wait(100)

    def test_set_drive_change_callback(self, monitor):
        """Test setting drive change callback."""
        callback = MagicMock()
        monitor.set_drive_change_callback(callback)
        assert monitor._on_drive_change_callback is callback

    def test_set_folder_change_callback(self, monitor):
        """Test setting folder change callback."""
        callback = MagicMock()
        monitor.set_folder_change_callback(callback)
        assert monitor._on_folder_change_callback is callback

    def test_get_monitored_folders(self, monitor, temp_dir):
        """Test getting monitored folders list."""
        monitor.add_folder(temp_dir)
        folders = monitor.get_monitored_folders()
        assert isinstance(folders, list)
        assert len(folders) == 1

    def test_get_current_drives(self, monitor):
        """Test getting current drives list."""
        monitor.start()
        drives = monitor.get_current_drives()
        assert isinstance(drives, list)
        # In CI environments, there may be no mount points
        if platform.system() == "Windows":
            # Windows should always have at least C:\
            assert len(drives) >= 1
        # On Linux/macOS, drives may be empty in CI
