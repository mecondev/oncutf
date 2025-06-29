"""
test_backup_simple.py

Author: Michael Economou
Date: 2025-01-01

Simplified tests for the backup manager system focusing on core functionality.
"""

import os
import tempfile
import unittest
import time
from pathlib import Path

from core.backup_manager import BackupManager, get_backup_manager, cleanup_backup_manager
from core.database_manager import DatabaseManagerV2 as DatabaseManager, initialize_database


class TestBackupSimple(unittest.TestCase):
    """Simple test cases for BackupManager core functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()

        # Create test database with some data
        self.db_manager = DatabaseManager(self.temp_db.name)
        self.db_manager.store_metadata('/test/file1.jpg', {'test': 'data1'})
        self.db_manager.store_hash('/test/file2.jpg', 'hash123')

    def tearDown(self):
        """Clean up test environment."""
        self.db_manager.close()

        # Remove test database
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

        # Clean up backup files
        backup_dir = Path(self.temp_db.name).parent
        for backup_file in backup_dir.glob("*.db.bak"):
            try:
                backup_file.unlink()
            except OSError:
                pass

    def test_basic_backup_creation(self):
        """Test basic backup creation functionality."""
        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=2,
            periodic_enabled=False
        )

        # Create backup
        backup_path = backup_manager.create_backup("test_basic")

        # Verify backup was created
        self.assertIsNotNone(backup_path)
        self.assertTrue(os.path.exists(backup_path))

        # Verify backup has correct extension
        self.assertTrue(backup_path.endswith('.db.bak'))

        # Verify backup has content
        backup_size = os.path.getsize(backup_path)
        self.assertGreater(backup_size, 0)

    def test_backup_file_naming(self):
        """Test backup file naming convention."""
        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=2,
            periodic_enabled=False
        )

        backup_path = backup_manager.create_backup("naming_test")
        backup_file = Path(backup_path)

        # Check filename format
        db_basename = Path(self.temp_db.name).stem
        self.assertTrue(backup_file.name.startswith(db_basename))
        self.assertTrue(backup_file.name.endswith('.db.bak'))

        # Check timestamp format (should be YYYYMMDD_HHMMSS)
        name_parts = backup_file.name.split('_')
        self.assertGreaterEqual(len(name_parts), 3)  # basename_YYYYMMDD_HHMMSS.db.bak

    def test_backup_count_limit(self):
        """Test that backup count limit is respected."""
        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=2,
            periodic_enabled=False
        )

        # Create 4 backups (more than limit of 2)
        for i in range(4):
            time.sleep(1.1)  # Ensure different timestamps
            backup_manager.create_backup(f"count_test_{i}")

        # Should only have 2 backups
        backups = backup_manager.get_backup_files()
        self.assertEqual(len(backups), 2)

    def test_backup_manager_status(self):
        """Test backup manager status reporting."""
        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=3,
            backup_interval=600,
            periodic_enabled=False
        )

        status = backup_manager.get_status()

        # Check required status fields
        self.assertIn('database_path', status)
        self.assertIn('backup_count', status)
        self.assertIn('backup_interval', status)
        self.assertIn('periodic_enabled', status)

        # Check status values
        self.assertEqual(status['backup_count'], 3)
        self.assertEqual(status['backup_interval'], 600)
        self.assertFalse(status['periodic_enabled'])

    def test_global_backup_manager(self):
        """Test global backup manager singleton."""
        # Clean up any existing instance
        cleanup_backup_manager()

        # Get first instance
        manager1 = get_backup_manager(self.temp_db.name, backup_count=2)

        # Get second instance
        manager2 = get_backup_manager(self.temp_db.name)

        # Should be the same instance
        self.assertIs(manager1, manager2)

        # Should have the configuration from first call
        self.assertEqual(manager1.backup_count, 2)

    def test_backup_with_database_integration(self):
        """Test backup creation with actual database integration."""
        # Use initialize_database for proper setup
        db_manager = initialize_database(self.temp_db.name)

        # Add some realistic data
        db_manager.store_metadata('/photos/vacation1.jpg', {
            'FileName': 'vacation1.jpg',
            'Camera': 'Canon EOS',
            'DateTimeOriginal': '2025:01:01 12:00:00'
        })

        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=2,
            periodic_enabled=False
        )

        # Create backup
        backup_path = backup_manager.create_backup("integration_test")
        self.assertIsNotNone(backup_path)

        # Verify backup can be opened as database
        backup_db = DatabaseManager(backup_path)
        try:
            # Should be able to get stats from backup
            stats = backup_db.get_database_stats()
            self.assertIsInstance(stats, dict)
            self.assertGreater(len(stats), 0)
        finally:
            backup_db.close()

        db_manager.close()

    def test_backup_configuration_changes(self):
        """Test backup configuration changes."""
        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=3,
            backup_interval=900,
            periodic_enabled=False
        )

        # Change backup count
        backup_manager.set_backup_count(5)
        self.assertEqual(backup_manager.backup_count, 5)

        # Change backup interval
        backup_manager.set_backup_interval(1800)
        self.assertEqual(backup_manager.backup_interval, 1800)

        # Enable periodic backups
        backup_manager.enable_periodic_backups(True)
        self.assertTrue(backup_manager.periodic_enabled)

    def test_shutdown_backup(self):
        """Test shutdown backup functionality."""
        backup_manager = BackupManager(
            database_path=self.temp_db.name,
            backup_count=2,
            periodic_enabled=False
        )

        # Create shutdown backup
        backup_path = backup_manager.backup_on_shutdown()

        # Verify backup was created
        self.assertIsNotNone(backup_path)
        self.assertTrue(os.path.exists(backup_path))

        # Verify it's a valid backup file
        backup_size = os.path.getsize(backup_path)
        self.assertGreater(backup_size, 0)


if __name__ == '__main__':
    unittest.main()
