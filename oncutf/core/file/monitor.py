"""Module: filesystem_monitor.py.

Author: Michael Economou
Date: 2025-12-16

Filesystem monitoring for drive and directory changes.

Features:
- Drive mount/unmount detection (polling-based)
- Directory content change detection (QFileSystemWatcher)
- Automatic refresh via FileLoadManager when changes detected
"""

from __future__ import annotations

import logging
import os
import platform
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt5.QtCore import QFileSystemWatcher, QObject, QTimer, pyqtSignal

from oncutf.utils.shared.timer_manager import TimerType, get_timer_manager

if TYPE_CHECKING:
    from collections.abc import Callable

    from oncutf.app.state.file_store import FileStore
    from oncutf.core.file.load_manager import FileLoadManager

logger = logging.getLogger(__name__)


class FilesystemMonitor(QObject):
    """Monitor filesystem for drive and directory changes.

    Features:
    - Drive mount/unmount detection (polling-based)
    - Directory content change detection (QFileSystemWatcher)
    - Loaded folder tracking and monitoring
    - Automatic FileStore refresh on changes
    """

    # Signals
    drive_added = pyqtSignal(str)  # New drive mounted
    drive_removed = pyqtSignal(str)  # Drive unmounted
    directory_changed = pyqtSignal(str)  # Directory content changed
    file_changed = pyqtSignal(str)  # File modified

    def __init__(
        self,
        file_store: FileStore | None = None,
        file_load_manager: FileLoadManager | None = None,
    ) -> None:
        """Initialize filesystem monitor.

        Args:
            file_store: FileStore instance for state access
            file_load_manager: FileLoadManager instance for I/O operations

        """
        super().__init__()
        self.file_store = file_store
        self.file_load_manager = file_load_manager
        self._system = platform.system()

        # QFileSystemWatcher for directory/file changes
        self._watcher = QFileSystemWatcher()
        self._watcher.directoryChanged.connect(self._on_directory_changed)
        self._watcher.fileChanged.connect(self._on_file_changed)

        # Timer for drive polling (detect mount/unmount)
        self._drive_poll_timer = QTimer()
        self._drive_poll_timer.setInterval(2000)  # Poll every 2 seconds
        self._drive_poll_timer.timeout.connect(self._poll_drives)
        self._current_drives: set[str] = set()

        # Debounce timer ID for change events (uses TimerManager)
        self._debounce_timer_id: str | None = None
        self._pending_changes: set[str] = set()

        # Track loaded folders
        self._monitored_folders: set[str] = set()

        # Pause flag for temporarily disabling auto-refresh (e.g., during metadata save)
        self._paused = False

        # Callbacks for custom actions
        self._on_drive_change_callback: Callable[[list[str]], None] | None = None
        self._on_folder_change_callback: Callable[[str], None] | None = None

        logger.debug("[FilesystemMonitor] Initialized", extra={"dev_only": True})

    def start(self) -> None:
        """Start monitoring filesystem."""
        # Initialize current drives
        self._current_drives = self._get_available_drives()
        logger.info(
            "[FilesystemMonitor] Initial drives: %s",
            ", ".join(sorted(self._current_drives)),
        )

        # Start drive polling
        self._drive_poll_timer.start()
        logger.info("[FilesystemMonitor] Started monitoring (polling every 2s)")

    def stop(self) -> None:
        """Stop monitoring filesystem."""
        self._drive_poll_timer.stop()
        # Cancel debounce timer if active
        if self._debounce_timer_id:
            get_timer_manager().cancel(self._debounce_timer_id)
            self._debounce_timer_id = None
        self._watcher.blockSignals(True)
        logger.info("[FilesystemMonitor] Stopped monitoring")

    def add_folder(self, folder_path: str) -> bool:
        """Add folder to monitoring.

        Args:
            folder_path: Absolute path to folder

        Returns:
            bool: True if added successfully

        """
        path = Path(folder_path)
        if not path.exists() or not path.is_dir():
            logger.warning("[FilesystemMonitor] Cannot watch non-existent folder: %s", folder_path)
            return False

        normalized_path = str(path.resolve())
        if normalized_path in self._monitored_folders:
            return True  # Already monitoring

        try:
            self._watcher.addPath(normalized_path)
            self._monitored_folders.add(normalized_path)
            logger.debug(
                "[FilesystemMonitor] Now watching: %s",
                normalized_path,
                extra={"dev_only": True},
            )
        except Exception as e:
            logger.exception("[FilesystemMonitor] Failed to watch %s", normalized_path)
            return False
        else:
            return True

    def remove_folder(self, folder_path: str) -> bool:
        """Remove folder from monitoring.

        Args:
            folder_path: Absolute path to folder

        Returns:
            bool: True if removed successfully

        """
        normalized_path = str(Path(folder_path).resolve())
        if normalized_path not in self._monitored_folders:
            return True  # Not monitoring anyway

        try:
            self._watcher.removePath(normalized_path)
            self._monitored_folders.discard(normalized_path)
            logger.debug(
                "[FilesystemMonitor] Stopped watching: %s",
                normalized_path,
                extra={"dev_only": True},
            )
        except Exception as e:
            logger.exception("[FilesystemMonitor] Failed to unwatch %s", normalized_path)
            return False
        else:
            return True

    def clear_folders(self) -> None:
        """Clear all monitored folders."""
        for folder in list(self._monitored_folders):
            self.remove_folder(folder)

    def set_drive_change_callback(self, callback: Callable[[list[str]], None]) -> None:
        """Set callback for drive changes.

        Args:
            callback: Function called with list of current drives

        """
        self._on_drive_change_callback = callback

    def set_folder_change_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for folder changes.

        Args:
            callback: Function called with changed folder path

        """
        self._on_folder_change_callback = callback

    def pause(self) -> None:
        """Pause auto-refresh (e.g., during metadata save)."""
        self._paused = True
        # Cancel any pending debounce timer
        if self._debounce_timer_id:
            get_timer_manager().cancel(self._debounce_timer_id)
            self._debounce_timer_id = None
        self._pending_changes.clear()
        logger.debug("[FilesystemMonitor] Paused", extra={"dev_only": True})

    def resume(self) -> None:
        """Resume auto-refresh after pause."""
        self._paused = False
        # Clear any pending changes that accumulated during pause
        self._pending_changes.clear()
        # Also cancel any debounce timer that might have been scheduled
        if self._debounce_timer_id:
            get_timer_manager().cancel(self._debounce_timer_id)
            self._debounce_timer_id = None
        logger.debug("[FilesystemMonitor] Resumed", extra={"dev_only": True})

    def is_paused(self) -> bool:
        """Check if monitoring is paused."""
        return self._paused

    def _get_available_drives(self) -> set[str]:
        """Get currently available drives.

        Returns:
            set: Set of drive paths

        """
        drives: set[str] = set()

        if self._system == "Windows":
            # Windows: Check A-Z drives
            import string

            for letter in string.ascii_uppercase:
                drive_path = f"{letter}:\\"
                if Path(drive_path).exists():
                    drives.add(drive_path)

        elif self._system == "Darwin":
            # macOS: mount points in /Volumes
            volumes_path = Path("/Volumes")
            if volumes_path.exists():
                for volume in volumes_path.iterdir():
                    if volume.is_dir():
                        drives.add(str(volume))

        else:
            # Linux: Check /media and /mnt for mount points
            # For /media, typical structure is /media/username/device
            # For /mnt, can be direct mounts like /mnt/data or /mnt/usb

            # Check /media (Ubuntu/Debian style: /media/username/device)
            media_path = Path("/media")
            if media_path.exists():
                try:
                    for user_dir in media_path.iterdir():
                        if user_dir.is_dir():
                            try:
                                for mount_point in user_dir.iterdir():
                                    if mount_point.is_dir() and mount_point.is_mount():
                                        drives.add(str(mount_point))
                            except (PermissionError, OSError):
                                pass
                except (PermissionError, OSError):
                    pass

            # Check /mnt (can have direct mounts)
            mnt_path = Path("/mnt")
            if mnt_path.exists():
                try:
                    for mount_point in mnt_path.iterdir():
                        if mount_point.is_dir() and mount_point.is_mount():
                            drives.add(str(mount_point))
                except (PermissionError, OSError):
                    pass

        return drives

    def _poll_drives(self) -> None:
        """Poll for drive changes (mount/unmount)."""
        current_drives = self._get_available_drives()

        # Check for added drives
        added = current_drives - self._current_drives
        for drive in added:
            logger.info("[FilesystemMonitor] Drive mounted: %s", drive)
            self.drive_added.emit(drive)

        # Check for removed drives
        removed = self._current_drives - current_drives
        for drive in removed:
            logger.info("[FilesystemMonitor] Drive unmounted: %s", drive)
            self.drive_removed.emit(drive)

            # Remove from monitored folders if it was being watched
            to_remove = [folder for folder in self._monitored_folders if folder.startswith(drive)]
            for folder in to_remove:
                self.remove_folder(folder)

            # Trigger FileStore refresh - files on unmounted drive will be automatically removed
            if self.file_load_manager and self.file_store:
                try:
                    logger.info(
                        "[FilesystemMonitor] Refreshing FileStore after drive unmount: %s",
                        drive,
                    )
                    # Use FileLoadManager to scan filesystem and update FileStore
                    # This will check if files still exist and automatically update the UI
                    if self.file_load_manager.refresh_loaded_folders(
                        changed_folder=None, file_store=self.file_store
                    ):
                        logger.info("[FilesystemMonitor] FileStore refreshed after drive unmount")
                    else:
                        logger.info(
                            "[FilesystemMonitor] FileStore refresh returned False (no files loaded)"
                        )
                except Exception as e:
                    logger.exception(
                        "[FilesystemMonitor] Error refreshing FileStore after unmount",
                    )
            else:
                logger.warning(
                    "[FilesystemMonitor] FileLoadManager or FileStore not available - cannot auto-refresh on unmount"
                )

        # Update state
        if added or removed:
            self._current_drives = current_drives

            # Trigger callback
            if self._on_drive_change_callback:
                try:
                    self._on_drive_change_callback(sorted(current_drives))
                except Exception as e:
                    logger.exception("[FilesystemMonitor] Drive callback error")

    def _on_directory_changed(self, path: str) -> None:
        """Handle directory changed signal (debounced).

        Args:
            path: Changed directory path

        """
        logger.debug("[FilesystemMonitor] Directory changed: %s", path, extra={"dev_only": True})

        # Add to pending changes
        self._pending_changes.add(path)

        # Schedule debounced processing via TimerManager
        # Cancel existing timer and reschedule (debounce behavior)
        timer_manager = get_timer_manager()
        if self._debounce_timer_id:
            timer_manager.cancel(self._debounce_timer_id)
        self._debounce_timer_id = timer_manager.schedule(
            self._process_pending_changes,
            delay=500,
            timer_type=TimerType.GENERIC,
            timer_id="filesystem_monitor_debounce",
            consolidate=False,
        )

    def _on_file_changed(self, path: str) -> None:
        """Handle file changed signal.

        Args:
            path: Changed file path

        """
        logger.debug("[FilesystemMonitor] File changed: %s", path, extra={"dev_only": True})
        self.file_changed.emit(path)

    def _process_pending_changes(self) -> None:
        """Process pending directory changes after debounce."""
        # Skip processing if paused
        if self._paused:
            self._pending_changes.clear()
            return

        for path in self._pending_changes:
            logger.info("[FilesystemMonitor] Processing directory change: %s", path)
            self.directory_changed.emit(path)

            # Trigger custom callback
            if self._on_folder_change_callback:
                try:
                    self._on_folder_change_callback(path)
                except Exception as e:
                    logger.exception("[FilesystemMonitor] Folder callback error")

            # Auto-refresh FileStore if available
            if self.file_store:
                try:
                    self._refresh_filestore_for_path(path)
                except Exception as e:
                    logger.exception("[FilesystemMonitor] FileStore refresh error")

        self._pending_changes.clear()

    def _refresh_filestore_for_path(self, changed_path: str) -> None:
        """Refresh FileStore for changed path.

        Args:
            changed_path: Path that changed

        """
        if not self.file_load_manager or not self.file_store:
            return

        # Get loaded files
        loaded_files = self.file_store.get_loaded_files()
        if not loaded_files:
            return

        # Check if any loaded file is in the changed directory
        changed_path_obj = Path(changed_path)
        has_files_in_folder = any(
            Path(file_item.full_path).parent == changed_path_obj for file_item in loaded_files
        )

        if has_files_in_folder:
            logger.info(
                "[FilesystemMonitor] Refreshing FileStore for changed folder: %s",
                changed_path,
            )
            # Use FileLoadManager to scan filesystem and refresh files from affected folder
            self.file_load_manager.refresh_loaded_folders(
                changed_folder=changed_path, file_store=self.file_store
            )

    def get_monitored_folders(self) -> list[str]:
        """Get list of currently monitored folders.

        Returns:
            list: List of folder paths

        """
        return sorted(self._monitored_folders)

    def get_current_drives(self) -> list[str]:
        """Get list of currently available drives.

        Returns:
            list: List of drive paths

        """
        return sorted(self._current_drives)
