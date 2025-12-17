"""
Module: filesystem_monitor.py

Author: Michael Economou
Date: 2025-12-16

Comprehensive filesystem monitoring for drive and directory changes.
"""

from __future__ import annotations

import logging
import os
import platform
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from oncutf.core.pyqt_imports import QFileSystemWatcher, QObject, QTimer, pyqtSignal

if TYPE_CHECKING:
    from oncutf.core.file_store import FileStore

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

    def __init__(self, file_store: FileStore | None = None) -> None:
        """Initialize filesystem monitor.

        Args:
            file_store: FileStore instance for auto-refresh
        """
        super().__init__()
        self.file_store = file_store
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

        # Timer for debouncing change events
        self._change_debounce_timer = QTimer()
        self._change_debounce_timer.setSingleShot(True)
        self._change_debounce_timer.setInterval(500)  # 500ms debounce
        self._change_debounce_timer.timeout.connect(self._process_pending_changes)
        self._pending_changes: set[str] = set()

        # Track loaded folders
        self._monitored_folders: set[str] = set()

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
            ", ".join(sorted(self._current_drives))
        )

        # Start drive polling
        self._drive_poll_timer.start()
        logger.info("[FilesystemMonitor] Started monitoring (polling every 2s)")

    def stop(self) -> None:
        """Stop monitoring filesystem."""
        self._drive_poll_timer.stop()
        self._change_debounce_timer.stop()
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
                extra={"dev_only": True}
            )
            return True

        except Exception as e:
            logger.error("[FilesystemMonitor] Failed to watch %s: %s", normalized_path, e)
            return False

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
                extra={"dev_only": True}
            )
            return True

        except Exception as e:
            logger.error("[FilesystemMonitor] Failed to unwatch %s: %s", normalized_path, e)
            return False

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
                if os.path.exists(drive_path):
                    drives.add(drive_path)

        elif self._system == "Darwin":
            # macOS: Check /Volumes
            volumes_path = Path("/Volumes")
            if volumes_path.exists():
                for volume in volumes_path.iterdir():
                    if volume.is_dir():
                        drives.add(str(volume))

        else:
            # Linux: Check /media and /mnt
            for mount_root in ["/media", "/mnt"]:
                mount_path = Path(mount_root)
                if mount_path.exists():
                    # Get user-specific mounts (e.g., /media/username/...)
                    try:
                        for user_mount in mount_path.iterdir():
                            if user_mount.is_dir():
                                # Check subdirectories (actual mount points)
                                try:
                                    for mount in user_mount.iterdir():
                                        if mount.is_dir():
                                            drives.add(str(mount))
                                except PermissionError:
                                    pass
                    except PermissionError:
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
            to_remove = [
                folder for folder in self._monitored_folders
                if folder.startswith(drive)
            ]
            for folder in to_remove:
                self.remove_folder(folder)

            # Auto-remove files from FileStore if available
            if self.file_store:
                try:
                    removed_count = self.file_store.remove_files_from_path(drive)
                    if removed_count > 0:
                        logger.info(
                            "[FilesystemMonitor] Removed %d files from unmounted drive: %s",
                            removed_count,
                            drive
                        )
                except Exception as e:
                    logger.exception("[FilesystemMonitor] Error removing files from unmounted drive: %s", e)

        # Update state
        if added or removed:
            self._current_drives = current_drives

            # Trigger callback
            if self._on_drive_change_callback:
                try:
                    self._on_drive_change_callback(sorted(current_drives))
                except Exception as e:
                    logger.error("[FilesystemMonitor] Drive callback error: %s", e)

    def _on_directory_changed(self, path: str) -> None:
        """Handle directory changed signal (debounced).

        Args:
            path: Changed directory path
        """
        logger.debug(
            "[FilesystemMonitor] Directory changed: %s",
            path,
            extra={"dev_only": True}
        )

        # Add to pending changes
        self._pending_changes.add(path)

        # Restart debounce timer
        self._change_debounce_timer.stop()
        self._change_debounce_timer.start()

    def _on_file_changed(self, path: str) -> None:
        """Handle file changed signal.

        Args:
            path: Changed file path
        """
        logger.debug(
            "[FilesystemMonitor] File changed: %s",
            path,
            extra={"dev_only": True}
        )
        self.file_changed.emit(path)

    def _process_pending_changes(self) -> None:
        """Process pending directory changes after debounce."""
        for path in self._pending_changes:
            logger.info("[FilesystemMonitor] Processing directory change: %s", path)
            self.directory_changed.emit(path)

            # Trigger custom callback
            if self._on_folder_change_callback:
                try:
                    self._on_folder_change_callback(path)
                except Exception as e:
                    logger.error("[FilesystemMonitor] Folder callback error: %s", e)

            # Auto-refresh FileStore if available
            if self.file_store:
                try:
                    self._refresh_filestore_for_path(path)
                except Exception as e:
                    logger.error("[FilesystemMonitor] FileStore refresh error: %s", e)

        self._pending_changes.clear()

    def _refresh_filestore_for_path(self, changed_path: str) -> None:
        """Refresh FileStore for changed path.

        Args:
            changed_path: Path that changed
        """
        if not self.file_store:
            return

        # Get loaded files
        loaded_files = self.file_store.get_all_files()
        if not loaded_files:
            return

        # Check if any loaded file is in the changed directory
        changed_path_obj = Path(changed_path)
        has_files_in_folder = any(
            Path(file_item.full_path).parent == changed_path_obj
            for file_item in loaded_files
        )

        if has_files_in_folder:
            logger.info(
                "[FilesystemMonitor] Refreshing FileStore for changed folder: %s",
                changed_path
            )
            # Refresh files from affected folder
            self.file_store.refresh_loaded_folders(changed_path)

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
