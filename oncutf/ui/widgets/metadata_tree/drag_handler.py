"""
Module: drag_handler.py

Author: Michael Economou
Date: 2025-12-23

Drag and drop handler for the metadata tree widget.

This module handles all drag & drop operations for the MetadataTreeView:
- Accepting drags only from the internal file table
- Processing drops to trigger metadata loading
- Cleanup after drag operations

The handler is Qt-aware but delegates metadata loading to the parent window.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from oncutf.core.pyqt_imports import (
    QApplication,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    Qt,
)
from oncutf.utils.logger_factory import get_cached_logger
from oncutf.utils.timer_manager import schedule_drag_cleanup

if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_tree_view import MetadataTreeView

logger = get_cached_logger(__name__)


class MetadataTreeDragHandler:
    """
    Handler for drag and drop operations in the metadata tree.

    This class encapsulates all drag & drop logic:
    - Validating drag sources (only accepts from internal file table)
    - Processing drop events
    - Triggering metadata loading via parent window
    - Cleanup after drag operations

    Usage:
        handler = MetadataTreeDragHandler(tree_view)
        # In tree view:
        def dragEnterEvent(self, event):
            self._drag_handler.handle_drag_enter(event)
    """

    # Custom MIME type for internal file table drags
    MIME_TYPE = "application/x-oncutf-filetable"

    def __init__(self, tree_view: MetadataTreeView) -> None:
        """
        Initialize the drag handler.

        Args:
            tree_view: The MetadataTreeView instance this handler belongs to
        """
        self._tree_view = tree_view

    def handle_drag_enter(self, event: QDragEnterEvent) -> None:
        """
        Accept drag only if it comes from our application's file table.

        This is identified by the presence of our custom MIME type.

        Args:
            event: The drag enter event
        """
        if event.mimeData().hasFormat(self.MIME_TYPE):
            event.acceptProposedAction()
        else:
            event.ignore()

    def handle_drag_move(self, event: QDragMoveEvent) -> None:
        """
        Continue accepting drag move events only for items from our file table.

        Args:
            event: The drag move event
        """
        if event.mimeData().hasFormat(self.MIME_TYPE):
            event.acceptProposedAction()
        else:
            event.ignore()

    def handle_drop(self, event: QDropEvent) -> None:
        """
        Handle drop events for file loading.

        Processes the dropped files and triggers metadata loading via the
        parent window's application service.

        Args:
            event: The drop event
        """
        # Get and deactivate any drag cancel filter
        _drag_cancel_filter = getattr(self._tree_view, "_drag_cancel_filter", None)
        if _drag_cancel_filter:
            _drag_cancel_filter.deactivate()

        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            files = [url.toLocalFile() for url in urls if url.isLocalFile()]
            if files:
                event.acceptProposedAction()

                # Check for modifiers (Shift = Extended Metadata)
                modifiers = event.keyboardModifiers()
                use_extended = bool(modifiers & Qt.ShiftModifier)

                # Trigger metadata load via parent window -> application service
                self._trigger_metadata_load(files, use_extended)

                logger.debug(
                    "[MetadataTreeDragHandler] Drop processed: %d files (extended=%s)",
                    len(files),
                    use_extended,
                    extra={"dev_only": True},
                )

                # Update viewport
                self._tree_view.viewport().update()
            else:
                event.ignore()
                self._perform_drag_cleanup(_drag_cancel_filter)
        else:
            event.ignore()
            self._perform_drag_cleanup(_drag_cancel_filter)

        # Schedule drag cleanup
        schedule_drag_cleanup(self._complete_drag_cleanup, 0)

    def _trigger_metadata_load(self, files: list[str], use_extended: bool) -> None:
        """
        Trigger metadata loading for dropped files.

        Args:
            files: List of file paths to load metadata for
            use_extended: Whether to load extended metadata
        """
        parent_window = self._tree_view._get_parent_with_file_table()
        if not parent_window or not hasattr(parent_window, "load_metadata_for_items"):
            logger.warning(
                "[MetadataTreeDragHandler] Cannot load metadata - no parent window",
                extra={"dev_only": True},
            )
            return

        if not hasattr(parent_window, "file_model"):
            logger.warning(
                "[MetadataTreeDragHandler] Cannot load metadata - no file model",
                extra={"dev_only": True},
            )
            return

        # Convert file paths to FileItems
        file_items = []
        for file_path in files:
            for item in parent_window.file_model.files:
                if item.path == file_path:
                    file_items.append(item)
                    break

        if not file_items:
            logger.debug(
                "[MetadataTreeDragHandler] No matching file items found for dropped files",
                extra={"dev_only": True},
            )
            return

        # Ensure files are checked (selected) after drag & drop
        for item in file_items:
            if not item.checked:
                item.checked = True

        # Update file table model to reflect changes
        if hasattr(parent_window, "file_table_model"):
            parent_window.file_table_model.layoutChanged.emit()

        # Trigger metadata loading
        parent_window.load_metadata_for_items(
            file_items,
            use_extended=use_extended,
            source="drag_drop"
        )

    def _perform_drag_cleanup(self, _drag_cancel_filter: Any) -> None:
        """
        Centralized drag cleanup logic.

        Args:
            _drag_cancel_filter: The drag cancel filter (interface parameter)
        """
        # Force cleanup of any drag state
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()
        self._tree_view.viewport().update()

    def _complete_drag_cleanup(self) -> None:
        """Complete cleanup after drag operation."""
        self._tree_view.viewport().update()
