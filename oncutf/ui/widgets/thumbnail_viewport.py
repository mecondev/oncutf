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
from oncutf.ui.helpers.placeholder_helper import create_placeholder_helper
from oncutf.ui.helpers.tooltip_helper import TooltipHelper, TooltipType
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import cancel_timer

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
    selection_changed = pyqtSignal(list)  # Emitted with list[int] of selected rows

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

        # Thumbnail loading progress
        self._thumbnail_progress: tuple[int, int] | None = None  # (completed, total)

        # Tooltip state
        self._tooltip_timer_id: int | None = None
        self._tooltip_index: QModelIndex | None = None

        self._setup_ui()
        self._connect_signals()

        logger.info(
            "[ThumbnailViewport] Initialized with thumbnail size: %d",
            self._thumbnail_size,
        )

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        from oncutf.ui.theme_manager import get_theme_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create QListView in IconMode
        self._list_view = QListView(self)
        self._list_view.setViewMode(QListView.IconMode)
        self._list_view.setResizeMode(QListView.Adjust)
        self._list_view.setSpacing(16)
        self._list_view.setUniformItemSizes(True)  # Performance optimization
        self._list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list_view.setMovement(QListView.Free)  # Allow drag rearrange

        # Apply styling from theme to match FileTable appearance
        theme = get_theme_manager()
        bg_color = theme.get_color("table_background")
        border_color = theme.get_color("border")
        self._list_view.setStyleSheet(f"""
            QListView {{
                border: 1px solid {border_color};
                background-color: {bg_color};
            }}
        """)

        # Set model
        self._list_view.setModel(self._model)

        # Install event filter for tooltips
        self._list_view.viewport().installEventFilter(self)

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

        # Create status bar at the bottom
        self._status_bar = self._create_status_bar()
        layout.addWidget(self._status_bar)

        # Setup placeholder for empty state
        # Note: Parent is self._list_view since placeholder_helper uses viewport()
        self.placeholder_helper = create_placeholder_helper(
            self._list_view, "thumbnail_viewport", text="No files loaded", icon_size=160
        )
        # Show placeholder initially if model is empty
        self._update_placeholder_visibility()

    def _create_status_bar(self) -> QWidget:
        """Create the status bar widget with zoom icons and slider.

        Returns:
            QWidget containing status label and zoom controls

        """
        from pathlib import Path

        from PyQt5.QtGui import QIcon, QPixmap
        from PyQt5.QtWidgets import QHBoxLayout, QLabel, QSlider, QToolButton

        from oncutf.ui.theme_manager import get_theme_manager

        status_widget = QWidget(self)
        status_widget.setFixedHeight(28)  # Small height as requested

        # Apply theme styling
        theme = get_theme_manager()
        bg_color = theme.get_color("table_background")
        border_color = theme.get_color("border")
        text_color = theme.get_color("text")
        status_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border-top: 1px solid {border_color};
            }}
            QLabel {{
                color: {text_color};
                padding: 0px 8px;
            }}
        """)

        layout = QHBoxLayout(status_widget)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        # Status label (left side)
        self._status_label = QLabel("Ready")
        layout.addWidget(self._status_label)

        # Spacer
        layout.addStretch()

        # Icon path for landscape icon
        icon_path = (
            Path(__file__).parent.parent.parent
            / "resources"
            / "icons"
            / "utilities"
            / "landscape.svg"
        )

        # Zoom out icon (small landscape)
        zoom_out_btn = QToolButton()
        zoom_out_btn.setFixedSize(16, 16)
        zoom_out_btn.setIcon(QIcon(str(icon_path)))
        zoom_out_btn.setIconSize(QSize(12, 12))
        zoom_out_btn.setToolTip("Zoom out")
        zoom_out_btn.clicked.connect(self.zoom_out)
        zoom_out_btn.setStyleSheet("QToolButton { border: none; background: transparent; }")
        layout.addWidget(zoom_out_btn)

        # Zoom slider (center)
        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setMinimum(self.MIN_THUMBNAIL_SIZE)
        self._zoom_slider.setMaximum(self.MAX_THUMBNAIL_SIZE)
        self._zoom_slider.setValue(self._thumbnail_size)
        self._zoom_slider.setSingleStep(self.ZOOM_STEP)
        self._zoom_slider.setPageStep(self.ZOOM_STEP * 2)
        self._zoom_slider.setFixedWidth(120)
        self._zoom_slider.setToolTip(f"Zoom: {self._thumbnail_size}px")

        # Connect slider to zoom change
        self._zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)

        layout.addWidget(self._zoom_slider)

        # Zoom in icon (large landscape)
        zoom_in_btn = QToolButton()
        zoom_in_btn.setFixedSize(20, 20)
        zoom_in_btn.setIcon(QIcon(str(icon_path)))
        zoom_in_btn.setIconSize(QSize(18, 18))
        zoom_in_btn.setToolTip("Zoom in")
        zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_in_btn.setStyleSheet("QToolButton { border: none; background: transparent; }")
        layout.addWidget(zoom_in_btn)

        return status_widget

    def _on_zoom_slider_changed(self, value: int) -> None:
        """Handle zoom slider value change.

        Args:
            value: New slider value (thumbnail size)

        """
        # Round to nearest ZOOM_STEP
        rounded_value = round(value / self.ZOOM_STEP) * self.ZOOM_STEP
        if rounded_value != value:
            self._zoom_slider.setValue(rounded_value)
            return

        # Update thumbnail size
        self.set_thumbnail_size(rounded_value)

        # Update tooltip
        self._zoom_slider.setToolTip(f"Zoom: {rounded_value}px")
        self._update_placeholder_visibility()

    def _connect_signals(self) -> None:
        """Connect Qt signals."""
        # Double-click activation
        self._list_view.doubleClicked.connect(self._on_item_activated)

        # Context menu
        self._list_view.customContextMenuRequested.connect(self._on_context_menu)

        # Model changes (for manual order save and placeholder visibility)
        self._model.layoutChanged.connect(self._on_model_layout_changed)
        self._model.rowsInserted.connect(self._update_placeholder_visibility)
        self._model.rowsRemoved.connect(self._update_placeholder_visibility)
        self._model.modelReset.connect(self._update_placeholder_visibility)

        # Model data changes (for metadata/hash indicator updates)
        self._model.dataChanged.connect(self._on_model_data_changed)

        # Selection changes - emit for rename preview sync
        self._list_view.selectionModel().selectionChanged.connect(self._on_selection_changed)

        # Connect thumbnail_ready signal from ThumbnailManager
        try:
            from oncutf.ui.adapters.qt_app_context import QtAppContext

            context = QtAppContext.get_instance()
            if context and context.has_manager("thumbnail"):
                thumbnail_manager = context.get_manager("thumbnail")
                thumbnail_manager.thumbnail_ready.connect(self._on_thumbnail_ready)
                thumbnail_manager.generation_progress.connect(self._on_thumbnail_progress)
                logger.debug("[ThumbnailViewport] Connected to thumbnail signals")
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

            # Update zoom slider if it exists (without triggering valueChanged signal)
            if hasattr(self, "_zoom_slider"):
                self._zoom_slider.blockSignals(True)
                self._zoom_slider.setValue(size)
                self._zoom_slider.setToolTip(f"Zoom: {size}px")
                self._zoom_slider.blockSignals(False)

            # Update status label
            if hasattr(self, "_status_label"):
                self._update_status_label()

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

            # Right-click should NOT select items (only show context menu)
            if event.button() == Qt.RightButton:
                # Don't change selection on right-click
                return False  # Let context menu handler deal with it

            # Lasso selection (left button on empty space)
            if event.button() == Qt.LeftButton:
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
            if self._rubber_band and self._rubber_band.isVisible() and self._rubber_band_origin:
                # Update rubber band geometry
                self._rubber_band.setGeometry(
                    QRect(self._rubber_band_origin, event.pos()).normalized()
                )

                # Calculate intersecting items
                self._update_lasso_selection()
                return True

            # Handle hover for tooltips (when not panning or lasso selecting)
            if not self._is_panning:
                index = self._list_view.indexAt(event.pos())
                if index.isValid() and index != self._tooltip_index:
                    # New item hovered
                    self._cancel_tooltip()
                    self._tooltip_index = index
                    self._schedule_tooltip()
                elif not index.isValid() and self._tooltip_index:
                    # Left item area
                    self._cancel_tooltip()

        elif event_type == QEvent.MouseButtonRelease:
            # End pan
            if event.button() == Qt.MiddleButton and self._is_panning:
                self._is_panning = False
                self._pan_start_pos = None
                self._list_view.viewport().setCursor(Qt.ArrowCursor)
                return True

            # End lasso
            if (
                event.button() == Qt.LeftButton
                and self._rubber_band
                and self._rubber_band.isVisible()
            ):
                self._rubber_band.hide()
                self._rubber_band_origin = None
                return False  # Let QListView handle the release

        elif event_type == QEvent.Leave:
            # Clear tooltip when mouse leaves viewport
            self._cancel_tooltip()

        return super().eventFilter(obj, event)

    def _update_lasso_selection(self) -> None:
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

    def _on_item_activated(self, index: "QModelIndex") -> None:
        """Handle double-click on thumbnail.

        Args:
            index: Clicked model index

        """
        file_item = index.data(Qt.UserRole)
        if file_item:
            self.file_activated.emit(file_item.full_path)
            logger.debug("[ThumbnailViewport] File activated: %s", file_item.filename)

    def _on_selection_changed(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        """Handle selection change in thumbnail view.

        Emits selection_changed signal for rename preview sync.

        Args:
            selected: Newly selected items
            deselected: Newly deselected items

        """
        # Get all selected rows
        selection_model = self._list_view.selectionModel()
        if not selection_model:
            return

        selected_indexes = selection_model.selectedIndexes()
        selected_rows = sorted({index.row() for index in selected_indexes})

        # Update status label
        self._update_status_label()

        # Emit signal for rename preview and other listeners
        self.selection_changed.emit(selected_rows)
        logger.debug(
            "[ThumbnailViewport] Selection changed: %d items selected",
            len(selected_rows),
            extra={"dev_only": True},
        )

    def _on_context_menu(self, position: QPoint) -> None:
        """Show context menu for thumbnail operations.

        Uses unified context menu handler (same as file table).

        Args:
            position: Click position in widget coordinates

        """
        # Use unified context menu handler from parent window
        if hasattr(self, "_parent_window") and self._parent_window:
            try:
                # Delegate to the same handler used by file table
                self._parent_window.handle_table_context_menu(position)
            except Exception as e:
                logger.warning("Error showing unified context menu: %s", e)
                # Fallback to simplified menu if unified handler fails
                self._show_fallback_context_menu(position)
        else:
            # No parent window - use fallback
            self._show_fallback_context_menu(position)

    def _show_fallback_context_menu(self, position: QPoint) -> None:
        """Show fallback context menu if unified handler not available.

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
            action = menu.addAction("Manual Order Active")
            action.setEnabled(False)

        menu.addSeparator()

        # Zoom controls
        menu.addAction("Zoom In", self.zoom_in)
        menu.addAction("Zoom Out", self.zoom_out)
        menu.addAction("Reset Zoom", self.reset_zoom)

        menu.addSeparator()

        # File operations
        selected_files = self.get_selected_files()
        if selected_files:
            if len(selected_files) == 1:
                menu.addAction("Open File", self._open_file)
                menu.addAction("Reveal in File Manager", self._reveal_in_file_manager)
            menu.addAction(
                f"Open Folder ({len(selected_files)} file(s) selected)",
                self._open_file_location,
            )
        else:
            action = menu.addAction("No files selected")
            action.setEnabled(False)

        menu.addSeparator()
        menu.addAction("Refresh", self._refresh)

        # Show menu
        menu.exec_(self._list_view.viewport().mapToGlobal(position))

    def _on_thumbnail_progress(self, completed: int, total: int) -> None:
        """Handle thumbnail loading progress updates.

        Args:
            completed: Number of thumbnails loaded
            total: Total number of thumbnails to load

        """
        self._thumbnail_progress = (completed, total)
        self._update_status_label()

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

    def _open_file(self) -> None:
        """Open selected file with default application."""
        from pathlib import Path

        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices

        selected_files = self.get_selected_files()
        if not selected_files:
            logger.warning("[ThumbnailViewport] No file selected for opening")
            return

        file_path = selected_files[0]
        if not Path(file_path).exists():
            logger.error("[ThumbnailViewport] File does not exist: %s", file_path)
            return

        success = QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        if success:
            logger.info("[ThumbnailViewport] Opened file: %s", file_path)
        else:
            logger.error("[ThumbnailViewport] Failed to open file: %s", file_path)

    def _reveal_in_file_manager(self) -> None:
        """Reveal selected file in system file manager."""
        import platform
        import subprocess
        from pathlib import Path

        selected_files = self.get_selected_files()
        if not selected_files:
            logger.warning("[ThumbnailViewport] No file selected for revealing")
            return

        file_path = Path(selected_files[0])
        if not file_path.exists():
            logger.error("[ThumbnailViewport] File does not exist: %s", file_path)
            return

        system = platform.system()
        try:
            if system == "Windows":
                subprocess.run(["explorer", "/select,", str(file_path)], check=False)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", "-R", str(file_path)], check=False)
            else:  # Linux and others
                # Open the containing folder (most file managers don't support reveal)
                folder_path = file_path.parent
                subprocess.run(["xdg-open", str(folder_path)], check=False)

            logger.info("[ThumbnailViewport] Revealed file: %s", file_path)
        except Exception:
            logger.exception("[ThumbnailViewport] Failed to reveal file")

    def _open_file_location(self) -> None:
        """Open containing folder of selected file(s)."""
        from pathlib import Path

        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices

        selected_files = self.get_selected_files()
        if not selected_files:
            logger.warning("[ThumbnailViewport] No files selected for folder opening")
            return

        # Get folder from first selected file
        folder_path = Path(selected_files[0]).parent
        if not folder_path.exists():
            logger.error("[ThumbnailViewport] Folder does not exist: %s", folder_path)
            return

        success = QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder_path)))
        if success:
            logger.info("[ThumbnailViewport] Opened folder: %s", folder_path)
        else:
            logger.error("[ThumbnailViewport] Failed to open folder: %s", folder_path)

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

    def selection_model(self) -> QItemSelectionModel | None:
        """Get the selection model for this viewport.

        Used for integration with table_manager to get selected files
        from the currently active viewport.

        Returns:
            QItemSelectionModel or None if not available

        """
        return self._list_view.selectionModel()

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

        # Update placeholder visibility and status label after layout changes
        self._update_placeholder_visibility()
        self._update_status_label()

    def _update_status_label(self) -> None:
        """Update the status label with thumbnail loading progress.

        Thread-safe: checks if widget exists and is valid before updating.
        """
        if not hasattr(self, "_status_label") or not self._status_label:
            return

        # Additional safety check - ensure widget hasn't been deleted
        try:
            from PyQt5.sip import isdeleted

            if isdeleted(self._status_label):
                return
        except (ImportError, RuntimeError):
            pass

        try:
            # Show thumbnail loading progress if available
            if hasattr(self, "_thumbnail_progress") and self._thumbnail_progress:
                completed, total = self._thumbnail_progress
                if completed < total:
                    status_text = f"Loading thumbnails: {completed}/{total}"
                else:
                    status_text = "Ready"
            else:
                status_text = "Ready"

            self._status_label.setText(status_text)
        except (RuntimeError, AttributeError) as e:
            # Widget was deleted or model is invalid - silently ignore
            logger.debug(
                "[ThumbnailViewport] Could not update status label: %s",
                e,
                extra={"dev_only": True},
            )

    def _update_placeholder_visibility(self) -> None:
        """Update placeholder visibility based on model row count."""
        if not hasattr(self, "placeholder_helper"):
            return

        row_count = self._model.rowCount()
        if row_count == 0:
            # Clear pending thumbnail requests when model is empty
            self._clear_pending_thumbnail_requests()

            self.placeholder_helper.show()
            # Center the placeholder after showing
            self.placeholder_helper.update_position()
            logger.debug("[ThumbnailViewport] Showing placeholder (no files)")
        else:
            self.placeholder_helper.hide()
            logger.debug("[ThumbnailViewport] Hiding placeholder (%d files)", row_count)

        # Update status label
        self._update_status_label()

    def _clear_pending_thumbnail_requests(self) -> None:
        """Clear pending thumbnail requests from ThumbnailManager.

        Called when files are cleared to prevent stale thumbnail updates.
        """
        try:
            from oncutf.ui.adapters.qt_app_context import QtAppContext

            context = QtAppContext.get_instance()
            if context and context.has_manager("thumbnail"):
                thumbnail_manager = context.get_manager("thumbnail")
                thumbnail_manager.clear_pending_requests()
        except Exception as e:
            logger.debug("[ThumbnailViewport] Could not clear pending requests: %s", e)

    def resizeEvent(self, event) -> None:
        """Handle resize events - update placeholder position."""
        super().resizeEvent(event)
        if hasattr(self, "placeholder_helper"):
            self.placeholder_helper.update_position()

    def _on_thumbnail_ready(self, file_path: str, pixmap: "QPixmap") -> None:
        """Handle thumbnail_ready signal from ThumbnailManager.

        Updates the view to show the newly loaded thumbnail.

        Args:
            file_path: Absolute path to file
            pixmap: Loaded thumbnail pixmap

        """
        # Check if model still has files (may have been cleared)
        if not self._model or not self._model.files:
            return

        logger.debug(
            "[ThumbnailViewport] thumbnail_ready signal received: %s (pixmap valid=%s)",
            file_path,
            not pixmap.isNull(),
        )
        # Find the row for this file
        for row, file_item in enumerate(self._model.files):
            if file_item.full_path == file_path:
                # Update the view for this item
                index = self._model.index(row, 0)
                self._list_view.update(index)
                logger.debug(
                    "[ThumbnailViewport] Updated view for row=%d, file=%s",
                    row,
                    file_path,
                )
                return
        # File not in model - likely cleared while thumbnails were loading (expected behavior)
        # No warning needed as this is a normal race condition during clear operations

    def _on_model_data_changed(
        self, top_left: "QModelIndex", bottom_right: "QModelIndex", roles: list[int] | None = None
    ) -> None:
        """Handle model data changes (e.g., metadata/hash status updates).

        Updates the view for changed items to reflect new indicator states.

        Args:
            top_left: Top-left index of changed range
            bottom_right: Bottom-right index of changed range
            roles: List of changed roles (optional)

        """
        # Update all items in the changed range
        for row in range(top_left.row(), bottom_right.row() + 1):
            index = self._model.index(row, 0)
            if index.isValid():
                self._list_view.update(index)

        logger.debug(
            "[ThumbnailViewport] Updated %d items after model data change",
            bottom_right.row() - top_left.row() + 1,
            extra={"dev_only": True},
        )

    # ========== Tooltip Helpers ==========

    def _schedule_tooltip(self) -> None:
        """Schedule tooltip display after hover delay."""
        from oncutf.utils.shared.timer_manager import schedule_dialog_close

        if self._tooltip_timer_id:
            cancel_timer(self._tooltip_timer_id)

        # Use schedule_dialog_close for consistent tooltip delay (default 500ms)
        self._tooltip_timer_id = schedule_dialog_close(self._show_tooltip)

    def _cancel_tooltip(self) -> None:
        """Cancel pending tooltip and clear active tooltip."""
        if self._tooltip_timer_id:
            cancel_timer(self._tooltip_timer_id)
            self._tooltip_timer_id = None

        TooltipHelper.clear_tooltips_for_widget(self._list_view.viewport())
        self._tooltip_index = None

    def _show_tooltip(self) -> None:
        """Show tooltip for currently hovered item."""
        if not self._tooltip_index or not self._tooltip_index.isValid():
            return

        file_item = self._tooltip_index.data(Qt.UserRole)
        if not file_item:
            return

        # Build tooltip text
        tooltip_lines = [
            f"<b>{file_item.filename}</b>",
            f"Type: {file_item.extension.upper() if file_item.extension else 'Unknown'}",
        ]

        # Add metadata if available
        if hasattr(file_item, "duration") and file_item.duration:
            tooltip_lines.append(f"Duration: {file_item.duration}")
        if hasattr(file_item, "image_size") and file_item.image_size:
            tooltip_lines.append(f"Size: {file_item.image_size}")
        if file_item.color and file_item.color.lower() != "none":
            tooltip_lines.append(f"Color: {file_item.color}")

        tooltip_text = "<br>".join(tooltip_lines)

        from oncutf.config import TOOLTIP_DURATION

        TooltipHelper.show_tooltip(
            self._list_view.viewport(),
            tooltip_text,
            TooltipType.INFO,
            duration=TOOLTIP_DURATION,
            persistent=False,
        )
