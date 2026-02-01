"""Module: backup_manager.py.

Author: Michael Economou
Date: 2025-06-10

This module provides database backup functionality for the oncutf application.
It handles automatic backups on application shutdown, periodic backups during
runtime, and backup file rotation to maintain disk space.
Features:
- Automatic backup on application shutdown
- Periodic backups with configurable interval
- Backup file rotation (keeps N most recent backups)
- Configurable backup count
- Thread-safe backup operations
"""

import shutil
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from oncutf.config import (
    BACKUP_FILENAME_FORMAT,
    BACKUP_TIMESTAMP_FORMAT,
    DEFAULT_BACKUP_COUNT,
    DEFAULT_BACKUP_INTERVAL,
    DEFAULT_PERIODIC_BACKUP_ENABLED,
)
from oncutf.utils.logging.logger_helper import get_logger

logger = get_logger(__name__)


class BackupManager(QObject):
    """Manages database backup operations including periodic backups and cleanup.

    This class handles:
    - Creating backups of the database file
    - Rotating old backup files
    - Periodic backup scheduling
    - Backup on application shutdown
    """

    # Signals
    backup_completed = pyqtSignal(str)  # Emitted when backup is completed (filepath)
    backup_failed = pyqtSignal(str)  # Emitted when backup fails (error message)

    def __init__(
        self,
        database_path: str,
        backup_count: int = DEFAULT_BACKUP_COUNT,
        backup_interval: int = DEFAULT_BACKUP_INTERVAL,
        periodic_enabled: bool = DEFAULT_PERIODIC_BACKUP_ENABLED,
        grouping_timeout: float = 10.0,
    ):
        """Initialize the backup manager.

        Args:
            database_path: Path to the database file to backup
            backup_count: Number of backup files to keep (default from config)
            backup_interval: Interval between periodic backups in seconds
            periodic_enabled: Whether periodic backups are enabled
            grouping_timeout: Time window (seconds) used for grouping operations

        """
        super().__init__()

        self.database_path = Path(database_path)
        self.grouping_timeout = float(grouping_timeout)
        self.backup_count = backup_count
        self.backup_interval = backup_interval
        self.periodic_enabled = periodic_enabled

        # Setup periodic backup timer
        self.backup_timer = QTimer()
        self.backup_timer.timeout.connect(self._perform_periodic_backup)

        # Start periodic backups if enabled
        if self.periodic_enabled and self.backup_interval > 0:
            self.start_periodic_backups()

        logger.info("[BackupManager] Initialized for %s", self.database_path)
        logger.info(
            "[BackupManager] Backup count: %d, Interval: %ds, Periodic: %s",
            self.backup_count,
            self.backup_interval,
            self.periodic_enabled,
        )

    def create_backup(self, reason: str = "manual") -> str | None:
        """Create a backup of the database file.

        Args:
            reason: Reason for the backup (for logging)

        Returns:
            Path to the created backup file, or None if backup failed

        """
        try:
            # Check if database file exists
            if not self.database_path.exists():
                logger.warning("[BackupManager] Database file not found: %s", self.database_path)
                return None

            # Generate backup filename
            timestamp = datetime.now().strftime(BACKUP_TIMESTAMP_FORMAT)
            basename = self.database_path.stem
            backup_filename = BACKUP_FILENAME_FORMAT.format(basename=basename, timestamp=timestamp)
            backup_path = self.database_path.parent / backup_filename

            # Create the backup
            shutil.copy2(self.database_path, backup_path)

            logger.info("[BackupManager] Database backup created (%s): %s", reason, backup_path)

            # Clean up old backups
            self._cleanup_old_backups()

            # Emit success signal
            self.backup_completed.emit(str(backup_path))

            return str(backup_path)

        except Exception as e:
            error_msg = f"[BackupManager] Failed to create backup: {e!s}"
            logger.exception(error_msg)
            self.backup_failed.emit(error_msg)
            return None

    def _cleanup_old_backups(self) -> None:
        """Remove old backup files, keeping only the most recent ones."""
        try:
            # Find all backup files for this database
            basename = self.database_path.stem
            backup_pattern = f"{basename}_*.db.bak"
            backup_dir = self.database_path.parent
            backup_files = list(backup_dir.glob(backup_pattern))

            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # Remove excess backups
            if len(backup_files) > self.backup_count:
                files_to_remove = backup_files[self.backup_count :]
                for old_backup in files_to_remove:
                    try:
                        old_backup.unlink()
                        logger.info("[BackupManager] Removed old backup: %s", old_backup)
                    except Exception:
                        logger.exception(
                            "[BackupManager] Failed to remove old backup %s",
                            old_backup,
                        )

        except Exception:
            logger.exception("[BackupManager] Error during backup cleanup")

    def start_periodic_backups(self) -> None:
        """Start the periodic backup timer."""
        if self.backup_interval > 0:
            self.backup_timer.start(self.backup_interval * 1000)  # Convert to milliseconds
            logger.info(
                "[BackupManager] Periodic backups started (every %d seconds)",
                self.backup_interval,
            )

    def stop_periodic_backups(self) -> None:
        """Stop the periodic backup timer."""
        self.backup_timer.stop()
        logger.info("[BackupManager] Periodic backups stopped")

    def _perform_periodic_backup(self) -> None:
        """Perform a periodic backup (called by timer)."""
        self.create_backup("periodic")

    def backup_on_shutdown(self) -> str | None:
        """Create a backup when the application is shutting down.

        Returns:
            Path to the created backup file, or None if backup failed

        """
        logger.info("[BackupManager] Creating shutdown backup...")
        return self.create_backup("shutdown")

    def set_backup_count(self, count: int) -> None:
        """Update the number of backup files to keep.

        Args:
            count: New backup count

        """
        if count < 1:
            logger.warning("[BackupManager] Invalid backup count: %d. Must be >= 1", count)
            return

        old_count = self.backup_count
        self.backup_count = count
        logger.info("[BackupManager] Backup count changed from %d to %d", old_count, count)

        # Clean up immediately if we reduced the count
        if count < old_count:
            self._cleanup_old_backups()

    def set_backup_interval(self, interval: int) -> None:
        """Update the periodic backup interval.

        Args:
            interval: New interval in seconds

        """
        if interval < 0:
            logger.warning("[BackupManager] Invalid backup interval: %d. Must be >= 0", interval)
            return

        old_interval = self.backup_interval
        self.backup_interval = interval
        logger.info(
            "[BackupManager] Backup interval changed from %ds to %ds",
            old_interval,
            interval,
        )

        # Restart timer with new interval
        if self.periodic_enabled:
            self.stop_periodic_backups()
            if interval > 0:
                self.start_periodic_backups()

    def enable_periodic_backups(self, enabled: bool) -> None:
        """Enable or disable periodic backups.

        Args:
            enabled: Whether to enable periodic backups

        """
        self.periodic_enabled = enabled

        if enabled:
            self.start_periodic_backups()
            logger.info("[BackupManager] Periodic backups enabled")
        else:
            self.stop_periodic_backups()
            logger.info("[BackupManager] Periodic backups disabled")

    def get_backup_files(self) -> list[Path]:
        """Get a list of all backup files for this database.

        Returns:
            List of backup file paths, sorted by modification time (newest first)

        """
        try:
            basename = self.database_path.stem
            backup_pattern = f"{basename}_*.db.bak"
            backup_dir = self.database_path.parent
            backup_files = list(backup_dir.glob(backup_pattern))

            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        except Exception:
            logger.exception("[BackupManager] Error getting backup files")
            return []
        else:
            return backup_files

    def get_status(self) -> dict[str, object]:
        """Get current backup manager status.

        Returns:
            Dictionary with status information

        """
        backup_files = self.get_backup_files()

        return {
            "database_path": str(self.database_path),
            "backup_count": self.backup_count,
            "backup_interval": self.backup_interval,
            "periodic_enabled": self.periodic_enabled,
            "timer_active": self.backup_timer.isActive(),
            "existing_backups": len(backup_files),
            "latest_backup": str(backup_files[0]) if backup_files else None,
        }


# Global backup manager instance
_backup_manager: BackupManager | None = None


def get_backup_manager(
    database_path: str,
    *,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    backup_interval: int = DEFAULT_BACKUP_INTERVAL,
    periodic_enabled: bool = DEFAULT_PERIODIC_BACKUP_ENABLED,
    grouping_timeout: float = 10.0,
) -> BackupManager:
    """Get or create the global backup manager instance.

    Args:
        database_path: Path to the database file
        backup_count: Number of backup files to keep
        backup_interval: Interval between periodic backups in seconds
        periodic_enabled: Whether periodic backups are enabled
        grouping_timeout: Time window for grouping operations

    Returns:
        BackupManager: The global backup manager instance

    Returns:
        The global BackupManager instance

    """
    global _backup_manager

    if _backup_manager is None:
        _backup_manager = BackupManager(
            database_path,
            backup_count=backup_count,
            backup_interval=backup_interval,
            periodic_enabled=periodic_enabled,
            grouping_timeout=grouping_timeout,
        )
        logger.info("[BackupManager] Global instance created")

    return _backup_manager


def cleanup_backup_manager() -> None:
    """Clean up the global backup manager instance."""
    global _backup_manager

    if _backup_manager is not None:
        _backup_manager.stop_periodic_backups()
        _backup_manager = None
        logger.info("[BackupManager] Global instance cleaned up")
