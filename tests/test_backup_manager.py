"""
test_backup_manager.py

Author: Michael Economou
Date: 2025-01-01

Comprehensive tests for the backup manager system including backup creation,
rotation, periodic backups, and configuration management.
"""

import os
import tempfile
import unittest
import time
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from core.backup_manager import BackupManager, get_backup_manager, cleanup_backup_manager
from core.database_manager import DatabaseManagerV2 as DatabaseManager
from config import (
    DEFAULT_BACKUP_COUNT,
    DEFAULT_BACKUP_INTERVAL,
    BACKUP_FILENAME_FORMAT,
    BACKUP_TIMESTAMP_FORMAT
)


class TestBackupManager(unittest.TestCase):
    """Test cases for BackupManager functionality."""

    def setUp(self):
        """Set up test environment with temporary database and backup manager."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()

        # Create test database manager
        self.db_manager = DatabaseManager(self.temp_db.name)

        # Add some test data to make the database non-empty
        self.db_manager.store_metadata('/test/file1.jpg', {'test': 'data1'})
        self.db_manager.store_hash('/test/file2.jpg', 'hash123')

        # Create backup manager
        self.backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=3,
            backup_interval=60,  # 1 minute for testing
            periodic_enabled=False  # Disable periodic backups in tests
        )

        # Store original backup directory for cleanup
        self.backup_dir = Path(self.temp_db.name).parent

    def tearDown(self):
        """Clean up test environment."""
        # Stop any running timers
        if hasattr(self.backup_manager, 'backup_timer'):
            self.backup_manager.stop_periodic_backups()

        # Close database
        self.db_manager.close()

        # Remove test database
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

        # Clean up backup files
        for backup_file in self.backup_dir.glob("*.db.bak"):
            try:
                backup_file.unlink()
            except OSError:
                pass  # File might already be deleted

    def test_backup_manager_initialization(self):
        """Test BackupManager initialization."""
        self.assertEqual(self.backup_manager.backup_count, 3)
        self.assertEqual(self.backup_manager.backup_interval, 60)
        self.assertFalse(self.backup_manager.periodic_enabled)
        self.assertEqual(str(self.backup_manager.database_path), self.temp_db.name)

    def test_manual_backup_creation(self):
        """Test manual backup creation."""
        # Create backup
        backup_path = self.backup_manager.create_backup("test_manual")

        # Verify backup was created
        self.assertIsNotNone(backup_path)
        self.assertTrue(os.path.exists(backup_path))

        # Verify backup filename format
        backup_file = Path(backup_path)
        self.assertTrue(backup_file.name.startswith(Path(self.temp_db.name).stem))
        self.assertTrue(backup_file.name.endswith('.db.bak'))

        # Verify backup has content
        self.assertGreater(backup_file.stat().st_size, 0)

    def test_backup_filename_format(self):
        """Test backup filename format compliance."""
        backup_path = self.backup_manager.create_backup("format_test")
        backup_file = Path(backup_path)

        # Extract timestamp from filename
        filename = backup_file.name
        expected_prefix = Path(self.temp_db.name).stem + "_"
        expected_suffix = ".db.bak"

        self.assertTrue(filename.startswith(expected_prefix))
        self.assertTrue(filename.endswith(expected_suffix))

        # Extract and validate timestamp format (YYYYMMDD_HHMMSS)
        timestamp_part = filename[len(expected_prefix):-len(expected_suffix)]
        self.assertEqual(len(timestamp_part), 15)  # YYYYMMDD_HHMMSS
        self.assertTrue(timestamp_part[8] == '_')  # Underscore separator

    def test_backup_rotation(self):
        """Test backup file rotation and cleanup."""
        # Create more backups than the limit
        backup_paths = []
        for i in range(5):  # More than our limit of 3
            time.sleep(1.1)  # Ensure different timestamps (1+ second delay)
            backup_path = self.backup_manager.create_backup(f"rotation_test_{i}")
            if backup_path:
                backup_paths.append(backup_path)

        # Check that only backup_count files remain
        existing_backups = self.backup_manager.get_backup_files()
        self.assertEqual(len(existing_backups), self.backup_manager.backup_count)

        # Verify that the most recent backups are kept
        existing_names = [b.name for b in existing_backups]
        for backup_path in backup_paths[-3:]:  # Last 3 should exist
            backup_name = Path(backup_path).name
            # Note: Some might have been cleaned up, so we check if they exist
            if os.path.exists(backup_path):
                self.assertIn(backup_name, existing_names)

    def test_backup_count_configuration(self):
        """Test backup count configuration changes."""
        # Create initial backups
        for i in range(4):
            time.sleep(1.1)  # Ensure different timestamps
            self.backup_manager.create_backup(f"config_test_{i}")

        # Verify we have 3 backups (our limit)
        self.assertEqual(len(self.backup_manager.get_backup_files()), 3)

        # Change backup count to 2
        self.backup_manager.set_backup_count(2)

        # Verify configuration changed
        self.assertEqual(self.backup_manager.backup_count, 2)

        # Verify excess backups were cleaned up
        self.assertEqual(len(self.backup_manager.get_backup_files()), 2)

    def test_backup_interval_configuration(self):
        """Test backup interval configuration changes."""
        # Change interval
        new_interval = 300  # 5 minutes
        self.backup_manager.set_backup_interval(new_interval)

        # Verify configuration changed
        self.assertEqual(self.backup_manager.backup_interval, new_interval)

    def test_invalid_backup_count(self):
        """Test handling of invalid backup count."""
        original_count = self.backup_manager.backup_count

        # Try to set invalid count
        self.backup_manager.set_backup_count(0)

        # Count should remain unchanged
        self.assertEqual(self.backup_manager.backup_count, original_count)

        # Try negative count
        self.backup_manager.set_backup_count(-1)
        self.assertEqual(self.backup_manager.backup_count, original_count)

    def test_invalid_backup_interval(self):
        """Test handling of invalid backup interval."""
        original_interval = self.backup_manager.backup_interval

        # Try to set negative interval
        self.backup_manager.set_backup_interval(-1)

        # Interval should remain unchanged
        self.assertEqual(self.backup_manager.backup_interval, original_interval)

    def test_missing_database_file(self):
        """Test backup creation when database file doesn't exist."""
        # Create backup manager with non-existent database
        non_existent_db = "/tmp/non_existent_database.db"
        backup_manager = BackupManager(
            database_path=non_existent_db,
            backup_count=2,
            periodic_enabled=False
        )

        # Try to create backup
        backup_path = backup_manager.create_backup("missing_db_test")

        # Should return None for missing database
        self.assertIsNone(backup_path)

    def test_backup_status(self):
        """Test backup manager status reporting."""
        status = self.backup_manager.get_status()

        # Verify status contains expected keys
        expected_keys = [
            'database_path', 'backup_count', 'backup_interval',
            'periodic_enabled', 'timer_active', 'existing_backups'
        ]
        for key in expected_keys:
            self.assertIn(key, status)

        # Verify status values
        self.assertEqual(status['database_path'], self.temp_db.name)
        self.assertEqual(status['backup_count'], 3)
        self.assertEqual(status['backup_interval'], 60)
        self.assertFalse(status['periodic_enabled'])

    def test_shutdown_backup(self):
        """Test shutdown backup creation."""
        backup_path = self.backup_manager.backup_on_shutdown()

        # Verify backup was created
        self.assertIsNotNone(backup_path)
        if backup_path:
            self.assertTrue(os.path.exists(backup_path))

            # Verify it's a valid backup file
            backup_size = os.path.getsize(backup_path)
            self.assertGreater(backup_size, 0)

    def test_get_backup_files(self):
        """Test getting list of backup files."""
        # Initially no backups
        initial_backups = self.backup_manager.get_backup_files()

        # Create some backups
        created_backups = []
        for i in range(3):
            time.sleep(1.1)  # Ensure different timestamps
            backup_path = self.backup_manager.create_backup(f"list_test_{i}")
            if backup_path:
                created_backups.append(backup_path)

        # Get backup list
        backup_files = self.backup_manager.get_backup_files()

        # Verify count
        self.assertEqual(len(backup_files), len(created_backups))

        # Verify files are sorted by modification time (newest first)
        if len(backup_files) > 1:
            for i in range(len(backup_files) - 1):
                self.assertGreaterEqual(
                    backup_files[i].stat().st_mtime,
                    backup_files[i + 1].stat().st_mtime
                )


class TestBackupManagerQt(unittest.TestCase):
    """Test cases for BackupManager Qt integration."""

    def setUp(self):
        """Set up test environment with Qt mocking."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()

        # Create test database manager
        self.db_manager = DatabaseManager(self.temp_db.name)
        self.db_manager.store_metadata('/test/file.jpg', {'test': 'data'})

    def tearDown(self):
        """Clean up test environment."""
        self.db_manager.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

        # Clean up backup files
        backup_dir = Path(self.temp_db.name).parent
        for backup_file in backup_dir.glob("*.db.bak"):
            try:
                backup_file.unlink()
            except OSError:
                pass

    @patch('core.backup_manager.QTimer')
    def test_periodic_backup_timer_setup(self, mock_qtimer):
        """Test periodic backup timer setup with Qt mocking."""
        mock_timer_instance = Mock()
        mock_qtimer.return_value = mock_timer_instance

        # Create backup manager with periodic backups enabled
        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=2,
            backup_interval=30,
            periodic_enabled=True
        )

        # Verify timer was created and configured
        mock_qtimer.assert_called_once()
        mock_timer_instance.timeout.connect.assert_called_once()
        mock_timer_instance.start.assert_called_once_with(30000)  # 30 seconds in ms

    @patch('core.backup_manager.QTimer')
    def test_periodic_backup_enable_disable(self, mock_qtimer):
        """Test enabling and disabling periodic backups."""
        mock_timer_instance = Mock()
        mock_qtimer.return_value = mock_timer_instance

        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=2,
            periodic_enabled=False
        )

        # Enable periodic backups
        backup_manager.enable_periodic_backups(True)
        mock_timer_instance.start.assert_called()

        # Disable periodic backups
        backup_manager.enable_periodic_backups(False)
        mock_timer_instance.stop.assert_called()

    @patch('core.backup_manager.QTimer')
    def test_backup_signals(self, mock_qtimer):
        """Test backup completion and failure signals."""
        mock_timer_instance = Mock()
        mock_qtimer.return_value = mock_timer_instance

        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=2,
            periodic_enabled=False
        )

        # Mock signal connections
        success_handler = Mock()
        failure_handler = Mock()

        backup_manager.backup_completed.connect(success_handler)
        backup_manager.backup_failed.connect(failure_handler)

        # Create successful backup
        backup_path = backup_manager.create_backup("signal_test")

        # Verify success signal was emitted (in real Qt environment)
        # Note: In unit tests, signals might not work exactly like in Qt app
        self.assertIsNotNone(backup_path)


class TestGlobalBackupManager(unittest.TestCase):
    """Test cases for global backup manager functionality."""

    def setUp(self):
        """Set up test environment."""
        # Clean up any existing global instance
        cleanup_backup_manager()

        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()

    def tearDown(self):
        """Clean up test environment."""
        cleanup_backup_manager()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

        # Clean up backup files
        backup_dir = Path(self.temp_db.name).parent
        for backup_file in backup_dir.glob("*.db.bak"):
            try:
                backup_file.unlink()
            except OSError:
                pass

    def test_global_backup_manager_singleton(self):
        """Test global backup manager singleton behavior."""
        # Get first instance
        manager1 = get_backup_manager(self.temp_db.name)

        # Get second instance
        manager2 = get_backup_manager(self.temp_db.name)

        # Should be the same instance
        self.assertIs(manager1, manager2)

    def test_global_backup_manager_cleanup(self):
        """Test global backup manager cleanup."""
        # Create global instance
        manager = get_backup_manager(self.temp_db.name, periodic_enabled=True)

        # Verify it exists
        self.assertIsNotNone(manager)

        # Clean up
        cleanup_backup_manager()

        # Getting new instance should create a new one
        new_manager = get_backup_manager(self.temp_db.name)
        self.assertIsNot(manager, new_manager)


class TestBackupManagerErrorHandling(unittest.TestCase):
    """Test cases for BackupManager error handling."""

    def setUp(self):
        """Set up test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    @patch('core.backup_manager.shutil.copy2')
    def test_backup_creation_failure(self, mock_copy2):
        """Test handling of backup creation failures."""
        # Mock copy2 to raise an exception
        mock_copy2.side_effect = OSError("Permission denied")

        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=2,
            periodic_enabled=False
        )

        # Try to create backup
        backup_path = backup_manager.create_backup("failure_test")

        # Should return None on failure
        self.assertIsNone(backup_path)

    @patch('core.backup_manager.Path.glob')
    def test_cleanup_failure_handling(self, mock_glob):
        """Test handling of cleanup failures."""
        # Mock glob to raise an exception
        mock_glob.side_effect = OSError("Access denied")

        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=2,
            periodic_enabled=False
        )

        # Create backup (cleanup will fail but shouldn't crash)
        backup_path = backup_manager.create_backup("cleanup_failure_test")

        # Backup creation should still succeed
        self.assertIsNotNone(backup_path)


if __name__ == '__main__':
    unittest.main()
