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

from PyQt5.QtCore import QItemSelectionModel, QObject, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem
    from oncutf.models.file_table.file_table_model import FileTableModel

logger = logging.getLogger(__name__)


class ThumbnailViewportController(QObject):
    """Controller for thumbnail viewport operations.

    Orchestrates thumbnail loading, file operations, selection, and sorting
    without direct UI dependencies. Emits signals for UI updates.

    Signals:
        thumbnail_ready: Emitted when thumbnail is loaded (file_path, pixmap)
        thumbnail_progress: Emitted during loading (completed, total)
        status_update: Emitted for statusbar updates (message)
        files_reordered: Emitted when manual order changes
        viewport_mode_changed: Emitted when order mode changes ("manual" or "sorted")

    """

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

        # Connect to ThumbnailManager signals if available
        self._connect_thumbnail_manager()

        logger.info("[ThumbnailViewportController] Initialized")

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

    def queue_all_thumbnails(self, size_px: int = 128) -> None:
        """Queue all file thumbnails for background loading (priority=0).

        Called when files are loaded into the model. Ensures all thumbnails
        are generated in background, with visible viewport items prioritized
        via viewport scrolling (implemented in widget).

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
            # Queue all with priority=0 (background)
            self._thumbnail_manager.queue_all_thumbnails(
                file_paths=file_paths, priority=0, size_px=size_px
            )
            logger.info(
                "[ThumbnailViewportController] Queued %d files for background thumbnail loading",
                len(file_paths),
            )

    def prioritize_visible_thumbnails(self, visible_file_paths: list[str]) -> None:
        """Re-queue visible thumbnails with high priority (priority=1).

        Called when viewport scrolls to ensure visible items load first.

        Args:
            visible_file_paths: List of visible file paths

        """
        if not self._thumbnail_manager or not visible_file_paths:
            return

        # Re-queue visible items with high priority
        self._thumbnail_manager.queue_all_thumbnails(
            file_paths=visible_file_paths, priority=1, size_px=self._thumbnail_size
        )
        logger.debug(
            "[ThumbnailViewportController] Prioritized %d visible thumbnails",
            len(visible_file_paths),
        )

    def clear_pending_thumbnail_requests(self) -> None:
        """Clear pending thumbnail requests from ThumbnailManager.

        Called when files are cleared to prevent stale thumbnail updates.
        """
        if not self._thumbnail_manager:
            return

        try:
            self._thumbnail_manager.clear_pending_requests()
            logger.debug("[ThumbnailViewportController] Cleared pending thumbnail requests")
        except Exception as e:
            logger.debug("[ThumbnailViewportController] Error clearing pending requests: %s", e)

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
            file_item = index.data(Qt.UserRole)
            if file_item and file_item.full_path in file_paths:
                selection_model.select(index, QItemSelectionModel.Select)

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
