"""Module: filesystem_handler.py

Author: Michael Economou
Date: 2026-01-02

Filesystem monitoring handler for file tree view.

Manages filesystem monitor setup, directory change callbacks,
and drive mount/unmount detection for automatic tree refresh.
"""

from __future__ import annotations

import os
import platform
from typing import TYPE_CHECKING

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.core.file.monitor import FilesystemMonitor
    from oncutf.ui.widgets.file_tree.view import FileTreeView

logger = get_cached_logger(__name__)


class FilesystemHandler:
    """Handles filesystem monitoring for the file tree view.

    Manages setup and teardown of filesystem monitor, handles directory
    change events, and refreshes the tree on drive changes.
    """

    def __init__(self, view: FileTreeView) -> None:
        """Initialize filesystem handler.

        Args:
            view: The file tree view widget to handle monitoring for

        """
        self._view = view
        self._filesystem_monitor: FilesystemMonitor | None = None
        self._last_monitored_path: str | None = None
        self._refresh_in_progress = False

    @property
    def filesystem_monitor(self) -> FilesystemMonitor | None:
        """Get the filesystem monitor instance."""
        return self._filesystem_monitor

    @property
    def last_monitored_path(self) -> str | None:
        """Get the last monitored path."""
        return self._last_monitored_path

    @last_monitored_path.setter
    def last_monitored_path(self, value: str | None) -> None:
        """Set the last monitored path."""
        self._last_monitored_path = value

    def setup_monitor(self) -> None:
        """Setup comprehensive filesystem monitoring."""
        try:
            from oncutf.core.file.monitor import FilesystemMonitor

            # Get FileStore and FileLoadManager from parent window if available
            file_store = None
            file_load_manager = None

            # Try multiple paths to find FileStore and FileLoadManager
            if hasattr(self._view, "parent") and self._view.parent():
                parent = self._view.parent()

                # Try 1: parent.context (MainWindow with context)
                if hasattr(parent, "context"):
                    if hasattr(parent.context, "file_store"):
                        file_store = parent.context.file_store
                        logger.debug(
                            "[FilesystemHandler] Found FileStore from parent.context",
                            extra={"dev_only": True},
                        )
                    if hasattr(parent.context, "file_load_manager"):
                        file_load_manager = parent.context.file_load_manager
                        logger.debug(
                            "[FilesystemHandler] Found FileLoadManager from parent.context",
                            extra={"dev_only": True},
                        )
                    # Also check parent directly (MainWindow stores managers as direct attrs)
                    if not file_load_manager and hasattr(parent, "file_load_manager"):
                        file_load_manager = parent.file_load_manager
                        logger.debug(
                            "[FilesystemHandler] Found FileLoadManager from parent.file_load_manager",
                            extra={"dev_only": True},
                        )
                # Try 2: parent direct attributes
                else:
                    if hasattr(parent, "_file_store"):
                        file_store = parent._file_store
                        logger.debug(
                            "[FilesystemHandler] Found FileStore from parent._file_store",
                            extra={"dev_only": True},
                        )
                    if hasattr(parent, "file_load_manager"):
                        file_load_manager = parent.file_load_manager
                        logger.debug(
                            "[FilesystemHandler] Found FileLoadManager from parent.file_load_manager",
                            extra={"dev_only": True},
                        )

                # Try 3: Walk up parent chain looking for MainWindow
                if not file_store or not file_load_manager:
                    current = parent
                    while current is not None:
                        if hasattr(current, "context"):
                            if not file_store and hasattr(current.context, "file_store"):
                                file_store = current.context.file_store
                                logger.debug(
                                    "[FilesystemHandler] Found FileStore from ancestor context",
                                    extra={"dev_only": True},
                                )
                            if not file_load_manager and hasattr(
                                current.context, "file_load_manager"
                            ):
                                file_load_manager = current.context.file_load_manager
                                logger.debug(
                                    "[FilesystemHandler] Found FileLoadManager from ancestor context",
                                    extra={"dev_only": True},
                                )
                        # Also check direct attribute on ancestor (MainWindow pattern)
                        if not file_load_manager and hasattr(current, "file_load_manager"):
                            file_load_manager = current.file_load_manager
                            logger.debug(
                                "[FilesystemHandler] Found FileLoadManager from ancestor direct attr",
                                extra={"dev_only": True},
                            )
                        if file_store and file_load_manager:
                            break
                        current = current.parent() if hasattr(current, "parent") else None

            if file_store is None:
                logger.warning(
                    "[FilesystemHandler] FileStore not found at init - will retry connection"
                )
            if file_load_manager is None:
                logger.warning(
                    "[FilesystemHandler] FileLoadManager not found at init - will retry connection"
                )

            self._filesystem_monitor = FilesystemMonitor(
                file_store=file_store, file_load_manager=file_load_manager
            )

            # Schedule delayed reconnection if managers not found
            if file_store is None or file_load_manager is None:
                from oncutf.utils.shared.timer_manager import schedule_ui_update
                schedule_ui_update(self._reconnect_managers, 500)  # Try again after 500ms

            # Connect directory change signal for tree model refresh
            self._filesystem_monitor.directory_changed.connect(self._on_directory_changed)

            # Set custom callback for tree refresh (handles drive mount/unmount)
            self._filesystem_monitor.set_drive_change_callback(self._refresh_tree_on_drives_change)

            # Start monitoring
            self._filesystem_monitor.start()

            # Watch the current root path to pick up directory changes
            root_path = ""
            model = self._view.model()
            if model and hasattr(model, "rootPath"):
                try:
                    root_path = model.rootPath()
                except Exception:
                    root_path = ""

            if root_path and os.path.isdir(root_path):
                if self._filesystem_monitor.add_folder(root_path):
                    self._last_monitored_path = root_path

            logger.info("[FilesystemHandler] Filesystem monitor started")

        except Exception as e:
            logger.warning("[FilesystemHandler] Failed to setup filesystem monitor: %s", e)
            self._filesystem_monitor = None

    def _reconnect_managers(self) -> None:
        """Attempt to reconnect FileStore and FileLoadManager after initialization.

        Called via delayed timer to pick up managers that weren't available
        during initial setup (timing issue with MainWindow initialization).
        """
        if not self._filesystem_monitor:
            return

        # Check if already connected
        if self._filesystem_monitor.file_store and self._filesystem_monitor.file_load_manager:
            return

        # Try to find managers by walking up parent chain
        file_store = None
        file_load_manager = None

        current = self._view.parent() if hasattr(self._view, "parent") else None
        while current is not None:
            # Check for file_model (FileStore)
            if not file_store and hasattr(current, "file_model"):
                file_store = current.file_model
                logger.debug(
                    "[FilesystemHandler] Reconnected FileStore from ancestor",
                    extra={"dev_only": True},
                )
            # Check for file_load_manager
            if not file_load_manager and hasattr(current, "file_load_manager"):
                file_load_manager = current.file_load_manager
                logger.debug(
                    "[FilesystemHandler] Reconnected FileLoadManager from ancestor",
                    extra={"dev_only": True},
                )
            if file_store and file_load_manager:
                break
            current = current.parent() if hasattr(current, "parent") else None

        # Update monitor with found managers
        if file_store and not self._filesystem_monitor.file_store:
            self._filesystem_monitor.file_store = file_store
            logger.info("[FilesystemHandler] FileStore reconnected successfully")
        if file_load_manager and not self._filesystem_monitor.file_load_manager:
            self._filesystem_monitor.file_load_manager = file_load_manager
            logger.info("[FilesystemHandler] FileLoadManager reconnected successfully")

    def _on_directory_changed(self, dir_path: str) -> None:
        """Handle directory content changed.

        Args:
            dir_path: Path of changed directory

        """
        # Prevent infinite loop if refresh triggers another directory change event
        if self._refresh_in_progress:
            logger.debug(
                "[FilesystemHandler] Ignoring directory change during refresh: %s",
                dir_path,
                extra={"dev_only": True},
            )
            return

        logger.debug(
            "[FilesystemHandler] Directory changed: %s", dir_path, extra={"dev_only": True}
        )

        # Save state before refresh
        expanded_paths = self._view.state_handler.save_expanded_state()
        selected_path = self._view.get_selected_path()
        scroll_position = self._view.verticalScrollBar().value()

        # Refresh model if it supports refresh
        model = self._view.model()
        if model and hasattr(model, "refresh"):
            try:
                self._refresh_in_progress = True
                model.refresh()

                # Reset root index after refresh to prevent "/" from appearing
                root = "" if platform.system() == "Windows" else "/"
                self._view.setRootIndex(model.index(root))

                logger.debug(
                    "[FilesystemHandler] Model refreshed after directory change",
                    extra={"dev_only": True},
                )
            except Exception as e:
                logger.exception("[FilesystemHandler] Model refresh error: %s", e)
            finally:
                self._refresh_in_progress = False

        # Restore state after model finishes loading (async)
        from oncutf.utils.shared.timer_manager import schedule_ui_update

        schedule_ui_update(
            lambda: self._view.state_handler.restore_tree_state(
                expanded_paths, selected_path, scroll_position
            ),
            delay=100,
        )

    def _refresh_tree_on_drives_change(self, drives: list[str]) -> None:
        """Refresh tree when drives change.

        Args:
            drives: Current list of available drives

        """
        # Prevent infinite loop if this triggers another change event
        if self._refresh_in_progress:
            logger.debug(
                "[FilesystemHandler] Ignoring drives change during refresh",
                extra={"dev_only": True},
            )
            return

        logger.info("[FilesystemHandler] Drives changed, refreshing tree")

        # Save state before refresh
        expanded_paths = self._view.state_handler.save_expanded_state()
        selected_path = self._view.get_selected_path()
        scroll_position = self._view.verticalScrollBar().value()

        old_model = self._view.model()
        if not old_model:
            logger.debug("[FilesystemHandler] No model to refresh", extra={"dev_only": True})
            return

        # Get the old model's configuration
        name_filters = old_model.nameFilters() if hasattr(old_model, "nameFilters") else []
        file_filter = old_model.filter() if hasattr(old_model, "filter") else None

        try:
            # Set refresh flag to prevent recursive calls
            self._refresh_in_progress = True

            # The only reliable way to refresh drives in Windows is to recreate the model
            from oncutf.ui.widgets.custom_file_system_model import CustomFileSystemModel

            # Create new model with same configuration
            new_model = CustomFileSystemModel()

            # Set root path based on platform
            # Windows: Start from first drive (C:) to show disk tree
            # Linux/macOS: Start from root (/)
            root = "C:" if platform.system() == "Windows" else "/"
            new_model.setRootPath(root)

            if file_filter is not None:
                new_model.setFilter(file_filter)

            if name_filters:
                new_model.setNameFilters(name_filters)
                new_model.setNameFilterDisables(False)

            # Replace the model
            self._view.setModel(new_model)
            self._view.setRootIndex(new_model.index(root))

            # Update parent window reference if available
            parent = self._view.parent()
            while parent is not None:
                if hasattr(parent, "dir_model"):
                    if old_model is not None:
                        old_model.deleteLater()
                    parent.dir_model = new_model
                    logger.debug(
                        "[FilesystemHandler] Parent window dir_model reference updated",
                        extra={"dev_only": True},
                    )
                    break
                parent = parent.parent() if hasattr(parent, "parent") else None

            logger.info("[FilesystemHandler] Model recreated successfully to reflect drive changes")

            # Restore state after model finishes loading (async)
            from oncutf.utils.shared.timer_manager import schedule_ui_update

            # Capture drives for closure
            current_drives = list(drives)

            def restore_and_expand() -> None:
                self._view.state_handler.restore_tree_state(
                    expanded_paths, selected_path, scroll_position
                )
                # On Linux, auto-expand /media/ to show mounted drives (like Nemo does)
                if platform.system() == "Linux":
                    self._auto_expand_media_paths(current_drives)

            schedule_ui_update(restore_and_expand, delay=100)

        except Exception as e:
            logger.exception("[FilesystemHandler] Error recreating model: %s", e)
            from oncutf.utils.shared.timer_manager import schedule_ui_update

            schedule_ui_update(
                lambda: self._view.state_handler.restore_tree_state(
                    expanded_paths, selected_path, scroll_position
                ),
                delay=100,
            )
        finally:
            self._refresh_in_progress = False

    def _auto_expand_media_paths(self, drives: list[str]) -> None:
        """Auto-expand /media/ and user directories to show mounted drives.

        On Linux, mounted USB drives appear under /media/username/device.
        This method expands those paths so users can see newly mounted drives,
        similar to how Nemo file manager behaves.

        Args:
            drives: List of currently mounted drive paths

        """
        model = self._view.model()
        if not model:
            return

        # Collect unique parent paths that need expanding
        paths_to_expand: set[str] = set()

        for drive_path in drives:
            # Check if drive is under /media/ (typical Ubuntu/Debian pattern)
            if drive_path.startswith("/media/"):
                # Add /media
                paths_to_expand.add("/media")

                # Add /media/username (parent of the drive)
                parts = drive_path.split("/")
                if len(parts) >= 3:
                    # /media/username
                    user_path = "/".join(parts[:3])
                    if os.path.isdir(user_path):
                        paths_to_expand.add(user_path)

            # Also check /mnt/ for direct mounts
            elif drive_path.startswith("/mnt/"):
                paths_to_expand.add("/mnt")

        # Expand the paths
        for path in sorted(paths_to_expand):
            try:
                index = model.index(path)
                if index.isValid() and not self._view.isExpanded(index):
                    self._view.expand(index)
                    logger.debug(
                        "[FilesystemHandler] Auto-expanded: %s",
                        path,
                        extra={"dev_only": True},
                    )
            except Exception as e:
                logger.debug(
                    "[FilesystemHandler] Could not expand %s: %s",
                    path,
                    e,
                    extra={"dev_only": True},
                )

    def update_monitored_folder(self, folder_path: str) -> None:
        """Update the monitored folder when selection changes.

        Args:
            folder_path: New folder path to monitor

        """
        if not folder_path or not os.path.isdir(folder_path) or not self._filesystem_monitor:
            return

        try:
            if self._last_monitored_path:
                self._filesystem_monitor.remove_folder(self._last_monitored_path)
            if self._filesystem_monitor.add_folder(folder_path):
                self._last_monitored_path = folder_path
        except Exception as e:
            logger.debug(
                "[FilesystemHandler] Failed to update monitored folder: %s",
                e,
                extra={"dev_only": True},
            )

    def cleanup(self) -> None:
        """Stop filesystem monitor and clean up resources."""
        if self._filesystem_monitor is not None:
            try:
                self._filesystem_monitor.stop()
                self._filesystem_monitor.blockSignals(True)
                self._filesystem_monitor.deleteLater()
                self._filesystem_monitor = None
                logger.debug(
                    "[FilesystemHandler] Filesystem monitor stopped", extra={"dev_only": True}
                )
            except Exception as e:
                logger.warning("[FilesystemHandler] Error stopping filesystem monitor: %s", e)
