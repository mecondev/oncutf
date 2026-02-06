"""ThumbnailViewportController - Orchestration layer for thumbnail viewport operations.

Author: Michael Economou
Date: 2026-02-05

This controller orchestrates thumbnail loading, file operations, selection management,
and sorting for the thumbnail viewport. It separates business logic from UI concerns.

Architecture:
    - UI (ThumbnailViewportWidget) → Controller → Services (ThumbnailManager, FileStore)
    - Controller is UI-agnostic and testable without Qt/GUI
    - All business logic stays in controller; widget only handles UI events

Responsibilities:
    - Thumbnail loading orchestration (bulk loading, priority queue)
    - File operations (open, reveal, refresh)
    - Selection management (get, set, clear)
    - Sorting coordination
    - Statusbar updates via signals
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from PyQt5.QtCore import QItemSelectionModel, QObject, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem
    from oncutf.models.file_table.file_table_model import FileTableModel

logger = logging.getLogger(__name__)


class ThumbnailViewportController(QObject):
    """Controller for thumbnail viewport operations.

    Orchestrates thumbnail loading, file operations, selection, and sorting
    without direct UI dependencies. Emits signals for UI updates.

    Hybrid Loading System:
        - HIGH priority (6 workers): Viewport visible, immediate loading
        - BACKGROUND priority (2 workers): Viewport hidden, low-priority continuation
        - PAUSED (0 workers): After 30s timeout in background mode

    Signals:
        thumbnail_ready: Emitted when thumbnail is loaded (file_path, pixmap)
        thumbnail_progress: Emitted during loading (completed, total)
        status_update: Emitted for statusbar updates (message)
        files_reordered: Emitted when manual order changes
        viewport_mode_changed: Emitted when order mode changes ("manual" or "sorted")

    """

    # Priority levels for thumbnail loading
    PRIORITY_HIGH = 10  # Visible items, immediate loading
    PRIORITY_BACKGROUND = 5  # Background continuation when not visible
    PRIORITY_IDLE = 1  # Low-priority prefetch

    # Background mode timeout (30 seconds)
    BACKGROUND_TIMEOUT_MS = 30000

    # Signals for UI updates
    thumbnail_ready = pyqtSignal(str, QPixmap)  # file_path, pixmap
    thumbnail_progress = pyqtSignal(int, int)  # completed, total
    status_update = pyqtSignal(str)  # status message
    files_reordered = pyqtSignal()  # manual order changed
    viewport_mode_changed = pyqtSignal(str)  # "manual" or "sorted"

    def __init__(
        self,
        model: FileTableModel,
        thumbnail_manager: Any | None = None,
        parent: QObject | None = None,
    ):
        """Initialize ThumbnailViewportController.

        Args:
            model: Shared FileTableModel instance
            thumbnail_manager: Optional ThumbnailManager (gets from context if None)
            parent: Parent QObject

        """
        super().__init__(parent)
        self._model = model
        self._thumbnail_manager = thumbnail_manager
        self._thumbnail_size = 128

        # Hybrid loading state
        self._is_background_mode = False
        self._normal_worker_count = 6  # High priority worker count
        self._background_worker_count = 2  # Background mode worker count
        self._current_priority = self.PRIORITY_HIGH

        # Resume tracking - track what we've queued to avoid re-queuing on resume
        self._queued_files: set[str] = set()  # All files ever queued
        self._last_queue_priority = self.PRIORITY_HIGH

        # Background timeout timer
        self._background_timeout_timer = QTimer()
        self._background_timeout_timer.setSingleShot(True)
        self._background_timeout_timer.timeout.connect(self._on_background_timeout)

        # Connect to ThumbnailManager signals if available
        self._connect_thumbnail_manager()

        logger.info("[ThumbnailViewportController] Initialized with hybrid priority system")

    def _connect_thumbnail_manager(self) -> None:
        """Connect to ThumbnailManager signals."""
        if self._thumbnail_manager:
            self._thumbnail_manager.thumbnail_ready.connect(self._on_thumbnail_ready)
            self._thumbnail_manager.generation_progress.connect(self._on_thumbnail_progress)
            logger.debug("[ThumbnailViewportController] Connected to ThumbnailManager")
        else:
            logger.warning(
                "[ThumbnailViewportController] No ThumbnailManager provided - "
                "thumbnail operations will not work. Pass thumbnail_manager to constructor."
            )

    # -------------------------------------------------------------------------
    # Thumbnail Loading Orchestration
    # -------------------------------------------------------------------------

    def set_viewport_visible(self, visible: bool) -> None:
        """Handle viewport visibility changes for hybrid loading.

        Args:
            visible: True if viewport is visible, False if hidden

        """
        if visible:
            self._switch_to_high_priority_mode()
        else:
            self._switch_to_background_mode()

    def _switch_to_high_priority_mode(self) -> None:
        """Switch to high priority mode (viewport visible)."""
        if not self._is_background_mode and self._current_priority == self.PRIORITY_HIGH:
            return  # Already in high priority mode

        logger.info(
            "[ThumbnailViewportController] Switching to HIGH priority mode (workers: %d -> %d)",
            self._background_worker_count if self._is_background_mode else 0,
            self._normal_worker_count,
        )

        self._is_background_mode = False
        self._current_priority = self.PRIORITY_HIGH
        self._background_timeout_timer.stop()

        # Scale up workers
        if self._thumbnail_manager:
            self._thumbnail_manager.set_worker_count(self._normal_worker_count)

        # Re-queue visible items with high priority
        self._reprioritize_visible_items()

    def _switch_to_background_mode(self) -> None:
        """Switch to background mode (viewport hidden, low priority continuation)."""
        if self._is_background_mode:
            return  # Already in background mode

        logger.info(
            "[ThumbnailViewportController] Switching to BACKGROUND mode "
            "(workers: %d -> %d, timeout: %ds)",
            self._normal_worker_count,
            self._background_worker_count,
            self.BACKGROUND_TIMEOUT_MS // 1000,
        )

        self._is_background_mode = True
        self._current_priority = self.PRIORITY_BACKGROUND

        # Scale down workers for background loading
        if self._thumbnail_manager:
            self._thumbnail_manager.set_worker_count(self._background_worker_count)

        # Start 30-second timeout to pause loading
        self._background_timeout_timer.start(self.BACKGROUND_TIMEOUT_MS)

    def _on_background_timeout(self) -> None:
        """Pause thumbnail loading after background timeout."""
        if not self._is_background_mode:
            return

        logger.info(
            "[ThumbnailViewportController] Background loading timeout - pausing thumbnail generation"
        )
        self._current_priority = self.PRIORITY_IDLE

        # Pause by removing workers
        if self._thumbnail_manager:
            self._thumbnail_manager.set_worker_count(0)

    def _reprioritize_visible_items(self) -> None:
        """Re-prioritize visible items on resume without duplicate queueing.

        Called when switching back to high priority mode. Only queues items
        that haven't been queued yet (smart resume).
        """
        # This is now implemented via prioritize_visible_thumbnails() from viewport
        # The viewport will call it with the current visible range
        logger.debug("[ThumbnailViewportController] Ready to re-prioritize visible items on demand")

    def queue_all_thumbnails(self, size_px: int = 128) -> None:
        """Queue all file thumbnails with priority based on visibility.

        Called when files are loaded into the model. Uses current priority
        based on viewport visibility (HIGH when visible, BACKGROUND when hidden).

        Smart queueing: Tracks what has been queued to enable resume without
        re-queueing on priority changes.

        Args:
            size_px: Thumbnail size in pixels

        """
        if not self._thumbnail_manager:
            logger.debug("[ThumbnailViewportController] ThumbnailManager not available")
            return

        self._thumbnail_size = size_px

        # Get all file paths from model
        file_paths = []
        for row in range(self._model.rowCount()):
            index = self._model.index(row, 0)
            file_item = index.data(0x0100)  # Qt.UserRole
            if file_item:
                file_paths.append(file_item.full_path)

        if file_paths:
            # Update queued files tracking
            new_files = set(file_paths) - self._queued_files
            self._queued_files.update(file_paths)

            # Use current priority (HIGH when visible, BACKGROUND when hidden)
            priority = self._current_priority
            self._last_queue_priority = priority

            # Only queue new files (smart resume)
            if new_files:
                self._thumbnail_manager.queue_all_thumbnails(
                    file_paths=list(new_files), priority=priority, size_px=size_px
                )
                logger.info(
                    "[ThumbnailViewportController] Queued %d new files with priority=%d "
                    "(background_mode=%s, total_tracked=%d)",
                    len(new_files),
                    priority,
                    self._is_background_mode,
                    len(self._queued_files),
                )
            else:
                logger.debug(
                    "[ThumbnailViewportController] All %d files already queued, skipping",
                    len(file_paths),
                )

    def prioritize_visible_thumbnails(self, visible_file_paths: list[str]) -> None:
        """Re-queue visible thumbnails with high priority.

        Called when viewport scrolls to ensure visible items load first.

        Args:
            visible_file_paths: List of visible file paths

        """
        if not self._thumbnail_manager or not visible_file_paths:
            return

        # Re-queue visible items with high priority
        self._thumbnail_manager.queue_all_thumbnails(
            file_paths=visible_file_paths, priority=self.PRIORITY_HIGH, size_px=self._thumbnail_size
        )
        logger.debug(
            "[ThumbnailViewportController] Prioritized %d visible thumbnails",
            len(visible_file_paths),
        )

    def clear_pending_thumbnail_requests(self) -> None:
        """Clear pending thumbnail requests from ThumbnailManager.

        Called when files are cleared to prevent stale thumbnail updates.
        Also resets tracking state for fresh start.
        """
        if not self._thumbnail_manager:
            return

        try:
            self._thumbnail_manager.clear_pending_requests()
            # Clear tracking state for fresh start
            self._queued_files.clear()
            logger.debug(
                "[ThumbnailViewportController] Cleared pending requests and tracking state"
            )
        except Exception as e:
            logger.debug("[ThumbnailViewportController] Error clearing pending requests: %s", e)

    def get_loading_stats(self) -> dict[str, int]:
        """Get thumbnail loading statistics for progress monitoring.

        Returns:
            dict with keys:
                - queued: Files queued by controller
                - queue_size: Items in ThumbnailManager queue
                - completed: Completed thumbnail requests
                - total: Total thumbnail requests
                - cached: Cached thumbnails (from stats)
                - active_workers: Currently active workers

        """
        if not self._thumbnail_manager:
            return {
                "queued": len(self._queued_files),
                "queue_size": 0,
                "completed": 0,
                "total": 0,
                "cached": 0,
                "active_workers": 0,
            }

        stats = self._thumbnail_manager.get_cache_stats()
        return {
            "queued": len(self._queued_files),
            "queue_size": stats.get("queue_size", 0),
            "completed": stats.get("completed_requests", 0),
            "total": stats.get("total_requests", 0),
            "cached": stats.get("memory_entries", 0) + stats.get("disk_entries", 0),
            "active_workers": stats.get("active_workers", 0),
        }

    def _on_thumbnail_ready(self, file_path: str, pixmap: QPixmap) -> None:
        """Handle thumbnail ready signal from ThumbnailManager.

        Args:
            file_path: Source file path
            pixmap: Generated thumbnail

        """
        # Forward to UI
        self.thumbnail_ready.emit(file_path, pixmap)
        logger.debug("[ThumbnailViewportController] Thumbnail ready: %s", file_path)

    def _on_thumbnail_progress(self, completed: int, total: int) -> None:
        """Handle thumbnail generation progress.

        Args:
            completed: Number of completed thumbnails
            total: Total thumbnails to generate

        """
        # Forward to UI
        self.thumbnail_progress.emit(completed, total)

        # Update status message
        status_msg = f"Loading thumbnails: {completed}/{total}"
        self.status_update.emit(status_msg)

    # -------------------------------------------------------------------------
    # Selection Management
    # -------------------------------------------------------------------------

    def get_selected_file_paths(self, selection_model: Any) -> list[str]:
        """Get list of selected file paths.

        Args:
            selection_model: QItemSelectionModel from view

        Returns:
            List of absolute file paths

        """
        if not selection_model:
            return []

        selected_rows = sorted({idx.row() for idx in selection_model.selectedIndexes()})
        file_paths = []

        for row in selected_rows:
            index = self._model.index(row, 0)
            file_item = index.data(0x0100)  # Qt.UserRole
            if file_item:
                file_paths.append(file_item.full_path)

        return file_paths

    def select_files_by_paths(self, file_paths: list[str], selection_model: Any) -> None:
        """Select files by their paths.

        Args:
            file_paths: List of file paths to select
            selection_model: QItemSelectionModel from view

        """
        if not selection_model:
            return

        # Clear current selection
        selection_model.clearSelection()

        # Find and select matching rows
        for row in range(self._model.rowCount()):
            index = self._model.index(row, 0)
            file_item = index.data(Qt.ItemDataRole.UserRole)
            if file_item and file_item.full_path in file_paths:
                selection_model.select(index, QItemSelectionModel.SelectionFlag.Select)

        logger.debug("[ThumbnailViewportController] Selected %d files", len(file_paths))

    # -------------------------------------------------------------------------
    # File Operations
    # -------------------------------------------------------------------------

    def open_selected_files(self, selection_model: Any) -> dict[str, Any]:
        """Open selected files in default application.

        Args:
            selection_model: QItemSelectionModel from view

        Returns:
            dict: {"success": bool, "opened_count": int, "errors": list[str]}

        """
        file_paths = self.get_selected_file_paths(selection_model)
        if not file_paths:
            return {"success": False, "opened_count": 0, "errors": ["No files selected"]}

        opened_count = 0
        errors = []

        for file_path in file_paths:
            try:
                import platform
                import subprocess

                if platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", file_path], check=True)
                elif platform.system() == "Windows":
                    subprocess.run(["start", "", file_path], shell=True, check=True)
                else:  # Linux
                    subprocess.run(["xdg-open", file_path], check=True)

                opened_count += 1
                logger.info("[ThumbnailViewportController] Opened file: %s", file_path)

            except Exception as e:
                error_msg = f"Failed to open {Path(file_path).name}: {e}"
                errors.append(error_msg)
                logger.warning("[ThumbnailViewportController] %s", error_msg)

        return {
            "success": opened_count > 0,
            "opened_count": opened_count,
            "errors": errors,
        }

    def reveal_in_file_manager(self, selection_model: Any) -> dict[str, Any]:
        """Reveal selected files in file manager.

        Args:
            selection_model: QItemSelectionModel from view

        Returns:
            dict: {"success": bool, "revealed_count": int, "errors": list[str]}

        """
        file_paths = self.get_selected_file_paths(selection_model)
        if not file_paths:
            return {"success": False, "revealed_count": 0, "errors": ["No files selected"]}

        revealed_count = 0
        errors = []

        for file_path in file_paths:
            try:
                import platform
                import subprocess

                if platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", "-R", file_path], check=True)
                elif platform.system() == "Windows":
                    subprocess.run(["explorer", "/select,", file_path], check=True)
                else:  # Linux
                    # Try Nautilus first, fallback to opening parent directory
                    try:
                        subprocess.run(["nautilus", "--select", file_path], check=True)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        parent_dir = str(Path(file_path).parent)
                        subprocess.run(["xdg-open", parent_dir], check=True)

                revealed_count += 1
                logger.info("[ThumbnailViewportController] Revealed file: %s", file_path)

            except Exception as e:
                error_msg = f"Failed to reveal {Path(file_path).name}: {e}"
                errors.append(error_msg)
                logger.warning("[ThumbnailViewportController] %s", error_msg)

        return {
            "success": revealed_count > 0,
            "revealed_count": revealed_count,
            "errors": errors,
        }

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    def cleanup(self) -> None:
        """Clean up controller resources."""
        self._background_timeout_timer.stop()
        logger.debug("[ThumbnailViewportController] Controller cleanup completed")

    # -------------------------------------------------------------------------
    # Sorting Operations
    # -------------------------------------------------------------------------

    def sort_by(self, sort_key: str, reverse: bool = False) -> None:
        """Sort files by given key.

        Args:
            sort_key: Sort key ("name", "date", "size", etc.)
            reverse: Sort in reverse order

        """
        logger.info("[ThumbnailViewportController] Sorting by %s (reverse=%s)", sort_key, reverse)

        # Delegate to model
        self._model.set_order_mode("sorted", sort_key=sort_key, reverse=reverse)

        # Emit mode change
        self.viewport_mode_changed.emit("sorted")

    def return_to_manual_order(self) -> None:
        """Return to manual drag-drop order."""
        logger.info("[ThumbnailViewportController] Returning to manual order")

        # Delegate to model
        self._model.set_order_mode("manual")

        # Emit mode change
        self.viewport_mode_changed.emit("manual")
        self.files_reordered.emit()

    def get_order_mode(self) -> Literal["manual", "sorted"]:
        """Get current order mode.

        Returns:
            "manual" or "sorted"

        """
        # FileTableModel stores order mode internally
        mode = getattr(self._model, "_order_mode", "manual")
        return "sorted" if mode == "sorted" else "manual"

    # -------------------------------------------------------------------------
    # Refresh Operations
    # -------------------------------------------------------------------------

    def refresh_files(self) -> None:
        """Refresh file list (reload from last folder)."""
        logger.info("[ThumbnailViewportController] Refreshing file list")

        # This would need FileLoadController integration
        # For now, just log
        logger.warning("[ThumbnailViewportController] refresh_files not fully implemented")

    # -------------------------------------------------------------------------
    # State Queries
    # -------------------------------------------------------------------------

    def get_file_count(self) -> int:
        """Get total file count.

        Returns:
            Number of files in model

        """
        return self._model.rowCount()

    def get_thumbnail_cache_stats(self) -> dict[str, int]:
        """Get thumbnail cache statistics.

        Returns:
            dict with cache stats

        """
        if not self._thumbnail_manager:
            return {}

        try:
            stats = self._thumbnail_manager.get_cache_stats()
            return dict(stats) if stats else {}
        except Exception as e:
            logger.warning("[ThumbnailViewportController] Error getting cache stats: %s", e)
            return {}

    def set_thumbnail_size(self, size_px: int) -> None:
        """Set thumbnail size for future requests.

        Args:
            size_px: Thumbnail size in pixels

        """
        self._thumbnail_size = size_px
