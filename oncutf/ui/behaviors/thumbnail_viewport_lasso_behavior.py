"""Thumbnail Viewport Lasso Selection Behavior.

Author: Michael Economou
Date: 2026-02-06

Provides lasso (rubber band) selection functionality for thumbnail viewport.
"""

from typing import TYPE_CHECKING

from PyQt5.QtCore import (
    QEvent,
    QItemSelection,
    QItemSelectionModel,
    QItemSelectionRange,
    QPoint,
    QRect,
    QSize,
    Qt,
)
from PyQt5.QtWidgets import QRubberBand

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from PyQt5.QtGui import QMouseEvent
    from PyQt5.QtWidgets import QListView

    from oncutf.models.file_table.file_table_model import FileTableModel

logger = get_cached_logger(__name__)


class ThumbnailViewportLassoBehavior:
    """Handles lasso selection (rubber band) for thumbnail viewport."""

    def __init__(self, list_view: "QListView", model: "FileTableModel"):
        """Initialize lasso selection behavior.

        Args:
            list_view: QListView widget to control
            model: File table model

        """
        self._list_view = list_view
        self._model = model

        # Create rubber band for lasso selection
        self._rubber_band = QRubberBand(QRubberBand.Rectangle, list_view.viewport())
        self._rubber_band.hide()

        self._rubber_band_origin: QPoint | None = None

    def is_active(self) -> bool:
        """Check if lasso selection is active.

        Returns:
            True if rubber band is visible

        """
        return self._rubber_band is not None and self._rubber_band.isVisible()

    def start_lasso(self, pos: QPoint) -> None:
        """Start lasso selection.

        Args:
            pos: Mouse position where lasso started

        """
        self._rubber_band_origin = pos
        self._rubber_band.setGeometry(QRect(self._rubber_band_origin, QSize()))
        self._rubber_band.show()
        logger.debug("[LassoBehavior] Lasso started at %s", pos)

    def update_lasso(self, pos: QPoint) -> None:
        """Update lasso geometry and selection.

        Args:
            pos: Current mouse position

        """
        if not self._rubber_band_origin or not self._rubber_band.isVisible():
            return

        # Update rubber band geometry
        self._rubber_band.setGeometry(QRect(self._rubber_band_origin, pos).normalized())

        # Update selection based on intersection
        self._update_selection()

    def end_lasso(self) -> None:
        """End lasso selection."""
        if not self._rubber_band.isVisible():
            return

        self._rubber_band.hide()
        self._rubber_band_origin = None
        logger.debug("[LassoBehavior] Lasso ended")

    def _update_selection(self) -> None:
        """Update selection based on rubber band intersection."""
        if not self._rubber_band or not self._rubber_band.isVisible():
            return

        if not self._model or self._model.rowCount() == 0:
            return

        rubber_rect = self._rubber_band.geometry()
        selection = QItemSelection()

        # Check all items for intersection
        for row in range(self._model.rowCount()):
            index = self._model.index(row, 0)
            if not index.isValid():
                continue

            item_rect = self._list_view.visualRect(index)

            if rubber_rect.intersects(item_rect):
                selection.append(QItemSelectionRange(index))

        # Apply selection (replace current selection)
        selection_model = self._list_view.selectionModel()
        if selection_model:
            selection_model.select(selection, QItemSelectionModel.ClearAndSelect)

    def handle_event_filter(self, obj: "QListView", event: QEvent) -> bool:
        """Handle events from event filter.

        Args:
            obj: Watched object
            event: Event

        Returns:
            True if event handled, False otherwise

        """
        event_type = event.type()

        # Left button press - start lasso (only on empty space)
        if event_type == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                index = self._list_view.indexAt(event.pos())
                # Start lasso only if clicking on empty space
                if not index.isValid():
                    self.start_lasso(event.pos())
                    return False  # Let QListView handle the click

        # Mouse move - update lasso
        elif event_type == QEvent.MouseMove:
            if self._rubber_band and self._rubber_band.isVisible() and self._rubber_band_origin:
                self.update_lasso(event.pos())
                return True

        # Left button release - end lasso
        elif (
            event_type == QEvent.MouseButtonRelease
            and event.button() == Qt.LeftButton
            and self._rubber_band
            and self._rubber_band.isVisible()
        ):
            self.end_lasso()
            return False  # Let QListView handle the release

        return False
