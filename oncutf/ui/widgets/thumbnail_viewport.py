"""Thumbnail Viewport Widget for grid-based file browsing.

Author: Michael Economou
Date: 2026-01-16

Provides a thumbnail grid view with:
- QListView in IconMode (virtual scrolling for performance)
- Shared FileTableModel (no data duplication)
- Zoom support (64-256px via mouse wheel)
- Pan support (middle mouse button)
- Selection (Ctrl/Shift click, lasso with QRubberBand)
- Drag reorder (manual mode only)
- Context menu (sort, manual order, file operations)
- Color flag and video duration display via delegate
"""

from typing import TYPE_CHECKING, Literal

from PyQt5.QtCore import (
    QEvent,
    QItemSelection,
    QItemSelectionModel,
    QItemSelectionRange,
    QPoint,
    QRect,
    QSize,
    Qt,
    pyqtSignal,
)
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QListView,
    QMenu,
    QRubberBand,
    QVBoxLayout,
    QWidget,
)

from oncutf.ui.delegates.thumbnail_delegate import ThumbnailDelegate
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from PyQt5.QtCore import QModelIndex
    from PyQt5.QtGui import QPixmap

    from oncutf.models.file_table.file_table_model import FileTableModel

logger = get_cached_logger(__name__)


class ThumbnailViewportWidget(QWidget):
    """Thumbnail grid viewport for visual file browsing.

    Displays files from FileTableModel as a grid of thumbnails with:
    - Zoom (64-256px)
    - Pan (middle mouse drag)
    - Multi-selection (Ctrl/Shift/Lasso)
    - Drag reorder (manual mode only)
    - Context menu for sorting and file operations

    Shares the same FileTableModel instance as the file table view,
    ensuring automatic synchronization of file list and selection state.
    """

    # Signals
    file_activated = pyqtSignal(str)  # file_path - emitted on double-click
    files_reordered = pyqtSignal()  # Emitted when manual order changes
    viewport_mode_changed = pyqtSignal(str)  # "manual" or "sorted"

    # Zoom limits
    MIN_THUMBNAIL_SIZE = 64
    MAX_THUMBNAIL_SIZE = 256
    DEFAULT_THUMBNAIL_SIZE = 128
    ZOOM_STEP = 16

    def __init__(self, model: "FileTableModel", parent: QWidget | None = None):
        """Initialize the thumbnail viewport.

        Args:
            model: Shared FileTableModel instance
            parent: Parent widget
        """
        super().__init__(parent)
        self._model = model
        self._thumbnail_size = self.DEFAULT_THUMBNAIL_SIZE

        # Lasso selection state
        self._rubber_band: QRubberBand | None = None
        self._rubber_band_origin: QPoint | None = None

        # Pan state
        self._is_panning = False
        self._pan_start_pos: QPoint | None = None

        self._setup_ui()
        self._connect_signals()

        logger.info("[ThumbnailViewport] Initialized with thumbnail size: %d", self._thumbnail_size)

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create QListView in IconMode
        self._list_view = QListView(self)
        self._list_view.setViewMode(QListView.IconMode)
        self._list_view.setResizeMode(QListView.Adjust)
        self._list_view.setSpacing(10)
        self._list_view.setUniformItemSizes(True)  # Performance optimization
        self._list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list_view.setMovement(QListView.Free)  # Allow drag rearrange

        # Set model
        self._list_view.setModel(self._model)

        # Create and set delegate
        self._delegate = ThumbnailDelegate(self._list_view)
        self._delegate.set_thumbnail_size(self._thumbnail_size)
        self._list_view.setItemDelegate(self._delegate)

        # Install event filter for lasso selection and pan
        self._list_view.viewport().installEventFilter(self)

        # Create rubber band (hidden initially)
        self._rubber_band = QRubberBand(QRubberBand.Rectangle, self._list_view.viewport())
        self._rubber_band.hide()

        layout.addWidget(self._list_view)

    def _connect_signals(self) -> None:
        """Connect Qt signals."""
        # Double-click activation
        self._list_view.doubleClicked.connect(self._on_item_activated)

        # Context menu
        self._list_view.customContextMenuRequested.connect(self._on_context_menu)

        # Model changes (for manual order save)
        self._model.layoutChanged.connect(self._on_model_layout_changed)

        # Connect thumbnail_ready signal from ThumbnailManager
        try:
            from oncutf.core.application_context import ApplicationContext

            context = ApplicationContext.get_instance()
            if context and context.has_manager("thumbnail"):
                thumbnail_manager = context.get_manager("thumbnail")
                thumbnail_manager.thumbnail_ready.connect(self._on_thumbnail_ready)
                logger.debug("[ThumbnailViewport] Connected to thumbnail_ready signal")
        except Exception as e:
            logger.warning("[ThumbnailViewport] Could not connect to ThumbnailManager: %s", e)

    def set_order_mode(self, mode: Literal["manual", "sorted"]) -> None:
        """Set the order mode (manual drag or sorted).

        Args:
            mode: "manual" for drag reorder, "sorted" for Qt sort
        """
        # Delegate to model
        if mode == "manual":
            self._model.set_order_mode("manual")
        # Note: sorted mode set by _sort_by() with specific key

        # Enable/disable drag reorder based on mode
        if mode == "manual":
            self._list_view.setDragDropMode(QAbstractItemView.InternalMove)
            logger.info("[ThumbnailViewport] Drag reorder enabled (manual mode)")
        else:
            self._list_view.setDragDropMode(QAbstractItemView.NoDragDrop)
            logger.info("[ThumbnailViewport] Drag reorder disabled (sorted mode)")

        self.viewport_mode_changed.emit(mode)

    def set_thumbnail_size(self, size: int) -> None:
        """Set the thumbnail size and refresh view.

        Args:
            size: Thumbnail size in pixels (clamped to MIN/MAX)
        """
        size = max(self.MIN_THUMBNAIL_SIZE, min(size, self.MAX_THUMBNAIL_SIZE))

        if size != self._thumbnail_size:
            self._thumbnail_size = size
            self._delegate.set_thumbnail_size(size)

            # Force layout update
            self._list_view.scheduleDelayedItemsLayout()

            logger.debug("[ThumbnailViewport] Thumbnail size changed to: %d", size)

    def zoom_in(self) -> None:
        """Increase thumbnail size by ZOOM_STEP."""
        new_size = self._thumbnail_size + self.ZOOM_STEP
        self.set_thumbnail_size(new_size)

    def zoom_out(self) -> None:
        """Decrease thumbnail size by ZOOM_STEP."""
        new_size = self._thumbnail_size - self.ZOOM_STEP
        self.set_thumbnail_size(new_size)

    def reset_zoom(self) -> None:
        """Reset thumbnail size to default."""
        self.set_thumbnail_size(self.DEFAULT_THUMBNAIL_SIZE)

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        """Event filter for lasso selection and pan support.

        Args:
            obj: Watched object (viewport)
            event: Event

        Returns:
            True if event handled, False otherwise
        """
        if obj != self._list_view.viewport():
            return super().eventFilter(obj, event)

        event_type = event.type()

        # Mouse wheel for zoom (Ctrl+wheel)
        if event_type == QEvent.Wheel:
            if event.modifiers() & Qt.ControlModifier:
                if event.angleDelta().y() > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
                return True

        # Middle button pan
        elif event_type == QEvent.MouseButtonPress:
            if event.button() == Qt.MiddleButton:
                self._is_panning = True
                self._pan_start_pos = event.pos()
                self._list_view.viewport().setCursor(Qt.ClosedHandCursor)
                return True

            # Lasso selection (left button on empty space, no modifiers for now)
            elif event.button() == Qt.LeftButton:
                index = self._list_view.indexAt(event.pos())
                # Start lasso only if clicking on empty space
                if not index.isValid():
                    self._rubber_band_origin = event.pos()
                    self._rubber_band.setGeometry(QRect(self._rubber_band_origin, QSize()))
                    self._rubber_band.show()
                    return False  # Let QListView handle the click

        elif event_type == QEvent.MouseMove:
            # Pan
            if self._is_panning and self._pan_start_pos:
                delta = event.pos() - self._pan_start_pos
                h_bar = self._list_view.horizontalScrollBar()
                v_bar = self._list_view.verticalScrollBar()

                h_bar.setValue(h_bar.value() - delta.x())
                v_bar.setValue(v_bar.value() - delta.y())

                self._pan_start_pos = event.pos()
                return True

            # Lasso selection
            elif self._rubber_band.isVisible() and self._rubber_band_origin:
                # Update rubber band geometry
                self._rubber_band.setGeometry(
                    QRect(self._rubber_band_origin, event.pos()).normalized()
                )

                # Calculate intersecting items
                self._update_lasso_selection()
                return True

        elif event_type == QEvent.MouseButtonRelease:
            # End pan
            if event.button() == Qt.MiddleButton and self._is_panning:
                self._is_panning = False
                self._pan_start_pos = None
                self._list_view.viewport().setCursor(Qt.ArrowCursor)
                return True

            # End lasso
            elif event.button() == Qt.LeftButton and self._rubber_band.isVisible():
                self._rubber_band.hide()
                self._rubber_band_origin = None
                return False  # Let QListView handle the release

        return super().eventFilter(obj, event)

    def _update_lasso_selection(self) -> None:
        """Update selection based on rubber band intersection."""
        if not self._rubber_band.isVisible():
            return

        rubber_rect = self._rubber_band.geometry()
        selection = QItemSelection()

        # Check all items for intersection
        for row in range(self._model.rowCount()):
            index = self._model.index(row, 0)
            item_rect = self._list_view.visualRect(index)

            if rubber_rect.intersects(item_rect):
                selection.append(QItemSelectionRange(index))

        # Apply selection (replace current selection)
        selection_model = self._list_view.selectionModel()
        if selection_model:
            selection_model.select(selection, QItemSelectionModel.ClearAndSelect)

    def _on_item_activated(self, index: "QModelIndex") -> None:
        """Handle double-click on thumbnail.

        Args:
            index: Clicked model index
        """
        file_item = index.data(Qt.UserRole)
        if file_item:
            self.file_activated.emit(file_item.file_path)
            logger.debug("[ThumbnailViewport] File activated: %s", file_item.filename)

    def _on_context_menu(self, position: QPoint) -> None:
        """Show context menu for thumbnail operations.

        Args:
            position: Click position in widget coordinates
        """
        menu = QMenu(self)

        # Sort submenu
        sort_menu = menu.addMenu("Sort")
        sort_menu.addAction("Ascending (A-Z)", lambda: self._sort_by("filename", False))
        sort_menu.addAction("Descending (Z-A)", lambda: self._sort_by("filename", True))
        sort_menu.addAction("By Color Flag", lambda: self._sort_by("color", False))

        menu.addSeparator()

        # Order mode toggle
        if self._model.order_mode == "sorted":
            menu.addAction("Return to Manual Order", lambda: self._return_to_manual_order())
        else:
            menu.addAction("Manual Order Active", None).setEnabled(False)

        menu.addSeparator()

        # File operations (TODO: integrate with existing context menu handlers)
        menu.addAction("Open File Location", self._open_file_location)
        menu.addAction("Refresh", self._refresh)

        # Show menu
        menu.exec_(self._list_view.viewport().mapToGlobal(position))

    def _sort_by(self, key: str, reverse: bool) -> None:
        """Sort files by key and switch to sorted mode.

        Args:
            key: Sort key ("filename", "color", etc.)
            reverse: Reverse order
        """
        logger.info("[ThumbnailViewport] Sorting by %s (reverse=%s)", key, reverse)

        # Delegate to model
        self._model.set_order_mode("sorted", sort_key=key, reverse=reverse)

        # Update local UI state
        self.set_order_mode("sorted")

    def _return_to_manual_order(self) -> None:
        """Return to manual order mode and load from DB."""
        logger.info("[ThumbnailViewport] Returning to manual order")

        # Delegate to model (will load from DB)
        self._model.set_order_mode("manual")

        # Update local UI state
        self.set_order_mode("manual")

    def _open_file_location(self) -> None:
        """Open file location in system file manager."""
        # TODO: Integrate with existing file operations
        logger.warning("[ThumbnailViewport] Open file location not yet implemented")

    def _refresh(self) -> None:
        """Refresh the viewport."""
        self._list_view.viewport().update()
        logger.debug("[ThumbnailViewport] Viewport refreshed")

    def get_selected_files(self) -> list[str]:
        """Get list of selected file paths.

        Returns:
            List of selected file paths
        """
        selection_model = self._list_view.selectionModel()
        if not selection_model:
            return []

        selected_indexes = selection_model.selectedIndexes()
        file_paths = []

        for index in selected_indexes:
            file_item = index.data(Qt.UserRole)
            if file_item:
                file_paths.append(file_item.full_path)

        return file_paths

    def select_files(self, file_paths: list[str]) -> None:
        """Select files by file paths (for sync with table view).

        Args:
            file_paths: List of file paths to select
        """
        selection_model = self._list_view.selectionModel()
        if not selection_model:
            return

        selection = QItemSelection()
        file_path_set = set(file_paths)

        for row in range(self._model.rowCount()):
            index = self._model.index(row, 0)
            file_item = index.data(Qt.UserRole)

            if file_item and file_item.full_path in file_path_set:
                selection.append(QItemSelectionRange(index))

        selection_model.select(selection, QItemSelectionModel.ClearAndSelect)
        logger.debug("[ThumbnailViewport] Selected %d files", len(file_paths))

    def clear_selection(self) -> None:
        """Clear all selections."""
        selection_model = self._list_view.selectionModel()
        if selection_model:
            selection_model.clearSelection()

    def get_thumbnail_size(self) -> int:
        """Get current thumbnail size.

        Returns:
            Current thumbnail size in pixels
        """
        return self._thumbnail_size

    def get_order_mode(self) -> Literal["manual", "sorted"]:
        """Get current order mode.

        Returns:
            Current order mode
        """
        return self._model.order_mode

    def _on_model_layout_changed(self) -> None:
        """Handle model layout changes (e.g., after drag reorder).

        Save manual order to DB if in manual mode.
        """
        if self._model.order_mode == "manual":
            self._model.save_manual_order()
            self.files_reordered.emit()
            logger.debug("[ThumbnailViewport] Manual order saved to DB")

    def _on_thumbnail_ready(self, file_path: str, pixmap: "QPixmap") -> None:
        """Handle thumbnail_ready signal from ThumbnailManager.

        Updates the view to show the newly loaded thumbnail.

        Args:
            file_path: Absolute path to file
            pixmap: Loaded thumbnail pixmap
        """
        # Find the row for this file
        for row, file_item in enumerate(self._model.files):
            if file_item.full_path == file_path:
                # Update the view for this item
                index = self._model.index(row, 0)
                self._list_view.update(index)
                logger.debug("[ThumbnailViewport] Updated thumbnail for %s", file_path)
                break
