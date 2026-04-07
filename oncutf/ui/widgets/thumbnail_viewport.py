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
    QTimer,
    pyqtSignal,
)
from PyQt5.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
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
from oncutf.utils.shared.timer_manager import cancel_timer, schedule_ui_update

if TYPE_CHECKING:
    from PyQt5.QtCore import QModelIndex
    from PyQt5.QtGui import QPixmap

    from oncutf.models.file_table.file_table_model import FileTableModel

logger = get_cached_logger(__name__)


class ThumbnailListView(QListView):
    """Custom QListView for thumbnail grid that handles drop events properly.

    This subclass ensures drop events are properly processed and provides
    access to the parent ThumbnailViewportWidget for drop handling.
    """

    def __init__(self, parent: "ThumbnailViewportWidget | None" = None):
        """Initialize thumbnail list view.

        Args:
            parent: Parent ThumbnailViewportWidget

        """
        super().__init__(parent)
        self._parent_viewport = parent

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event."""
        logger.debug(
            "[ThumbnailListView] dragEnterEvent called - delegating to parent",
            extra={"dev_only": True},
        )
        if self._parent_viewport:
            self._parent_viewport.dragEnterEvent(event)
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """Handle drag move event."""
        logger.debug(
            "[ThumbnailListView] dragMoveEvent called - delegating to parent",
            extra={"dev_only": True},
        )
        if self._parent_viewport:
            self._parent_viewport.dragMoveEvent(event)
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event."""
        logger.debug(
            "[ThumbnailListView] dropEvent called on list view - delegating to parent",
            extra={"dev_only": True},
        )
        if self._parent_viewport:
            self._parent_viewport.dropEvent(event)
        else:
            super().dropEvent(event)


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
    files_dropped = pyqtSignal(list, object)  # Emitted with dropped paths and modifiers

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

        # Get ThumbnailManager for controller
        thumbnail_manager = None
        try:
            from oncutf.ui.adapters.qt_app_context import QtAppContext

            context = QtAppContext.get_instance()
            if context and context.has_manager("thumbnail"):
                thumbnail_manager = context.get_manager("thumbnail")
        except Exception as e:
            logger.warning("[ThumbnailViewport] Could not get ThumbnailManager: %s", e)

        # Initialize controller for backend operations
        from oncutf.controllers.thumbnail_viewport_controller import (
            ThumbnailViewportController,
        )

        self._controller = ThumbnailViewportController(
            model=model, thumbnail_manager=thumbnail_manager, parent=self
        )

        # Thumbnail loading progress
        self._thumbnail_progress: tuple[int, int] | None = None  # (completed, total)
        # Track the row count of the last file-set that triggered a full load reset.
        # _update_placeholder_visibility uses this to avoid resetting counters on
        # layout changes / scroll activity that don't change the actual file set.
        self._loaded_file_count: int = -1

        # Scroll optimization - debouncing and range tracking
        self._scroll_debounce_timer = QTimer()
        self._scroll_debounce_timer.setSingleShot(True)
        self._scroll_debounce_timer.setInterval(150)  # 150ms debounce
        self._scroll_debounce_timer.timeout.connect(self._process_scroll_change)
        self._last_visible_range: set[str] | None = None  # Track visible file paths

        # Context menu state - prevent re-triggering while menu is open
        self._context_menu_open = False

        # Behaviors (initialized in _setup_ui after widgets are created)
        self._zoom_behavior = None
        self._pan_behavior = None
        self._lasso_behavior = None
        self._tooltip_behavior = None
        self._drag_drop_behavior = None

        # Drag-drop state
        self._loading_in_progress = False

        # Spinner state for loading animation
        self._spinner_base_pixmap: QPixmap | None = None
        self._spinner_angle: float = 0.0
        self._spinner_timer = QTimer()
        self._spinner_timer.setInterval(30)
        self._spinner_timer.timeout.connect(self._spin_tick)

        self._setup_ui()
        self._connect_signals()

        logger.info(
            "[ThumbnailViewport] Initialized with thumbnail size: %d",
            self._zoom_behavior.get_current_size(),
        )

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        from oncutf.ui.behaviors.thumbnail_viewport_lasso_behavior import (
            ThumbnailViewportLassoBehavior,
        )
        from oncutf.ui.behaviors.thumbnail_viewport_pan_behavior import (
            ThumbnailViewportPanBehavior,
        )
        from oncutf.ui.behaviors.thumbnail_viewport_tooltip_behavior import (
            ThumbnailViewportTooltipBehavior,
        )
        from oncutf.ui.behaviors.thumbnail_viewport_zoom_behavior import (
            ThumbnailViewportZoomBehavior,
        )
        from oncutf.ui.theme_manager import get_theme_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create custom ThumbnailListView with proper drop event handling
        self._list_view = ThumbnailListView(parent=self)
        self._list_view.setViewMode(QListView.IconMode)
        self._list_view.setResizeMode(QListView.Adjust)
        self._list_view.setSpacing(16)
        self._list_view.setUniformItemSizes(True)  # Performance optimization
        self._list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list_view.setMovement(QListView.Free)  # Allow drag rearrange
        self._list_view.setAcceptDrops(True)  # Enable drop acceptance

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

        # Create and set delegate
        self._delegate = ThumbnailDelegate(self._list_view)
        self._list_view.setItemDelegate(self._delegate)

        # Initialize behaviors
        self._zoom_behavior = ThumbnailViewportZoomBehavior(
            list_view=self._list_view,
            delegate=self._delegate,
            zoom_slider=None,  # Will be set after status bar creation
            status_update_callback=self._update_status_label,
        )

        self._pan_behavior = ThumbnailViewportPanBehavior(list_view=self._list_view)

        self._lasso_behavior = ThumbnailViewportLassoBehavior(
            list_view=self._list_view, model=self._model
        )

        self._tooltip_behavior = ThumbnailViewportTooltipBehavior(list_view=self._list_view)

        # Initialize drag-drop behavior (will use self as DraggableWidget)
        from oncutf.ui.behaviors.drag_drop_behavior import DragDropBehavior

        self._drag_drop_behavior = DragDropBehavior(widget=self)

        # Install event filter for behaviors
        self._list_view.viewport().installEventFilter(self)

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
        handle = theme.get_color("scrollbar_handle")
        handle_hover = theme.get_color("button_hover_bg")
        handle_pressed = theme.get_color("button_pressed_bg")
        status_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border: none;
            }}
            QLabel {{
                color: {text_color};
                padding: 0px 8px;
                border: none;
            }}
            QLabel#spinner {{
                padding: 0px;
                background: transparent;
            }}
            QLabel#status_text {{
                padding: 0px 8px 0px 0px;
            }}
            QSlider {{
                background: transparent;
            }}
            QSlider::groove:horizontal {{
                background: {bg_color};
                height: 12px;
                border-radius: 2px;
                border: none;
            }}
            QSlider::sub-page:horizontal {{
                background: {border_color};
                margin: 5px 0;
                border-radius: 2px;
            }}
            QSlider::add-page:horizontal {{
                background: {border_color};
                margin: 5px 0;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {handle};
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
                border: none;
            }}
            QSlider::handle:horizontal:hover {{
                background: {handle_hover};
            }}
            QSlider::handle:horizontal:pressed {{
                background: {handle_pressed};
            }}
        """)

        layout = QHBoxLayout(status_widget)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        # Spinner icon (shown during thumbnail loading)
        from oncutf.ui.helpers.icons_loader import icons_loader as _il

        self._spinner_label = QLabel()
        self._spinner_label.setObjectName("spinner")
        self._spinner_label.setFixedSize(14, 14)
        self._spinner_label.setVisible(False)
        spinner_pixmap = _il.load_pixmap("progress_activity", 14)
        if not spinner_pixmap.isNull():
            self._spinner_base_pixmap = spinner_pixmap
            self._spinner_label.setPixmap(self._spinner_base_pixmap)
        layout.addWidget(self._spinner_label)

        # Status label (left side)
        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("status_text")
        layout.addWidget(self._status_label)

        # Spacer
        layout.addStretch()

        # Get theme-aware landscape icon
        from oncutf.ui.helpers.icons_loader import icons_loader

        landscape_icon = icons_loader.load_icon("landscape")

        # Zoom out icon (small landscape)
        zoom_out_btn = QToolButton()
        zoom_out_btn.setFixedSize(18, 18)
        zoom_out_btn.setIcon(landscape_icon)
        zoom_out_btn.setIconSize(QSize(12, 12))
        zoom_out_btn.setToolTip("Zoom out")
        zoom_out_btn.clicked.connect(self.zoom_out)
        zoom_out_btn.setStyleSheet(
            "QToolButton { border: none; background: transparent; }"
            "QToolButton:hover { background: transparent; }"
            "QToolButton:pressed { background: transparent; }"
            "QToolButton:checked { background: transparent; }"
        )
        layout.addWidget(zoom_out_btn)

        # Zoom slider (center)
        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setMinimum(self._zoom_behavior.MIN_SIZE)
        self._zoom_slider.setMaximum(self._zoom_behavior.MAX_SIZE)
        self._zoom_slider.setValue(self._zoom_behavior.get_current_size())
        self._zoom_slider.setSingleStep(self._zoom_behavior.STEP)
        self._zoom_slider.setPageStep(self._zoom_behavior.STEP * 2)
        self._zoom_slider.setFixedWidth(120)
        self._zoom_slider.setToolTip(f"Zoom: {self._zoom_behavior.get_current_size()}px")

        # Connect slider to zoom change
        self._zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)

        # Update zoom behavior with slider reference
        self._zoom_behavior._zoom_slider = self._zoom_slider

        layout.addWidget(self._zoom_slider)

        # Zoom in icon (large landscape)
        zoom_in_btn = QToolButton()
        zoom_in_btn.setFixedSize(20, 20)
        zoom_in_btn.setIcon(landscape_icon)
        zoom_in_btn.setIconSize(QSize(18, 18))
        zoom_in_btn.setToolTip("Zoom in")
        zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_in_btn.setStyleSheet(
            "QToolButton { border: none; background: transparent; }"
            "QToolButton:hover { background: transparent; }"
            "QToolButton:pressed { background: transparent; }"
            "QToolButton:checked { background: transparent; }"
        )
        layout.addWidget(zoom_in_btn)

        return status_widget

    def _on_zoom_slider_changed(self, value: int) -> None:
        """Handle zoom slider value change.

        Args:
            value: New slider value (thumbnail size)

        """
        # Round to nearest ZOOM_STEP
        rounded_value = round(value / self._zoom_behavior.STEP) * self._zoom_behavior.STEP
        if rounded_value != value:
            self._zoom_slider.setValue(rounded_value)
            return

        # Update thumbnail size via behavior
        self._zoom_behavior.set_size(rounded_value)

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
        self._model.modelReset.connect(self._on_model_reset)

        # Model data changes (for metadata/hash indicator updates)
        self._model.dataChanged.connect(self._on_model_data_changed)

        # Selection changes - emit for rename preview sync
        self._list_view.selectionModel().selectionChanged.connect(self._on_selection_changed)

        # Viewport scroll changes - prioritize visible thumbnails
        v_scrollbar = self._list_view.verticalScrollBar()
        v_scrollbar.valueChanged.connect(self._on_viewport_scrolled)

        # Connect controller signals for thumbnail updates
        self._controller.thumbnail_ready.connect(self._on_thumbnail_ready)
        self._controller.thumbnail_progress.connect(self._on_thumbnail_progress)
        self._controller.viewport_mode_changed.connect(
            lambda mode: self.viewport_mode_changed.emit(mode)
        )
        self._controller.files_reordered.connect(lambda: self.files_reordered.emit())

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
        self._zoom_behavior.set_size(size)

    def zoom_in(self) -> None:
        """Increase thumbnail size by ZOOM_STEP."""
        self._zoom_behavior.zoom_in()

    def zoom_out(self) -> None:
        """Decrease thumbnail size by ZOOM_STEP."""
        self._zoom_behavior.zoom_out()

    def reset_zoom(self) -> None:
        """Reset thumbnail size to default."""
        self._zoom_behavior.reset()

    def sort_by(self, key: str, reverse: bool) -> None:
        """Public sort entry point for context menu actions."""
        self._controller.sort_by(key, reverse=reverse)

    def return_to_manual_order(self) -> None:
        """Return to manual order mode and load from DB."""
        self._controller.return_to_manual_order()

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        """Event filter delegating to behaviors.

        Args:
            obj: Watched object (viewport)
            event: Event

        Returns:
            True if event handled, False otherwise

        """
        if obj != self._list_view.viewport():
            return super().eventFilter(obj, event)

        event_type = event.type()

        # Right-click on empty space should NOT clear selection
        if event_type == QEvent.MouseButtonPress and event.button() == Qt.RightButton:
            # Check if click is on empty space
            index = self._list_view.indexAt(event.pos())
            if not index.isValid():
                # Emit context menu signal manually (since we're consuming the event)
                self._list_view.customContextMenuRequested.emit(event.pos())
                return True  # Consume event to prevent selection clear
            return False  # On item - let QListView handle it normally

        # Delegate to behaviors in priority order:
        # 1. Zoom behavior (Ctrl+Wheel)
        if self._zoom_behavior.handle_event_filter(obj, event):
            return True

        # 2. Pan behavior (middle mouse)
        if self._pan_behavior.handle_event_filter(obj, event):
            return True

        # 3. Lasso selection behavior (left mouse on empty space)
        if self._lasso_behavior.handle_event_filter(obj, event):
            return True

        # 4. Tooltip behavior (hover - doesn't consume events)
        self._tooltip_behavior.handle_event_filter(obj, event, self._pan_behavior.is_panning())

        return super().eventFilter(obj, event)

    # =====================================
    # Drag-and-Drop Event Handlers
    # =====================================

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event.

        Accepts drops from file explorer, file tree, and other file sources.

        Args:
            event: Qt drop event

        """
        if self._drag_drop_behavior.handle_drag_enter(event):
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """Handle drag move event.

        Args:
            event: Qt drop event

        """
        if self._drag_drop_behavior.handle_drag_move(event):
            return
        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event) -> None:
        """Handle drag leave event.

        Args:
            event: Qt drag leave event

        """
        if self._drag_drop_behavior.handle_drag_leave(event):
            return
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event.

        Processes dropped files/folders and emits files_dropped signal
        for the main window to load.

        Args:
            event: Qt drop event

        """
        from oncutf.ui.widgets.drag_cancel_handler import get_drag_cancel_handler
        from oncutf.ui.widgets.drag_overlay import DragOverlayManager
        from oncutf.utils.cursor_helper import wait_cursor

        logger.debug(
            "[ThumbnailViewport] dropEvent START",
            extra={"dev_only": True},
        )

        drag_cancel_handler = get_drag_cancel_handler()
        if drag_cancel_handler.was_cancelled():
            overlay_manager = DragOverlayManager.get_instance()
            overlay_manager.hide_overlay()
            event.ignore()
            drag_cancel_handler.deactivate()
            return

        # Set wait cursor for user feedback
        with wait_cursor(restore_after=False):
            QApplication.processEvents()

            try:
                logger.debug(
                    "[ThumbnailViewport] Calling handle_drop",
                    extra={"dev_only": True},
                )
                result = self._drag_drop_behavior.handle_drop(event)

                logger.debug(
                    "[ThumbnailViewport] handle_drop returned: %s",
                    result is not None,
                    extra={"dev_only": True},
                )

                if result:
                    # Suppress placeholder re-showing during streaming load
                    self._loading_in_progress = True

                    # Hide placeholder immediately
                    if hasattr(self, "placeholder_helper") and self.placeholder_helper:
                        self.placeholder_helper.hide()
                    self.update()

                    dropped_paths, modifiers = result
                    logger.info(
                        "[ThumbnailViewport] Emitting files_dropped with %d paths",
                        len(dropped_paths),
                        extra={"dev_only": True},
                    )
                    self.files_dropped.emit(dropped_paths, modifiers)
                else:
                    # Restore cursor if no valid drop
                    QApplication.restoreOverrideCursor()
                    logger.debug(
                        "[ThumbnailViewport] No valid drop",
                        extra={"dev_only": True},
                    )
            except Exception:
                QApplication.restoreOverrideCursor()
                logger.exception("[ThumbnailViewport] Error handling drop event")
                raise

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
        """Show unified context menu for thumbnail operations (same as file table).

        Uses the parent window's handle_table_context_menu handler.
        Protects selection from being cleared when dismissing menu with click.

        Args:
            position: Click position in widget coordinates

        """
        # Prevent re-triggering context menu while one is already open
        if self._context_menu_open:
            return

        self._context_menu_open = True

        # Temporarily disconnect the context menu signal to prevent re-triggering
        # when menu closes via ESC or outside click
        self._list_view.customContextMenuRequested.disconnect(self._on_context_menu)

        try:
            # Install menu dismiss guard to prevent selection loss
            from oncutf.ui.helpers.menu_dismiss_guard import MenuDismissGuard

            selection_model = self._list_view.selectionModel()
            if selection_model:
                saved_selection = selection_model.selection()
                guard = MenuDismissGuard.install(self._list_view, saved_selection)
            else:
                guard = None

            try:
                # Find parent window by walking up the widget hierarchy
                parent_window = None
                widget = self.parent()
                while widget and not parent_window:
                    if hasattr(widget, "handle_table_context_menu"):
                        parent_window = widget
                        break
                    widget = widget.parent()

                # Use unified context menu handler from parent window (same as file table)
                if parent_window:
                    parent_window.handle_table_context_menu(position, self._list_view)
                else:
                    logger.warning(
                        "Cannot show context menu: no parent window found",
                        extra={"dev_only": True},
                    )
            finally:
                # Remove guard after menu closes
                if guard:
                    guard.uninstall()
        finally:
            # Reconnect signal in next event loop iteration to avoid race conditions
            # when menu closes and generates events
            QTimer.singleShot(0, self._reconnect_context_menu_signal)

    def _reconnect_context_menu_signal(self) -> None:
        """Reconnect context menu signal after menu closes.

        Called via QTimer.singleShot to avoid race conditions.
        """
        try:
            self._list_view.customContextMenuRequested.connect(self._on_context_menu)
        except TypeError:
            # Already connected, ignore
            pass
        finally:
            self._context_menu_open = False

    def _on_thumbnail_progress(self, completed: int, total: int) -> None:
        """Handle thumbnail loading progress updates.

        Starts / stops the delegate shimmer animation based on loading state.

        Args:
            completed: Number of thumbnails loaded
            total: Total number of thumbnails to load

        """
        self._thumbnail_progress = (completed, total)
        self._update_status_label()
        # Stop shimmer when all thumbnails have been processed
        if total > 0 and completed >= total:
            self._delegate.stop_shimmer()

    def _spin_tick(self) -> None:
        """Advance spinner rotation by one step."""
        if not self._spinner_base_pixmap:
            return
        from PyQt5.QtGui import QPainter, QPixmap

        self._spinner_angle = (self._spinner_angle + 12.0) % 360.0
        size = self._spinner_base_pixmap.width()
        result = QPixmap(size, size)
        result.fill(Qt.transparent)
        painter = QPainter(result)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.translate(size / 2.0, size / 2.0)
        painter.rotate(self._spinner_angle)
        painter.translate(-size / 2.0, -size / 2.0)
        painter.drawPixmap(0, 0, self._spinner_base_pixmap)
        painter.end()
        try:
            self._spinner_label.setPixmap(result)
        except RuntimeError:
            self._spinner_timer.stop()

    def _set_spinner_visible(self, visible: bool) -> None:
        """Show or hide the loading spinner in the status bar."""
        try:
            if visible:
                if not self._spinner_timer.isActive():
                    self._spinner_timer.start()
                self._spinner_label.setVisible(True)
            else:
                self._spinner_timer.stop()
                self._spinner_label.setVisible(False)
        except RuntimeError:
            pass

    def _sort_by(self, key: str, reverse: bool) -> None:
        """Sort files by key and switch to sorted mode.

        Args:
            key: Sort key ("filename", "color", etc.)
            reverse: Reverse order

        """
        # Delegate to controller
        self._controller.sort_by(key, reverse=reverse)

    def _return_to_manual_order(self) -> None:
        """Return to manual order mode and load from DB."""
        # Delegate to controller
        self._controller.return_to_manual_order()

    def _open_file(self) -> None:
        """Open selected file with default application."""
        # Delegate to controller
        result = self._controller.open_selected_files(self._list_view.selectionModel())
        if not result["success"]:
            logger.warning("[ThumbnailViewport] Failed to open files: %s", result["errors"])

    def _reveal_in_file_manager(self) -> None:
        """Reveal selected file in system file manager."""
        # Delegate to controller
        result = self._controller.reveal_in_file_manager(self._list_view.selectionModel())
        if not result["success"]:
            logger.warning("[ThumbnailViewport] Failed to reveal files: %s", result["errors"])

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
        # Delegate to controller
        return self._controller.get_selected_file_paths(self._list_view.selectionModel())

    def select_files(self, file_paths: list[str]) -> None:
        """Select files by file paths (for sync with table view).

        Args:
            file_paths: List of file paths to select

        """
        # Delegate to controller
        self._controller.select_files_by_paths(file_paths, self._list_view.selectionModel())

    def clear_selection(self) -> None:
        """Clear all selections."""
        selection_model = self._list_view.selectionModel()
        if selection_model:
            selection_model.clearSelection()

    def sync_selection_from_rows(self, rows: set[int]) -> None:
        """Sync internal Qt selection model from an explicit set of row indices.

        Called when the SelectionStore is updated externally (e.g. from
        SelectionManager.clear_all_selection / invert_selection / select_all_rows).
        Blocks the selection model's own signals to prevent circular propagation
        back to SelectionStore.

        Args:
            rows: Set of row indices to mark as selected.

        """
        selection_model = self._list_view.selectionModel()
        model = self._list_view.model()
        if not selection_model or not model:
            return

        # Block the selection model's selectionChanged signal so that
        # _on_selection_changed does not fire and loop back to SelectionStore.
        selection_model.blockSignals(True)
        try:
            selection = QItemSelection()
            for row in sorted(rows):
                if 0 <= row < model.rowCount():
                    index = model.index(row, 0)
                    selection.select(index, index)
            selection_model.clearSelection()
            if not selection.isEmpty():
                selection_model.select(selection, QItemSelectionModel.Select)
        finally:
            selection_model.blockSignals(False)

        # Keep the status bar consistent without emitting signals
        self._update_status_label()

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
        return self._zoom_behavior.get_current_size()

    def get_order_mode(self) -> Literal["manual", "sorted"]:
        """Get current order mode.

        Returns:
            Current order mode

        """
        return self._model.order_mode

    @property
    def list_view(self) -> "ThumbnailListView":
        """Return the internal QListView for shortcut/focus registration."""
        return self._list_view

    def _on_model_reset(self) -> None:
        """Handle model reset signal (new file set loaded).

        Invalidates the loaded-file-count so that _update_placeholder_visibility
        always triggers a full reset + re-queue even if the new file count
        happens to be identical to the previous one.
        """
        self._loaded_file_count = -1
        self._update_placeholder_visibility()

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
        Shows total files from model, not just queued thumbnail requests.
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
            # Get total file count from model (not from thumbnail requests)
            total_files = self._model.rowCount() if self._model else 0
            is_loading = False

            # Show thumbnail loading progress if available
            if hasattr(self, "_thumbnail_progress") and self._thumbnail_progress:
                completed, _queued_total = self._thumbnail_progress
                # Use total_files from model, not queued count
                if completed < total_files and total_files > 0:
                    status_text = f"Loading thumbnails: {completed}/{total_files}"
                    is_loading = True
                else:
                    status_text = f"Ready ({total_files} files)" if total_files > 0 else "Ready"
            else:
                status_text = f"Ready ({total_files} files)" if total_files > 0 else "Ready"

            self._status_label.setText(status_text)
            if hasattr(self, "_spinner_label"):
                self._set_spinner_visible(is_loading)
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
            self._loaded_file_count = 0

            self.placeholder_helper.show()
            # Update position immediately (no delay for instant visibility)
            self.placeholder_helper.update_position()
            logger.debug("[ThumbnailViewport] Showing placeholder (no files)")
        else:
            self.placeholder_helper.hide()
            logger.debug("[ThumbnailViewport] Hiding placeholder (%d files)", row_count)

            if self._loaded_file_count <= 0:
                # Transitioning from empty / reset state to having files.
                # Clear pending requests first, then queue to find out how
                # many items actually need generation.
                self._loaded_file_count = row_count
                self._clear_pending_thumbnail_requests()
                queued = self._queue_all_thumbnails_for_background_loading()
                if queued > 0:
                    # Some items need loading -- reset animation state so
                    # incoming thumbnails crossfade in cleanly.
                    self._delegate.reset_for_new_files()
                # else: all cached -- keep existing _completed_fades intact
            elif row_count != self._loaded_file_count:
                # Incremental file-count change (streaming add / remove).
                # Do NOT reset delegate animation state or clear pending
                # requests -- that would wipe the progress counters and
                # _completed_fades built up during the current session.
                # Just update the count and queue any new items; the
                # controller's dedup logic skips already-queued files.
                self._loaded_file_count = row_count
                self._queue_all_thumbnails_for_background_loading()
            # else: same file count (layout change / scroll repaint) -- no reset

        # Update status label
        self._update_status_label()

    def _clear_pending_thumbnail_requests(self) -> None:
        """Clear pending thumbnail requests from ThumbnailManager.

        Called when files are cleared to prevent stale thumbnail updates.
        """
        # Delegate to controller
        self._controller.clear_pending_thumbnail_requests()

    def _queue_all_thumbnails_for_background_loading(self) -> int:
        """Queue all file thumbnails for background loading (priority=0).

        Called when files are loaded into the model. This ensures all thumbnails
        are generated in background, with visible viewport items prioritized via
        scroll tracking (implemented separately).

        Professional app behavior:
        - Load ALL thumbnails immediately when files are loaded
        - Visible items get priority=1 (loaded first)
        - Non-visible items get priority=0 (background loading)

        Returns:
            Number of items actually queued for generation (0 if all cached).

        """
        import time

        t0 = time.time()

        # Skip thumbnail loading if viewport is not visible (e.g., table view is active)
        if not self.isVisible():
            logger.debug(
                "[ThumbnailViewport] Skipping thumbnail loading - viewport not visible",
            )
            return 0

        # STEP 1: Prioritize visible thumbnails first (priority=1)
        visible_paths = self._get_visible_file_paths()
        logger.debug(
            "[THUMBS-QUEUE] _get_visible_file_paths at t=%.3fms, found %d",
            (time.time() - t0) * 1000,
            len(visible_paths),
        )
        if visible_paths:
            self._controller.prioritize_visible_thumbnails(visible_paths)
            logger.debug(
                "[ThumbnailViewport] Prioritized %d visible thumbnails on initial load",
                len(visible_paths),
            )

        # STEP 2: Queue all thumbnails for background loading (priority=0)
        # The ThumbnailManager will skip already-queued visible items
        queued_count = self._controller.queue_all_thumbnails(
            size_px=self._zoom_behavior.get_current_size()
        )

        # Only start shimmer if there are items actually being loaded.
        # On view switch (all cached), queued_count==0 so shimmer stays off
        # and already-completed fades are not re-triggered.
        if queued_count > 0:
            self._delegate.start_shimmer()

        # Always mark rows that already have a cached pixmap as completed
        # so the delegate's paint() state machine renders them directly
        # instead of showing a shimmer skeleton.  This is essential in
        # mixed scenarios (some cached, some not) and on view switch.
        self._mark_cached_rows_completed()

        logger.debug(
            "[THUMBS-QUEUE] Completed at t=%.3fms",
            (time.time() - t0) * 1000,
        )

        return queued_count

    def _mark_cached_rows_completed(self) -> None:
        """Pre-populate delegate's _completed_fades for rows with cached pixmaps.

        Checks the ThumbnailManager's cache directly (memory -> disk -> DB)
        instead of calling model.data(UserRole+1) which triggers
        get_thumbnail() and its side-effect of re-queuing uncached items.

        This is essential on view-switch (listview -> thumbsview) or reload
        when most/all thumbnails are already cached -- without this, the
        shimmer guard inside paint() would block rendering until a
        register_fade() call that never arrives for cached items.
        """
        manager = self._controller._thumbnail_manager
        if manager is None:
            return

        row_count = self._model.rowCount()
        for row in range(row_count):
            index = self._model.index(row, 0)
            file_item = index.data(Qt.UserRole)
            if file_item is None:
                continue
            cached = manager._check_cache(file_item.full_path, 128)
            if cached is not None:
                self._delegate.mark_row_completed(row)

    def _mark_visible_cached_rows_completed(self) -> None:
        """Mark cached rows as completed for currently visible items only.

        Lightweight version of _mark_cached_rows_completed() that only checks
        items in the current viewport. Called on scroll to fix stuck shimmer
        for cached thumbnails that scroll into view.
        """
        manager = self._controller._thumbnail_manager
        if manager is None:
            return

        viewport_rect = self._list_view.viewport().rect()
        if not viewport_rect.isValid():
            return

        row_count = self._model.rowCount()
        for row in range(row_count):
            # Skip already-completed rows
            if row in self._delegate._completed_fades:
                continue

            index = self._model.index(row, 0)
            item_rect = self._list_view.visualRect(index)

            if not viewport_rect.intersects(item_rect):
                continue

            file_item = index.data(Qt.UserRole)
            if file_item is None:
                continue

            cached = manager._check_cache(file_item.full_path, 128)
            if cached is not None:
                self._delegate.mark_row_completed(row)

    def _get_visible_file_paths(self) -> list[str]:
        """Get list of file paths for currently visible thumbnails.

        Optimized for performance:
        - Early exit if viewport invalid
        - Direct iteration over visible items only

        Returns:
            List of absolute file paths for visible items

        """
        if not self._list_view or not self._model:
            return []

        visible_paths = []
        viewport_rect = self._list_view.viewport().rect()

        # Early exit if viewport is invalid
        if not viewport_rect.isValid() or viewport_rect.isEmpty():
            return []

        row_count = self._model.rowCount()
        for row in range(row_count):
            index = self._model.index(row, 0)
            item_rect = self._list_view.visualRect(index)

            # Check if item intersects viewport
            if viewport_rect.intersects(item_rect):
                file_item = index.data(Qt.UserRole)
                if file_item:
                    visible_paths.append(file_item.full_path)

        return visible_paths

    def _on_viewport_scrolled(self) -> None:
        """Handle viewport scroll - debounced to avoid excessive re-queuing.

        Called on every scroll event. Uses a timer to debounce and only process
        scroll changes after 150ms of no scrolling activity.
        """
        # Skip if viewport is hidden (table view active)
        if not self.isVisible():
            return

        # Restart debounce timer (cancels previous timer if still running)
        self._scroll_debounce_timer.start()

    def _process_scroll_change(self) -> None:
        """Process scroll change after debounce delay.

        Always marks cached rows as completed for newly visible items to prevent
        stuck shimmer on items that are already in cache. Re-queues only when
        visible range has changed significantly (>50% new items).
        """
        visible_paths = self._get_visible_file_paths()
        if not visible_paths:
            return

        # Convert to set for efficient comparison
        visible_set = set(visible_paths)

        # ALWAYS mark cached rows completed for visible items.
        # This is the key fix for "stuck shimmer" after scroll -- cached items
        # that scroll into view need to be in _completed_fades or the paint()
        # state machine will draw shimmer forever.
        self._mark_visible_cached_rows_completed()

        # Check if visible range changed enough to warrant re-prioritizing
        if self._last_visible_range is not None:
            # Calculate overlap
            intersection = visible_set & self._last_visible_range
            union = visible_set | self._last_visible_range

            if union:
                overlap_ratio = len(intersection) / len(union)
                # If more than 80% overlap, skip re-queue (range hasn't changed much)
                if overlap_ratio > 0.80:
                    logger.debug(
                        "[ThumbnailViewport] Scroll range overlap %.1f%% - skipping re-queue",
                        overlap_ratio * 100,
                    )
                    return

        # Update tracked range
        self._last_visible_range = visible_set

        # Re-queue visible items with HIGH priority
        self._controller.prioritize_visible_thumbnails(visible_paths)
        logger.debug(
            "[ThumbnailViewport] Scroll processed - prioritized %d visible thumbnails",
            len(visible_paths),
        )

    def resizeEvent(self, event) -> None:
        """Handle resize events - update placeholder position."""
        super().resizeEvent(event)
        if hasattr(self, "placeholder_helper"):
            self.placeholder_helper.update_position()

    def showEvent(self, event) -> None:
        """Handle show events - switch to high priority loading."""
        import time

        t0 = time.time()
        super().showEvent(event)
        logger.debug("[THUMBS-SHOW] showEvent START at t=%.3fms", (time.time() - t0) * 1000)

        if hasattr(self, "placeholder_helper"):
            # Update position immediately (no delay for instant visibility)
            self.placeholder_helper.update_position()

        # Switch to HIGH priority mode when viewport becomes visible
        if hasattr(self, "_controller") and self._controller:
            self._controller.set_viewport_visible(True)

        row_count = self._model.rowCount()
        if row_count == 0:
            # No files -- ensure placeholder is visible
            if hasattr(self, "placeholder_helper"):
                self.placeholder_helper.show()
                self.placeholder_helper.update_position()
        else:
            # Has files -- ensure all thumbnails are queued.
            # Handles both: file count changed while hidden, AND viewport was
            # hidden when files were loaded (isVisible guard in
            # _queue_all_thumbnails_for_background_loading skipped queuing).
            # Controller dedup (_queued_files) prevents duplicate work.
            if row_count != self._loaded_file_count:
                logger.debug(
                    "[ThumbnailViewport] Viewport shown with %d files (loaded=%d)"
                    " - scheduling thumbnail queue",
                    row_count,
                    self._loaded_file_count,
                )
            schedule_ui_update(self._queue_all_thumbnails_for_background_loading, delay=0)

        logger.debug("[THUMBS-SHOW] showEvent END at t=%.3fms", (time.time() - t0) * 1000)

    def hideEvent(self, event) -> None:
        """Handle hide events - switch to background loading."""
        import time

        t0 = time.time()
        super().hideEvent(event)
        logger.debug("[THUMBS-HIDE] hideEvent START at t=%.3fms", (time.time() - t0) * 1000)

        # Switch to BACKGROUND priority mode when viewport becomes hidden
        if hasattr(self, "_controller") and self._controller:
            self._controller.set_viewport_visible(False)
            logger.debug("[ThumbnailViewport] Viewport hidden - switched to BACKGROUND mode")

        logger.debug("[THUMBS-HIDE] hideEvent END at t=%.3fms", (time.time() - t0) * 1000)

    def _on_thumbnail_ready(self, file_path: str, pixmap: "QPixmap") -> None:
        """Handle thumbnail_ready signal from ThumbnailManager.

        Registers a crossfade transition in the delegate so the real thumbnail
        fades in smoothly over the skeleton placeholder.

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
                # Register crossfade in delegate (skeleton -> real thumbnail)
                if not pixmap.isNull():
                    self._delegate.register_fade(row, pixmap)
                # Always trigger a view update for the item
                index = self._model.index(row, 0)
                self._list_view.update(index)
                if self._tooltip_behavior:
                    self._tooltip_behavior.refresh_tooltip_if_active(row, row)
                logger.debug(
                    "[ThumbnailViewport] Updated view for row=%d, file=%s",
                    row,
                    file_path,
                )
                return
        # File not in model - likely cleared while thumbnails were loading (expected behavior)
        # No warning needed as this is a normal race condition during clear operations

    def refresh_thumbnail(self, file_path: str, pixmap: "QPixmap") -> None:
        """Replace the displayed thumbnail for a file immediately (no async reload).

        Used when the logical content of a cached thumbnail changes in-place
        (e.g., after staging a metadata rotation change) so the viewport shows
        the new pixmap without waiting for a file save / mtime change.

        Unlike _on_thumbnail_ready(), this method forcibly removes the row from
        _completed_fades so that register_fade() is not silently skipped for
        rows whose initial crossfade already finished.

        Args:
            file_path: Absolute path to the file whose thumbnail should be updated
            pixmap: New thumbnail pixmap to display

        """
        if not self._model or not self._model.files or pixmap.isNull():
            return

        for row, file_item in enumerate(self._model.files):
            if file_item.full_path == file_path:
                # Remove from completed-fades so register_fade() is not skipped
                self._delegate._completed_fades.discard(row)
                self._delegate.register_fade(row, pixmap)
                index = self._model.index(row, 0)
                self._list_view.update(index)
                logger.debug(
                    "[ThumbnailViewport] refresh_thumbnail for row=%d, file=%s",
                    row,
                    file_path,
                )
                return

    def cleanup(self) -> None:
        """Clean up viewport resources.

        Called on widget destruction to stop timers and clean up resources.
        """
        # Stop scroll debounce timer
        if hasattr(self, "_scroll_debounce_timer") and self._scroll_debounce_timer:
            self._scroll_debounce_timer.stop()

        # Stop spinner timer
        if hasattr(self, "_spinner_timer") and self._spinner_timer:
            self._spinner_timer.stop()

        # Stop delegate shimmer timer
        if hasattr(self, "_delegate") and self._delegate:
            self._delegate._shimmer_timer.stop()

        # Clean up controller
        if hasattr(self, "_controller") and self._controller:
            self._controller.cleanup()

        logger.debug("[ThumbnailViewport] Cleanup completed")

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

        if self._tooltip_behavior:
            self._tooltip_behavior.refresh_tooltip_if_active(top_left.row(), bottom_right.row())

        logger.debug(
            "[ThumbnailViewport] Updated %d items after model data change",
            bottom_right.row() - top_left.row() + 1,
            extra={"dev_only": True},
        )

    # =====================================
    # DraggableWidget Protocol Implementation
    # (Required by DragDropBehavior)
    # =====================================

    def model(self):
        """Return the underlying model."""
        return self._model

    def viewport(self):
        """Return the list view viewport."""
        return self._list_view.viewport()

    def visualRect(self, index: "QModelIndex"):
        """Return visual rectangle for model index."""
        return self._list_view.visualRect(index)

    def rect(self):
        """Return widget rectangle."""
        return self._list_view.rect()

    def mapFromGlobal(self, pos):
        """Map global position to list view coordinates."""
        return self._list_view.mapFromGlobal(pos)

    def blockSignals(self, block: bool) -> bool:
        """Block/unblock signals on list view."""
        return self._list_view.blockSignals(block)

    def _get_current_selection(self) -> set[int]:
        """Get currently selected rows from list view.

        Returns:
            Set of row indices that are selected

        """
        selection_model = self._list_view.selectionModel()
        if not selection_model:
            return set()
        return {index.row() for index in selection_model.selectedIndexes()}

    def _get_current_selection_safe(self) -> set[int]:
        """Get current selection safely (fallback implementation)."""
        try:
            return self._get_current_selection()
        except Exception as e:
            logger.warning("[ThumbnailViewport] Error getting selection: %s", e)
            return set()

    def _get_selection_store(self):
        """Get selection store (not used in thumbnail viewport, return None)."""

    def _force_cursor_cleanup(self) -> None:
        """Force cleanup of any stuck cursors during drag operations."""
        from oncutf.utils.cursor_helper import force_restore_cursor

        force_restore_cursor()
