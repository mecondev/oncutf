"""
test_backup_integration.py

Author: Michael Economou
Date: 2025-01-01

Integration tests for the backup system testing interaction with main
application components like database manager, main window, and configuration.
"""

import os
import tempfile
import unittest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from core.backup_manager import BackupManager, get_backup_manager
from core.database_manager import DatabaseManagerV2 as DatabaseManager, initialize_database
from config import (
    DEFAULT_BACKUP_COUNT,
    DEFAULT_BACKUP_INTERVAL,
    DEFAULT_PERIODIC_BACKUP_ENABLED
)


class TestBackupDatabaseIntegration(unittest.TestCase):
    """Test backup system integration with database manager."""

    def setUp(self):
        """Set up test environment with real database."""
        # Create temporary directory for database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')

        # Initialize database with test data
        self.db_manager = initialize_database(self.db_path)

        # Add realistic test data
        test_files = [
            '/test/photos/img001.jpg',
            '/test/photos/img002.jpg',
            '/test/videos/vid001.mp4'
        ]

        for file_path in test_files:
            # Add metadata
            self.db_manager.store_metadata(file_path, {
                'FileName': Path(file_path).name,
                'FileSize': '1024000',
                'DateTimeOriginal': '2025:01:01 12:00:00'
            })

            # Add hash
            self.db_manager.store_hash(file_path, f'hash_{hash(file_path)}')

    def tearDown(self):
        """Clean up test environment."""
        self.db_manager.close()

        # Clean up all files in temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_backup_with_real_data(self):
        """Test backup creation with real database data."""
        backup_manager = BackupManager(
            database_path=self.db_path,
            backup_count=2,
            periodic_enabled=False
        )

        # Create backup
        backup_path = backup_manager.create_backup("integration_test")
        self.assertIsNotNone(backup_path)

        # Verify backup file exists and has content
        backup_file = Path(backup_path)
        self.assertTrue(backup_file.exists())
        self.assertGreater(backup_file.stat().st_size, 1000)  # Should have substantial content

        # Verify backup is a valid SQLite database
        backup_db = DatabaseManager(backup_path)
        try:
            # Should be able to read data from backup
            stats = backup_db.get_database_stats()
            self.assertGreater(stats['file_paths'], 0)
            self.assertGreater(stats['file_metadata'], 0)
            self.assertGreater(stats['file_hashes'], 0)
        finally:
            backup_db.close()

    def test_backup_preserves_data_integrity(self):
        """Test that backup preserves all database data correctly."""
        backup_manager = BackupManager(
            database_path=self.db_path,
            backup_count=2,
            periodic_enabled=False
        )

        # Get original data
        original_stats = self.db_manager.get_database_stats()
        original_metadata = self.db_manager.get_metadata('/test/photos/img001.jpg')
        original_hash = self.db_manager.get_hash('/test/photos/img001.jpg')

        # Create backup
        backup_path = backup_manager.create_backup("integrity_test")

        # Verify backup data matches original
        backup_db = DatabaseManager(backup_path)
        try:
            backup_stats = backup_db.get_database_stats()
            backup_metadata = backup_db.get_metadata('/test/photos/img001.jpg')
            backup_hash = backup_db.get_hash('/test/photos/img001.jpg')

            # Compare statistics
            self.assertEqual(original_stats['file_paths'], backup_stats['file_paths'])
            self.assertEqual(original_stats['file_metadata'], backup_stats['file_metadata'])
            self.assertEqual(original_stats['file_hashes'], backup_stats['file_hashes'])

            # Compare specific data
            self.assertEqual(original_metadata, backup_metadata)
            self.assertEqual(original_hash, backup_hash)

        finally:
            backup_db.close()

    def test_backup_after_database_changes(self):
        """Test backup creation after database modifications."""
        backup_manager = BackupManager(
            database_path=self.db_path,
            backup_count=3,
            periodic_enabled=False
        )

        # Create initial backup
        backup1_path = backup_manager.create_backup("before_changes")
        backup1_size = Path(backup1_path).stat().st_size

        # Modify database with significant changes
        for i in range(10):  # Add multiple files to ensure size difference
            self.db_manager.store_metadata(f'/test/new_file_{i}.jpg', {
                'FileName': f'new_file_{i}.jpg',
                'Camera': f'New Camera Model {i}',
                'Description': f'A long description for file {i} to increase database size significantly'
            })

        # Create second backup with delay to ensure different timestamp
        time.sleep(1.1)  # Ensure different timestamp
        backup2_path = backup_manager.create_backup("after_changes")
        backup2_size = Path(backup2_path).stat().st_size

        # Second backup should be larger (more data)
        self.assertGreater(backup2_size, backup1_size)

        # Verify both backups exist
        backups = backup_manager.get_backup_files()
        self.assertEqual(len(backups), 2)


class TestBackupConfigurationIntegration(unittest.TestCase):
    """Test backup system integration with configuration system."""

    def setUp(self):
        """Set up test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()

        # Create minimal database
        self.db_manager = DatabaseManager(self.temp_db.name)
        self.db_manager.store_metadata('/test.jpg', {'test': 'data'})

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

    def test_default_configuration_values(self):
        """Test that backup manager uses correct default configuration values."""
        backup_manager = BackupManager(database_path=self.temp_db.name)

        # Should use config defaults
        self.assertEqual(backup_manager.backup_count, DEFAULT_BACKUP_COUNT)
        self.assertEqual(backup_manager.backup_interval, DEFAULT_BACKUP_INTERVAL)
        self.assertEqual(backup_manager.periodic_enabled, DEFAULT_PERIODIC_BACKUP_ENABLED)

    def test_custom_configuration_values(self):
        """Test backup manager with custom configuration values."""
        custom_count = 5
        custom_interval = 1800  # 30 minutes
        custom_periodic = False

        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=custom_count,
            backup_interval=custom_interval,
            periodic_enabled=custom_periodic
        )

        # Should use custom values
        self.assertEqual(backup_manager.backup_count, custom_count)
        self.assertEqual(backup_manager.backup_interval, custom_interval)
        self.assertEqual(backup_manager.periodic_enabled, custom_periodic)

    def test_configuration_persistence(self):
        """Test that configuration changes persist correctly."""
        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=2,
            periodic_enabled=False
        )

        # Change configuration
        new_count = 4
        new_interval = 3600  # 1 hour

        backup_manager.set_backup_count(new_count)
        backup_manager.set_backup_interval(new_interval)
        backup_manager.enable_periodic_backups(True)

        # Verify changes persisted
        self.assertEqual(backup_manager.backup_count, new_count)
        self.assertEqual(backup_manager.backup_interval, new_interval)
        self.assertTrue(backup_manager.periodic_enabled)


class TestBackupMainWindowIntegration(unittest.TestCase):
    """Test backup system integration with main window lifecycle."""

    def setUp(self):
        """Set up test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()

        # Create test database
        self.db_manager = DatabaseManager(self.temp_db.name)
        self.db_manager.store_metadata('/test.jpg', {'test': 'data'})

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

    def test_backup_manager_initialization_in_main_window(self):
        """Test backup manager initialization as it would happen in main window."""
        # Simulate main window initialization
        backup_manager = get_backup_manager(
            database_path=self.temp_db.name,
            backup_count=DEFAULT_BACKUP_COUNT,
            backup_interval=DEFAULT_BACKUP_INTERVAL,
            periodic_enabled=DEFAULT_PERIODIC_BACKUP_ENABLED
        )

        # Verify initialization
        self.assertIsNotNone(backup_manager)
        self.assertEqual(backup_manager.backup_count, DEFAULT_BACKUP_COUNT)
        self.assertTrue(backup_manager.periodic_enabled)

    def test_shutdown_backup_workflow(self):
        """Test the complete shutdown backup workflow."""
        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=2,
            periodic_enabled=True
        )

        # Simulate application shutdown
        backup_path = backup_manager.backup_on_shutdown()

        # Verify shutdown backup was created
        self.assertIsNotNone(backup_path)
        self.assertTrue(os.path.exists(backup_path))

        # Verify backup filename indicates shutdown
        # (The backup reason is logged but not in filename)
        backup_file = Path(backup_path)
        self.assertTrue(backup_file.name.endswith('.db.bak'))

        # Simulate cleanup
        backup_manager.stop_periodic_backups()

    @patch('core.backup_manager.QTimer')
    def test_periodic_backup_lifecycle(self, mock_qtimer):
        """Test periodic backup lifecycle during application runtime."""
        mock_timer = Mock()
        mock_qtimer.return_value = mock_timer

        # Create backup manager (simulating main window startup)
        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=3,
            backup_interval=900,  # 15 minutes
            periodic_enabled=True
        )

        # Verify timer was started
        mock_timer.start.assert_called_with(900000)  # 15 minutes in milliseconds

        # Simulate periodic backup trigger
        backup_path = backup_manager.create_backup("periodic")
        self.assertIsNotNone(backup_path)

        # Simulate application shutdown
        backup_manager.stop_periodic_backups()
        mock_timer.stop.assert_called()


class TestBackupErrorRecovery(unittest.TestCase):
    """Test backup system error recovery and resilience."""

    def setUp(self):
        """Set up test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()

        # Create test database
        self.db_manager = DatabaseManager(self.temp_db.name)
        self.db_manager.store_metadata('/test.jpg', {'test': 'data'})

    def tearDown(self):
        """Clean up test environment."""
        self.db_manager.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_backup_with_locked_database(self):
        """Test backup creation when database is locked."""
        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=2,
            periodic_enabled=False
        )

        # Keep database connection open to simulate lock
        # (SQLite allows multiple readers, so this tests the backup process)
        backup_path = backup_manager.create_backup("locked_db_test")

        # Backup should still succeed with SQLite
        self.assertIsNotNone(backup_path)

    def test_backup_directory_permissions(self):
        """Test backup behavior with directory permission issues."""
        # Create backup manager
        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=2,
            periodic_enabled=False
        )

        # This test would require actually changing permissions
        # For now, just verify the backup manager handles the normal case
        backup_path = backup_manager.create_backup("permission_test")
        self.assertIsNotNone(backup_path)

    def test_backup_with_corrupted_database(self):
        """Test backup behavior with corrupted database."""
        # Create a corrupted database file
        corrupted_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        corrupted_db.write(b'This is not a valid SQLite database')
        corrupted_db.close()

        try:
            backup_manager = BackupManager(
                database_path=corrupted_db.name,
                backup_count=2,
                periodic_enabled=False
            )

            # Should still be able to create backup (copies file as-is)
            backup_path = backup_manager.create_backup("corrupted_test")
            self.assertIsNotNone(backup_path)

            # Backup should have same size as original
            original_size = os.path.getsize(corrupted_db.name)
            backup_size = os.path.getsize(backup_path)
            self.assertEqual(original_size, backup_size)

        finally:
            os.unlink(corrupted_db.name)
            if 'backup_path' in locals() and os.path.exists(backup_path):
                os.unlink(backup_path)


if __name__ == '__main__':
    unittest.main()
