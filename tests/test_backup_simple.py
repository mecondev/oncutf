"""
Module: test_backup_simple.py

Author: Michael Economou
Date: 2025-05-31

Simple backup manager tests for development verification.
Tests basic functionality without complex mocking or timing dependencies.
"""

import warnings

warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*coroutine.*never awaited')
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)

import tempfile
from pathlib import Path

from core.backup_manager import BackupManager


class TestBackupSimple:
    """Simple backup tests for core functionality verification."""

    def test_backup_manager_initialization(self):
        """Test that BackupManager initializes with default settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db_path.touch()

            backup_manager = BackupManager(str(db_path))

            assert backup_manager.database_path == Path(db_path)
            assert backup_manager.backup_count == 2  # Default from config
            assert backup_manager.backup_interval == 900  # Default from config

    def test_create_backup_basic(self):
        """Test basic backup creation without database dependencies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "source.db"

            # Create source file with some content
            db_path.write_text("test database content")

            backup_manager = BackupManager(str(db_path))

            # Create backup
            backup_path_str = backup_manager.create_backup()

            # Verify backup was created
            assert backup_path_str is not None
            backup_path = Path(backup_path_str)
            assert backup_path.exists()
            assert backup_path.suffix == ".bak"
            assert "source_" in backup_path.name

            # Verify content matches
            assert backup_path.read_text() == "test database content"

    def test_backup_filename_format(self):
        """Test that backup filenames follow the correct format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_data.db"
            db_path.write_text("test content")

            backup_manager = BackupManager(str(db_path))

            # Create a backup and check the filename format
            backup_path_str = backup_manager.create_backup()

            assert backup_path_str is not None
            backup_path = Path(backup_path_str)

            # Check filename format: test_data_YYYYMMDD_HHMMSS.db.bak
            assert backup_path.name.startswith("test_data_")
            assert backup_path.suffix == ".bak"
            assert backup_path.parent == db_path.parent

    def test_configuration_integration(self):
        """Test that backup manager respects configuration values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "config_test.db"
            db_path.touch()

            # Test custom configuration
            custom_count = 5
            custom_interval = 1800  # 30 minutes

            backup_manager = BackupManager(
                str(db_path),
                backup_count=custom_count,
                backup_interval=custom_interval
            )

            assert backup_manager.backup_count == custom_count
            assert backup_manager.backup_interval == custom_interval
