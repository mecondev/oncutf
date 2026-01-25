"""Module: interactive_header.py.

Author: Michael Economou
Date: 2025-05-22

interactive_header.py
This module defines InteractiveHeader, a subclass of QHeaderView that
adds interactive behavior to table headers in the oncutf application.
Features:
- Toggles selection of all rows when clicking on column 0
- Performs manual sort handling for sortable columns (excluding column 0)
- Prevents accidental sort when resizing (Explorer-like behavior)
"""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

from PyQt5.QtCore import QEvent, QPoint, Qt
from PyQt5.QtWidgets import (
    QAction,
    QHeaderView,
    QMenu,
    QStyle,
    QWidget,
)

from oncutf.controllers.header_interaction_controller import HeaderInteractionController
from oncutf.ui.behaviors.column_visibility_menu_builder import ColumnVisibilityMenuBuilder
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.ui.tooltip_helper import TooltipHelper, TooltipType

if TYPE_CHECKING:
    from PyQt5.QtCore import QRect
    from PyQt5.QtGui import QHelpEvent, QPainter

logger = get_cached_logger(__name__)


# ApplicationContext integration
try:
    from oncutf.core.application_context import get_app_context
except ImportError:
    get_app_context = None


class DropIndicatorWidget(QWidget):
    """Transparent widget for drawing column drop indicator on top of everything."""

    def __init__(self, parent, indicator_x: int, height: int):
        """Initialize drop indicator widget.

        Args:
            parent: Parent header widget.
            indicator_x: X position of the drop indicator.
            height: Height of the indicator.

        """
        super().__init__(parent)
        self.indicator_x = indicator_x
        self.indicator_height = height
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)

    def paintEvent(self, event):
        """Paint the drop indicator line and triangle."""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QBrush, QColor, QPainter, QPen, QPolygon

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Get text color from theme for indicator
        from oncutf.ui.theme_manager import get_theme_manager
        theme = get_theme_manager()
        text_color = theme.get_color("table_header_text")
        indicator_color = QColor(text_color) if isinstance(text_color, str) else text_color

        x = self.indicator_x
        h = self.indicator_height

        # Draw vertical line (thinner)
        pen = QPen(indicator_color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(x, 0, x, h)

        # Draw triangle marker at top (pointing down)
        tri = 5
        poly = QPolygon([QPoint(x - tri, 0), QPoint(x + tri, 0), QPoint(x, tri)])
        brush = QBrush(indicator_color)
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(poly)

        painter.end()


class InteractiveHeader(QHeaderView):
    """A custom QHeaderView that toggles selection on column 0 click,
    and performs manual sorting for other columns. Prevents accidental sort
    when user clicks near the edge to resize.
    """

    def __init__(self, orientation, parent=None, parent_window=None):
        """Initialize interactive header with orientation and optional parent window."""
        super().__init__(orientation, parent)
        self.parent_window = parent_window  # Keep for backward compatibility
        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setSortIndicatorShown(True)
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.header_enabled = True

        # When False, header clicks won't trigger app actions (sort/toggle).
        self._click_actions_enabled: bool = True

        self._press_pos: QPoint = QPoint()
        self._pressed_index: int = -1
        self._drag_active: bool = False
        self._drag_grab_offset: int = 0
        self._interaction_qss_applied: bool = False

        # Drop indicator (Excel-like) widget - separate widget to stay on top
        self._drop_indicator_widget: QWidget | None = None
        self._drop_indicator_visible: bool = False
        self._drop_indicator_x: int = -1
        self._drop_indicator_to_visual: int = -1

        # Internal flag to allow controlled section moves (used by configurator)
        self._allow_forced_section_move: bool = False

        # Track last tooltip section to avoid redundant rendering
        self._last_tooltip_section: int = -1

        # Tooltip hover delay timer ID (managed by TimerManager)
        self._tooltip_timer_id: str | None = None
        self._pending_tooltip_section: int = -1

        # Auto-scroll support during column drag (using QTimer for repeating scroll)
        self._auto_scroll_timer = None  # Created on demand
        self._auto_scroll_direction: int = 0  # -1 for left, 1 for right, 0 for none

        # Header tooltip texts (rendered via TooltipHelper for consistent styling)
        self._header_tooltips_by_key: dict[str, str] = {
            "color": (
                "Color flag for files. You can set it per selection.\n"
                "When multiple folders are loaded, the context menu\n"
                "can auto-assign random colors per folder to keep\n"
                "them visually separated."
            ),
            "filename": "Original filename (base name).",
            "extension": "File extension (lowercase).",
            "folder": "Parent folder path (normalized).",
            "type": "Media type/category derived from\nmetadata and extension.",
            "file_size": "File size in human-readable units.",
            "modified": "Last modified timestamp.",
            "duration": "Media duration when available\n(audio/video).",
            "video_fps": "Video frames per second\n(reported or detected).",
            "video_format": "Video container/format info.",
            "video_codec": "Video codec name.",
            "video_avg_bitrate": "Average video bitrate.",
            "image_size": "Image resolution\n(width x height).",
            "rotation": "Image/video rotation metadata.",
            "iso": "Capture ISO value (if present).",
            "aperture": "Capture aperture (F-stop).",
            "shutter_speed": "Capture shutter speed.",
            "white_balance": "White balance setting.",
            "compression": "Image compression/quality\ninfo.",
            "color_space": "Color space / profile info.",
            "audio_channels": "Audio channel count\n(mono/stereo/etc).",
            "audio_format": "Audio codec/format info.",
            "artist": "Metadata artist/creator tag.",
            "copyright": "Metadata copyright tag.",
            "owner_name": "Metadata owner name tag.",
            "device_manufacturer": "Capture device manufacturer\n(metadata).",
            "device_model": "Capture device model\n(metadata).",
            "device_serial_no": "Capture device serial\n(metadata).",
            "target_umid": "Target UMID / unique media\nidentifier if present.",
            "file_hash": "Hash value status\n(cached when computed).",
        }

        # Disable Qt default tooltips on the header viewport (we render our own)
        with suppress(Exception):
            self.viewport().setToolTip("")

        # Initialize controller (will be set properly after main window is available)
        self._controller: HeaderInteractionController | None = None

        self._ensure_interaction_qss()
        self._set_interaction_state(locked=not self.sectionsMovable())

    def _ensure_controller(self) -> HeaderInteractionController | None:
        """Ensure controller is initialized. Returns None if main window not available yet."""
        if self._controller is not None:
            return self._controller

        main_window = self._get_main_window_via_context()
        if main_window:
            self._controller = HeaderInteractionController(main_window)
        return self._controller

    def setSectionsMovable(self, movable: bool) -> None:
        """Override to keep UI interaction feedback consistent with lock state."""
        super().setSectionsMovable(movable)
        if not movable:
            self._drag_active = False
            self._hide_drop_indicator()
        self._set_interaction_state(locked=not movable)

    def _create_drop_indicator_widget(self) -> None:
        """Create a transparent widget for drawing the drop indicator on top."""
        if self._drop_indicator_widget:
            self._drop_indicator_widget.deleteLater()

        # Create custom drop indicator widget with paintEvent
        self._drop_indicator_widget = DropIndicatorWidget(
            self,
            self._drop_indicator_x,
            self.height()
        )
        self._drop_indicator_widget.setGeometry(0, 0, self.width(), self.height())
        self._drop_indicator_widget.show()
        self._drop_indicator_widget.raise_()  # Always on top

    def _update_drop_indicator_widget_geometry(self) -> None:
        """Update drop indicator widget geometry and position."""
        if self._drop_indicator_widget:
            self._drop_indicator_widget.indicator_x = self._drop_indicator_x
            self._drop_indicator_widget.indicator_height = self.height()
            self._drop_indicator_widget.setGeometry(0, 0, self.width(), self.height())
            self._drop_indicator_widget.raise_()  # Ensure it stays on top
            self._drop_indicator_widget.update()  # Trigger repaint

    def _hide_drop_indicator(self) -> None:
        """Hide drop indicator and request repaint."""
        if self._drop_indicator_visible:
            self._drop_indicator_visible = False
            self._drop_indicator_x = -1
            self._drop_indicator_to_visual = -1
            if self._drop_indicator_widget:
                self._drop_indicator_widget.hide()
                self._drop_indicator_widget.deleteLater()
                self._drop_indicator_widget = None

    def _update_drop_indicator(self, mouse_x: int) -> None:
        """Compute and show an Excel-like drop indicator for the current drag position.

        The indicator represents the insertion boundary between sections.
        Coordinates are in header viewport space.

        Args:
            mouse_x: Current mouse X position in viewport coordinates.

        """
        # Don't show indicator if not dragging a valid column
        if self._pressed_index < 0 or self._pressed_index == 0:
            self._hide_drop_indicator()
            return

        target_logical = self.logicalIndexAt(mouse_x)

        # If mouse is beyond all columns (returns -1), treat as "after last column"
        if target_logical == -1:
            # Place indicator after the last visible column
            target_logical = self.logicalIndex(self.count() - 1)
            target_visual = self.count() - 1
            # Force insertion at the end
            insert_visual = self.count()
            last_logical = self.logicalIndex(self.count() - 1)
            boundary_x = self.sectionViewportPosition(last_logical) + self.sectionSize(last_logical)

            self._drop_indicator_visible = True
            self._drop_indicator_to_visual = insert_visual
            self._drop_indicator_x = boundary_x

            if not self._drop_indicator_widget:
                self._create_drop_indicator_widget()
            else:
                self._update_drop_indicator_widget_geometry()

            with suppress(Exception):
                if self._drop_indicator_widget:
                    self._drop_indicator_widget.update()
            return

        # Never indicate insertion into status column area (logical 0)
        if target_logical <= 0:
            self._hide_drop_indicator()
            return

        dragged_visual = self.visualIndex(self._pressed_index)
        target_visual = self.visualIndex(target_logical)
        if dragged_visual < 0 or target_visual < 0:
            self._hide_drop_indicator()
            return

        # Determine before/after target section by comparing mouse_x with section midpoint
        section_left = self.sectionViewportPosition(target_logical)
        section_width = self.sectionSize(target_logical)
        midpoint = section_left + (section_width // 2)
        insert_visual = target_visual + (1 if mouse_x > midpoint else 0)

        # Clamp insert_visual to [1, self.count()] (never insert at position 0)
        insert_visual = max(1, min(insert_visual, self.count()))

        # Adjust when dragging from left to right so the boundary feels correct
        if dragged_visual < insert_visual:
            insert_visual = max(1, insert_visual - 1)

        # Convert insert_visual to boundary x coordinate
        if insert_visual >= self.count():
            last_logical = self.logicalIndex(self.count() - 1)
            boundary_x = self.sectionViewportPosition(last_logical) + self.sectionSize(last_logical)
        else:
            logical_at_insert = self.logicalIndex(insert_visual)
            boundary_x = self.sectionViewportPosition(logical_at_insert)

        self._drop_indicator_visible = True
        self._drop_indicator_to_visual = insert_visual
        self._drop_indicator_x = boundary_x

        # Create/update drop indicator widget
        if not self._drop_indicator_widget:
            self._create_drop_indicator_widget()
        else:
            self._update_drop_indicator_widget_geometry()

        # Trigger repaint of indicator widget
        with suppress(Exception):
            if self._drop_indicator_widget:
                self._drop_indicator_widget.update()

    def _check_auto_scroll(self, mouse_x: int) -> None:
        """Check if auto-scroll should be triggered based on mouse position.

        Args:
            mouse_x: Current mouse X position in widget coordinates.

        """
        # Define edge zone width (pixels from edge to trigger scroll)
        edge_zone = 50

        viewport_width = self.width()
        new_direction = 0

        # Check if mouse is near left edge
        if mouse_x < edge_zone:
            new_direction = -1
        # Check if mouse is near right edge
        elif mouse_x > viewport_width - edge_zone:
            new_direction = 1

        # Start/stop/update auto-scroll timer based on direction change
        if new_direction != self._auto_scroll_direction:
            self._auto_scroll_direction = new_direction
            if new_direction == 0:
                self._stop_auto_scroll()
            else:
                self._start_auto_scroll()

    def _start_auto_scroll(self) -> None:
        """Start auto-scroll timer for smooth scrolling during drag."""
        # Stop existing timer if any
        self._stop_auto_scroll()

        # Create and start timer (scroll every 50ms for smooth animation)
        from PyQt5.QtCore import QTimer

        self._auto_scroll_timer = QTimer()
        self._auto_scroll_timer.setSingleShot(False)
        self._auto_scroll_timer.timeout.connect(self._perform_auto_scroll)
        self._auto_scroll_timer.start(50)  # 50ms interval

    def _stop_auto_scroll(self) -> None:
        """Stop auto-scroll timer."""
        if self._auto_scroll_timer:
            self._auto_scroll_timer.stop()
            self._auto_scroll_timer.deleteLater()
            self._auto_scroll_timer = None
        self._auto_scroll_direction = 0

    def _perform_auto_scroll(self) -> None:
        """Perform one step of auto-scroll in the current direction."""
        if self._auto_scroll_direction == 0:
            return

        # Get the file table view to access its horizontal scroll bar
        file_table_view = self._get_file_table_view()
        if not file_table_view:
            return

        h_scroll = file_table_view.horizontalScrollBar()
        if not h_scroll:
            return

        # Scroll by small increments (10 pixels per step)
        scroll_step = 10 * self._auto_scroll_direction
        new_value = h_scroll.value() + scroll_step

        # Clamp to valid range
        new_value = max(h_scroll.minimum(), min(new_value, h_scroll.maximum()))
        h_scroll.setValue(new_value)

        # Update overlay and indicator positions after scroll
        # The scroll will trigger events, but we need to ensure visual feedback
        # stays consistent during auto-scroll
        with suppress(Exception):
            if self._drag_overlay:
                # Recalculate overlay position based on current mouse position
                # (stored implicitly in the drag state)
                pass  # Position is already managed by mouseMoveEvent updates

    def _get_app_context(self):
        """Get ApplicationContext with fallback to None."""
        if get_app_context is None:
            return None
        try:
            return get_app_context()
        except RuntimeError:
            # ApplicationContext not ready yet
            return None

    def _get_main_window_via_context(self):
        """Get main window via ApplicationContext with fallback to parent traversal."""
        # Try ApplicationContext first
        context = self._get_app_context()
        if context and hasattr(context, "_main_window"):
            return context._main_window

        # Fallback to legacy parent_window approach
        if self.parent_window:
            return self.parent_window

        # Last resort: traverse parents to find main window
        from oncutf.utils.filesystem.path_utils import find_parent_with_attribute

        return find_parent_with_attribute(self, "handle_header_toggle")

    def mousePressEvent(self, event) -> None:
        """Handle mouse press to track position and index for drag detection."""
        if event.button() != Qt.LeftButton:
            self._pressed_index = -1
            super().mousePressEvent(event)
            return

        self._press_pos = event.pos()
        self._pressed_index = self.logicalIndexAt(event.pos())
        self._drag_active = False

        logger.info("[HEADER PRESS] logical=%d, pos=%s", self._pressed_index, event.pos())

        # Prevent dragging status column (0)
        if self._pressed_index == 0:
            # Keep column 0 fixed but allow click to toggle select all
            self._drag_grab_offset = 0
            # Accept event here to prevent base class from handling it
            # (stops propagation but preserves visual feedback)
            event.accept()
            return

        # Store grab offset for drag overlay positioning
        if self._pressed_index >= 0:
            section_left = self.sectionViewportPosition(self._pressed_index)
            self._drag_grab_offset = event.pos().x() - section_left

        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:
        """Handle keyboard events during drag operations."""
        # ESC cancels column drag
        if event.key() == Qt.Key_Escape and self._drag_active:
            logger.info("[HEADER] ESC pressed - canceling column drag")
            self._drag_active = False
            self._pressed_index = -1
            self._hide_drop_indicator()
            self._stop_auto_scroll()
            event.accept()
            return

        super().keyPressEvent(event)

    def enterEvent(self, event) -> None:
        """Clear table hover when mouse enters header."""
        # Get file table view to clear its hover state
        file_table_view = self._get_file_table_view()
        if file_table_view and hasattr(file_table_view, '_hover_handler'):
            file_table_view._hover_handler.clear_hover()
        super().enterEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move to create and update drag overlay for column reordering."""
        if not self.sectionsMovable():
            self._hide_drop_indicator()
            super().mouseMoveEvent(event)
            return

        if self._pressed_index == 0:
            self._hide_drop_indicator()
            return

        if (event.buttons() & Qt.LeftButton) and self._pressed_index >= 0:
            if not self._drag_active:
                if (event.pos() - self._press_pos).manhattanLength() > 4:
                    self._drag_active = True

            if self._drag_active:
                self._update_drop_indicator(event.pos().x())
                # Trigger auto-scroll if near viewport edges
                self._check_auto_scroll(event.pos().x())
        elif not self._drag_active:
            # Not dragging - ensure indicator is hidden
            self._hide_drop_indicator()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release to finalize drag or trigger column actions (sort/toggle)."""
        if event.button() != Qt.LeftButton:
            self._pressed_index = -1
            super().mouseReleaseEvent(event)
            return

        if self._drag_active:
            self._drag_active = False
            self._hide_drop_indicator()
            self._stop_auto_scroll()

        super().mouseReleaseEvent(event)

        released_index = self.logicalIndexAt(event.pos())
        logger.info(
            "[HEADER RELEASE] released=%d, pressed=%d, enabled=%s, manhattan=%d",
            released_index,
            self._pressed_index,
            self._click_actions_enabled,
            (event.pos() - self._press_pos).manhattanLength()
        )

        # Use controller to determine if click should be handled
        controller = self._ensure_controller()
        if not controller:
            logger.warning("[HEADER RELEASE] No controller available!")
            return

        manhattan = (event.pos() - self._press_pos).manhattanLength()
        should_handle, action_type = controller.should_handle_click(
            self._pressed_index,
            released_index,
            manhattan,
            self._click_actions_enabled,
        )

        if not should_handle:
            return

        # Execute the appropriate action via controller
        if action_type == "toggle":
            logger.info("[HEADER RELEASE] Column 0 clicked - calling controller.handle_toggle_all")
            controller.handle_toggle_all()
        elif action_type == "sort":
            logger.info("[HEADER RELEASE] Column %d clicked - calling controller.handle_sort", released_index)
            controller.handle_sort(released_index)


    def _get_header_tooltip_text(self, logical_index: int) -> str | None:
        if logical_index == 0:
            return "Select/Deselect all files (toggle status column)."

        file_table_view = self._get_file_table_view()
        if not file_table_view or not hasattr(file_table_view, "_column_mgmt_behavior"):
            return None

        visible_columns = file_table_view._column_mgmt_behavior.get_visible_columns_list()
        column_index = logical_index - 1  # -1 for status column
        if not (0 <= column_index < len(visible_columns)):
            return None

        column_key = visible_columns[column_index]
        return self._header_tooltips_by_key.get(column_key)

    def viewportEvent(self, event: QEvent) -> bool:
        """Handle tooltip events on the header viewport to suppress Qt default tooltips."""
        if event.type() == QEvent.ToolTip:
            from oncutf.utils.shared.timer_manager import cancel_timer, schedule_dialog_close

            logical_index = self.logicalIndexAt(event.pos())
            text = self._get_header_tooltip_text(logical_index)

            if text:
                # Only show tooltip when section changes (avoid flickering on mouse move)
                if logical_index != self._last_tooltip_section:
                    # Cancel previous timer
                    if self._tooltip_timer_id:
                        cancel_timer(self._tooltip_timer_id)

                    TooltipHelper.clear_tooltips_for_widget(self)
                    self._last_tooltip_section = logical_index
                    self._pending_tooltip_section = logical_index
                    # Schedule tooltip with 500ms delay (consistent with other UI tooltips)
                    self._tooltip_timer_id = schedule_dialog_close(self._show_pending_tooltip)
            else:
                # No tooltip text for this section
                if self._tooltip_timer_id:
                    cancel_timer(self._tooltip_timer_id)
                    self._tooltip_timer_id = None
                if self._last_tooltip_section != -1:
                    TooltipHelper.clear_tooltips_for_widget(self)
                    self._last_tooltip_section = -1

            event.accept()
            return True

        if event.type() == QEvent.Leave:
            if self._tooltip_timer_id:
                from oncutf.utils.shared.timer_manager import cancel_timer
                cancel_timer(self._tooltip_timer_id)
                self._tooltip_timer_id = None
            TooltipHelper.clear_tooltips_for_widget(self)
            self._last_tooltip_section = -1

        return super().viewportEvent(event)

    def moveSection(self, from_visual: int, to_visual: int) -> None:
        """Block any move that would involve the status column (logical 0 or visual 0)."""
        if self._allow_forced_section_move:
            # Bypass safeguards when restoration logic explicitly requests it
            QHeaderView.moveSection(self, from_visual, to_visual)
            return

        # Use controller to validate drag
        controller = self._ensure_controller()
        if controller and not controller.validate_column_drag(from_visual, to_visual):
            return

        super().moveSection(from_visual, to_visual)

    def paintSection(self, painter: QPainter, rect: QRect, logical_index: int) -> None:
        """Disable hover highlight for status column while keeping others intact."""
        if logical_index == 0:
            try:
                from PyQt5.QtWidgets import QStyleOptionHeader
            except ImportError:
                super().paintSection(painter, rect, logical_index)
                return

            option = QStyleOptionHeader()
            self.initStyleOption(option)
            option.rect = rect
            option.section = logical_index
            option.state &= ~QStyle.State_MouseOver
            option.state &= ~QStyle.State_Sunken
            self.style().drawControl(QStyle.CE_Header, option, painter, self)
            return

        super().paintSection(painter, rect, logical_index)

    def paintEvent(self, event) -> None:
        """Paint header sections."""
        super().paintEvent(event)

    def helpEvent(self, event: QHelpEvent) -> bool:
        # Tooltips are handled in viewportEvent.
        return super().helpEvent(event)

    def _show_pending_tooltip(self) -> None:
        """Show tooltip for pending section after delay expires."""
        if self._pending_tooltip_section < 0:
            return

        text = self._get_header_tooltip_text(self._pending_tooltip_section)
        if text:
            TooltipHelper.show_tooltip(
                self,
                text,
                TooltipType.INFO,
                duration=0,
            )

    def set_click_actions_enabled(self, enabled: bool) -> None:
        """Enable/disable click-triggered actions (sort/toggle).

        Note: This does not change Qt's sectionsClickable, which is needed
        for pressed/drag visual feedback.
        """
        self._click_actions_enabled = enabled

    def _ensure_interaction_qss(self) -> None:
        """Apply QSS for locked state interaction (neutralize hover when locked)."""
        if self._interaction_qss_applied:
            return

        try:
            from oncutf.ui.theme_manager import get_theme_manager

            theme = get_theme_manager()
            header_bg = theme.get_color("table_header_bg")
            header_text = theme.get_color("table_header_text")

            # While locked: neutralize hover.
            qss = (
                "\nQHeaderView[oncutf_locked=\"true\"]::section:hover {"
                f"background-color: {header_bg};"
                f"color: {header_text};"
                "}"
            )

            self.setStyleSheet((self.styleSheet() or "") + qss)
            self._interaction_qss_applied = True
        except Exception:
            self._interaction_qss_applied = False

    def _set_interaction_state(self, *, locked: bool | None = None) -> None:
        """Update header lock state property and trigger style refresh."""
        if locked is not None:
            self.setProperty("oncutf_locked", locked)

        with suppress(Exception):
            self.style().unpolish(self)
            self.style().polish(self)
        self.update()



    def contextMenuEvent(self, event):
        """Show unified right-click context menu for header."""
        logical_index = self.logicalIndexAt(event.pos())

        # Don't show context menu for status column (0)
        if logical_index == 0:
            return

        menu = QMenu(self)

        # Apply theme styling
        from oncutf.ui.theme_manager import get_theme_manager

        theme = get_theme_manager()
        menu.setStyleSheet(theme.get_context_menu_stylesheet())

        # Add sorting options for columns > 0
        if logical_index > 0:
            try:
                from oncutf.utils.ui.icons_loader import get_menu_icon

                sort_asc = QAction("Sort Ascending", self)
                sort_asc.setIcon(get_menu_icon("chevron-down"))
                sort_desc = QAction("Sort Descending", self)
                sort_desc.setIcon(get_menu_icon("chevron-up"))
            except ImportError:
                sort_asc = QAction("Sort Ascending", self)
                sort_desc = QAction("Sort Descending", self)

            asc = getattr(Qt, "AscendingOrder", 0)
            desc = getattr(Qt, "DescendingOrder", 1)
            sort_asc.triggered.connect(lambda: self._sort(logical_index, asc))
            sort_desc.triggered.connect(lambda: self._sort(logical_index, desc))

            menu.addAction(sort_asc)
            menu.addAction(sort_desc)
            menu.addSeparator()

        # Add column visibility options
        self._add_column_visibility_menu(menu)

        menu.exec_(self.mapToGlobal(event.pos()))

    def _sort(self, column: int, order: Qt.SortOrder) -> None:
        """Calls controller.handle_sort() with forced order from context menu."""
        controller = self._ensure_controller()
        if controller:
            controller.handle_sort(column, force_order=order)

    def _add_column_visibility_menu(self, menu):
        """Add column visibility toggle options to the menu with grouped sections."""
        file_table_view = self._get_file_table_view()
        if not file_table_view:
            return

        # Use builder to create column visibility submenu
        builder = ColumnVisibilityMenuBuilder(file_table_view)
        builder.build_menu(menu, self._toggle_column_visibility)

        # Add separator before lock toggle
        menu.addSeparator()

        # Add lock columns toggle
        self._add_lock_columns_toggle(menu, file_table_view)

        # Add reset column order option
        self._add_reset_column_order(menu, file_table_view)

    def _get_file_table_view(self):
        """Get the file table view that this header belongs to."""
        # The header's parent should be the table view
        parent = self.parent()
        if parent and hasattr(parent, "_column_mgmt_behavior"):
            return parent
        return None

    def _add_lock_columns_toggle(self, menu, file_table_view):
        """Add lock/unlock columns toggle to menu."""
        try:
            from oncutf.utils.ui.icons_loader import get_menu_icon

            # Check current lock state
            is_locked = self._is_columns_locked()

            # Use toggle switch icons: toggle-left (off/locked), toggle-right (on/unlocked)
            if is_locked:
                lock_action = QAction("Unlock Columns", menu)
                lock_action.setIcon(get_menu_icon("toggle-left"))  # Off = Locked
            else:
                lock_action = QAction("Lock Columns", menu)
                lock_action.setIcon(get_menu_icon("toggle-right"))  # On = Unlocked

            lock_action.triggered.connect(self._toggle_columns_lock)
            menu.addAction(lock_action)

        except Exception as e:
            logger.warning("Failed to add lock columns toggle: %s", e)

    def _is_columns_locked(self) -> bool:
        """Check if columns are currently locked (not movable)."""
        # Try to load from config first
        try:
            main_window = self._get_main_window_via_context()
            if main_window and hasattr(main_window, "window_config_manager"):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category("window")
                return window_config.get("columns_locked", False)
        except Exception:
            pass

        # Fallback: check current header state
        return not self.sectionsMovable()

    def _toggle_columns_lock(self):
        """Toggle lock state of columns (enable/disable reordering)."""
        current_state = self.sectionsMovable()
        new_state = not current_state

        # Update header
        self.setSectionsMovable(new_state)

        # Save to config
        try:
            main_window = self._get_main_window_via_context()
            if main_window and hasattr(main_window, "window_config_manager"):
                config_manager = main_window.window_config_manager.config_manager
                window_config = config_manager.get_category("window")
                window_config.set("columns_locked", not new_state)
                config_manager.mark_dirty()

                logger.info(
                    "Columns %s", "locked" if not new_state else "unlocked"
                )
        except Exception as e:
            logger.warning("Failed to save columns lock state: %s", e)

    def _add_reset_column_order(self, menu, file_table_view):
        """Add reset column order option to menu."""
        try:
            from oncutf.utils.ui.icons_loader import get_menu_icon

            reset_action = QAction("Reset Column Order", menu)
            reset_action.setIcon(get_menu_icon("refresh"))
            reset_action.triggered.connect(self._reset_column_order)

            # Disable if columns are locked
            if self._is_columns_locked():
                reset_action.setEnabled(False)

            menu.addAction(reset_action)

        except Exception as e:
            logger.warning("Failed to add reset column order option: %s", e)

    def _reset_column_order(self):
        """Reset column order, widths, and visibility to defaults."""
        try:
            main_window = self._get_main_window_via_context()
            if not main_window or not hasattr(main_window, "window_config_manager"):
                return

            # Get file table view
            file_table_view = self._get_file_table_view()
            if not file_table_view:
                return

            config_manager = main_window.window_config_manager.config_manager
            window_config = config_manager.get_category("window")

            # 1. Clear saved column order
            window_config.set("column_order", None)

            # 2. Reset all column widths to defaults
            window_config.set("file_table_column_widths", {})

            # 3. Reset column visibility to defaults (from FILE_TABLE_COLUMN_CONFIG)
            from oncutf.config import FILE_TABLE_COLUMN_CONFIG
            default_visibility = {
                key: config.get("default_visible", True)
                for key, config in FILE_TABLE_COLUMN_CONFIG.items()
            }
            window_config.set("file_table_columns", default_visibility)

            config_manager.mark_dirty()

            # 4. Reset visual order immediately
            header = self.parent().horizontalHeader() if self.parent() else None
            if header:
                # Move sections back to their logical order
                for logical_index in range(header.count()):
                    current_visual = header.visualIndex(logical_index)
                    if current_visual != logical_index:
                        header.moveSection(current_visual, logical_index)

            # 5. Reconfigure columns to apply defaults
            if hasattr(file_table_view, "_column_mgmt_behavior"):
                file_table_view._column_mgmt_behavior.configure_columns()

            logger.info("Reset columns to default (order, widths, visibility)")

        except Exception as e:
            logger.warning("Failed to reset column order: %s", e)

    def _toggle_column_visibility(self, column_key: str):
        """Toggle visibility of a specific column via canonical column management API."""
        file_table_view = self._get_file_table_view()
        if file_table_view and hasattr(file_table_view, "_column_mgmt_behavior"):
            file_table_view._column_mgmt_behavior.toggle_column_visibility(column_key)
