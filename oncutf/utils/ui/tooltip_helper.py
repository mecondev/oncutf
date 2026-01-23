"""Module: tooltip_helper.py.

Author: Michael Economou
Date: 2025-05-31

This module provides centralized tooltip management with custom styling and
behavior. It supports both temporary tooltips (with auto-hide) and persistent
tooltips (that behave like Qt standard tooltips) for displaying tooltips with
different types (error, warning, info, success) and consistent styling across
the application.
Classes:
- CustomTooltip: Enhanced tooltip widget with custom styling
- TooltipHelper: Central management class for tooltip operations
- TooltipType: Constants for different tooltip types
- ActionTooltipFilter: Event filter for QAction custom tooltips
- ItemTooltipFilter: Event filter for QListWidget/QTableWidget item tooltips
- Convenience functions for easy tooltip display
"""

from typing import ClassVar

from PyQt5.QtCore import QEvent, QObject, QPoint, Qt, QTimer
from PyQt5.QtWidgets import QApplication, QLabel, QListWidget, QMenu, QTableWidget, QWidget

from oncutf.config import TOOLTIP_DURATION, TOOLTIP_POSITION_OFFSET
from oncutf.utils.logging.logger_helper import get_logger

logger = get_logger(__name__)


class WidgetTooltipFilter(QObject):
    """Event filter for persistent tooltips on widgets."""

    def __init__(self, widget: QWidget, tooltip: "CustomTooltip", parent: QObject | None = None):
        """Initialize tooltip filter for widget with hover delay."""
        super().__init__(parent)
        self.widget = widget
        self.tooltip = tooltip
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self._show_tooltip)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter events to show tooltip on hover."""
        if obj != self.widget:
            return False

        try:
            if event.type() == QEvent.Enter:
                # Mouse entered widget - start timer
                self.hover_timer.start(600)  # 600ms delay
            elif event.type() == QEvent.Leave:
                # Mouse left widget - hide tooltip
                self.hover_timer.stop()
                self.tooltip.hide()
            elif event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
                # Mouse clicked - hide tooltip immediately
                self.hover_timer.stop()
                self.tooltip.hide()
            elif event.type() == QEvent.ToolTip:
                # Suppress default Qt tooltip
                return True
        except RuntimeError:
            # Widget has been deleted
            pass

        return False

    def _show_tooltip(self) -> None:
        """Show the tooltip."""
        try:
            from oncutf.utils.ui.tooltip_helper import TooltipHelper

            TooltipHelper._show_persistent_tooltip(self.widget, self.tooltip)
        except RuntimeError:
            # Widget or tooltip has been deleted
            pass


class TooltipType:
    """Tooltip type constants."""

    DEFAULT = "default"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"


class CustomTooltip(QLabel):
    """Custom tooltip widget with enhanced styling and behavior."""

    def __init__(
        self,
        parent: QWidget,
        text: str,
        tooltip_type: str = TooltipType.DEFAULT,
        persistent: bool = False,
    ):
        """Initialize custom tooltip with text, type, and persistence mode."""
        super().__init__(text, parent)
        self.tooltip_type = tooltip_type
        self.persistent = persistent
        self._timer = QTimer()
        self._timer.timeout.connect(self.hide_tooltip)
        self._setup_ui()

    def _setup_ui(self):
        """Setup tooltip UI and styling."""
        # Set window flags for tooltip behavior
        if self.persistent:
            # Persistent tooltips behave like Qt standard tooltips
            self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)  # type: ignore[attr-defined]
        else:
            # Temporary tooltips with auto-hide
            self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)  # type: ignore[attr-defined]

        # Apply styling based on tooltip type
        style_classes = {
            TooltipType.ERROR: "ErrorTooltip",
            TooltipType.WARNING: "WarningTooltip",
            TooltipType.INFO: "InfoTooltip",
            TooltipType.SUCCESS: "SuccessTooltip",
            TooltipType.DEFAULT: "InfoTooltip",  # Default to info style
        }.get(self.tooltip_type, "InfoTooltip")

        self.setProperty("class", style_classes)
        self.setWordWrap(False)  # Only break on explicit \n

        # Calculate optimal width and height based on text content using QFontMetrics
        from PyQt5.QtGui import QFontMetrics

        fm = QFontMetrics(self.font())
        text = self.text()

        # Calculate padding based on font metrics (make it scalable)
        line_height = fm.height()
        # Padding: 6px top + 6px bottom from stylesheet = 12px base
        # Scale with font size: use ~0.7 * line_height for vertical padding
        vertical_padding = int(line_height * 0.7)
        # Horizontal padding: 8px left + 8px right from stylesheet = 16px base
        # Scale with font size: use ~1.0 * line_height for horizontal padding
        horizontal_padding = int(line_height * 1.0)

        if "\n" in text:
            # Multi-line: calculate width based on longest line
            lines = text.split("\n")
            max_line_width = max(fm.horizontalAdvance(line) for line in lines)
            optimal_width = min(max_line_width + horizontal_padding, 400)
            # Calculate height: (line height + leading) * number of lines + vertical padding
            optimal_height = (line_height * len(lines)) + vertical_padding
        else:
            # Single line: fit to content
            text_width = fm.horizontalAdvance(text)
            optimal_width = min(text_width + horizontal_padding, 400)
            # Single line height + vertical padding
            optimal_height = line_height + vertical_padding

        self.setFixedWidth(optimal_width)
        self.setFixedHeight(optimal_height)
        self.setMaximumWidth(400)  # Safety limit

    def show_tooltip(self, position: QPoint, duration: int | None = None):
        """Show tooltip at specific position for specified duration."""
        if duration is not None and duration > 0:
            self._timer.start(duration)

        self.move(position)
        self.show()
        self.raise_()

    def mousePressEvent(self, event) -> None:
        """Hide tooltip when clicked."""
        self.hide_tooltip()
        event.accept()

    def hide_tooltip(self) -> None:
        """Hide the tooltip."""
        self._timer.stop()
        self.hide()
        self.hide()


class ActionTooltipFilter(QObject):
    """Event filter for QMenu to show custom tooltips on QAction hover."""

    def __init__(self, menu: QMenu, parent: QObject | None = None):
        """Initialize action tooltip filter for menu."""
        super().__init__(parent)
        self.menu = menu
        self.current_tooltip: CustomTooltip | None = None
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self._show_tooltip)
        self.current_action = None
        self.tooltip_data: dict = {}  # action -> (text, type)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter events on QMenu to detect action hover."""
        if obj != self.menu:
            return False

        if event.type() == QEvent.ToolTip:
            # Suppress default Qt tooltips
            return True

        elif event.type() == QEvent.MouseMove:
            # Find action under mouse
            action = self.menu.actionAt(event.pos())

            if action and action != self.current_action:
                # New action hovered
                self.current_action = action

                # Hide previous tooltip
                if self.current_tooltip:
                    self.current_tooltip.hide()
                    self.current_tooltip = None

                # Schedule new tooltip show
                if action in self.tooltip_data:
                    self.hover_timer.start(600)  # 600ms delay

            elif not action and self.current_action:
                # Mouse left action area
                self._hide_tooltip()

        elif event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            # Mouse clicked - hide tooltip immediately
            self._hide_tooltip()

        elif event.type() == QEvent.Leave:
            # Mouse left menu
            self._hide_tooltip()

        return False

    def _show_tooltip(self) -> None:
        """Show custom tooltip for current action."""
        if not self.current_action or self.current_action not in self.tooltip_data:
            return

        text, tooltip_type = self.tooltip_data[self.current_action]

        # Create custom tooltip
        self.current_tooltip = CustomTooltip(
            self.menu.window(), text, tooltip_type, persistent=False
        )

        # Position and show tooltip
        tooltip_pos = TooltipHelper._calculate_tooltip_position(self.menu)
        self.current_tooltip.show_tooltip(tooltip_pos, duration=TOOLTIP_DURATION)

    def _hide_tooltip(self) -> None:
        """Hide current tooltip."""
        self.hover_timer.stop()
        self.current_action = None

        if self.current_tooltip:
            self.current_tooltip.hide()
            self.current_tooltip = None

    def register_action(self, action, text: str, tooltip_type: str) -> None:
        """Register an action with custom tooltip data."""
        self.tooltip_data[action] = (text, tooltip_type)


class ItemTooltipFilter(QObject):
    """Event filter for QListWidget/QTableWidget to show custom tooltips on item hover."""

    def __init__(self, widget: QListWidget | QTableWidget, parent: QObject | None = None):
        """Initialize item tooltip filter for list/table widget."""
        super().__init__(parent)
        self.widget = widget
        self.current_tooltip: CustomTooltip | None = None
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self._show_tooltip)
        self.current_item = None
        self.tooltip_data: dict = {}  # id(item) -> (text, type)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter events on widget to detect item hover."""
        try:
            if obj != self.widget.viewport():
                return False
        except RuntimeError:
            # Widget has been deleted
            return False

        if event.type() == QEvent.ToolTip:
            # Suppress default Qt tooltips
            return True

        elif event.type() == QEvent.MouseMove:
            # Find item under mouse
            if isinstance(self.widget, QListWidget):
                item = self.widget.itemAt(event.pos())
            else:  # QTableWidget
                item = self.widget.itemAt(event.pos())

            if item != self.current_item:
                # Item changed, hide current tooltip and start timer for new one
                self._hide_tooltip()
                self.current_item = item

                if item and id(item) in self.tooltip_data:
                    # Start timer to show tooltip after hover delay
                    self.hover_timer.start(600)  # 600ms delay
                return False

        elif event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            # Mouse clicked - hide tooltip immediately
            self._hide_tooltip()

        elif event.type() == QEvent.Leave:
            # Mouse left widget, hide tooltip
            self._hide_tooltip()

        return False

    def _show_tooltip(self) -> None:
        """Show tooltip for current item."""
        if not self.current_item or id(self.current_item) not in self.tooltip_data:
            return

        text, tooltip_type = self.tooltip_data[id(self.current_item)]

        # Hide any existing tooltip
        self._hide_tooltip()

        # Create new tooltip
        self.current_tooltip = CustomTooltip(
            self.widget.window(), text, tooltip_type, persistent=False
        )

        # Position and show tooltip
        tooltip_pos = TooltipHelper._calculate_tooltip_position(self.widget)
        self.current_tooltip.show_tooltip(tooltip_pos, duration=TOOLTIP_DURATION)

    def _hide_tooltip(self) -> None:
        """Hide current tooltip."""
        self.hover_timer.stop()
        self.current_item = None

        if self.current_tooltip:
            self.current_tooltip.hide()
            self.current_tooltip.deleteLater()
            self.current_tooltip = None

    def register_item(self, item, text: str, tooltip_type: str) -> None:
        """Register an item with custom tooltip data using item id as key."""
        self.tooltip_data[id(item)] = (text, tooltip_type)


class TooltipHelper:
    """Central tooltip management utility."""

    # Active tooltips tracking
    _active_tooltips: ClassVar[list[object]] = []
    _persistent_tooltips: ClassVar[dict[object, object]] = {}

    @classmethod
    def _get_cursor_position(cls, widget: QWidget) -> QPoint:
        """Get cursor position with fallback to widget center."""
        from PyQt5.QtGui import QCursor

        try:
            return QCursor.pos()
        except (AttributeError, RuntimeError):
            # Fallback to widget position if cursor position not available
            return widget.mapToGlobal(widget.rect().center())

    @classmethod
    def _calculate_tooltip_position(cls, widget: QWidget) -> QPoint:
        """Calculate tooltip position relative to cursor with offset."""
        global_pos = cls._get_cursor_position(widget)
        offset_x, offset_y = TOOLTIP_POSITION_OFFSET
        return QPoint(global_pos.x() + offset_x, global_pos.y() + offset_y)

    @classmethod
    def show_tooltip(
        cls,
        widget: QWidget,
        message: str,
        tooltip_type: str = TooltipType.DEFAULT,
        duration: int | None = None,
        persistent: bool = False,
    ) -> None:
        """Show a custom tooltip near the specified widget.

        Args:
            widget: The widget to show tooltip for
            message: Tooltip text
            tooltip_type: Type of tooltip (error, warning, info, success, default)
            duration: Duration in milliseconds (None for config default, 0 for no auto-hide)
            persistent: If True, tooltip behaves like Qt standard tooltip (show on hover)

        """
        try:
            if persistent:
                cls._setup_persistent_tooltip(widget, message, tooltip_type)
            else:
                cls._show_temporary_tooltip(widget, message, tooltip_type, duration)

        except Exception as e:
            logger.error("[TooltipHelper] Failed to show tooltip: %s", e)

    @classmethod
    def _show_temporary_tooltip(
        cls, widget: QWidget, message: str, tooltip_type: str, duration: int | None
    ) -> None:
        """Show a temporary tooltip that auto-hides."""
        # Clear any existing tooltip for this widget
        cls.clear_tooltips_for_widget(widget)

        # Create new tooltip
        tooltip = CustomTooltip(widget.window(), message, tooltip_type, persistent=False)

        # Calculate position and adjust to stay on screen
        tooltip_pos = cls._calculate_tooltip_position(widget)
        adjusted_pos = cls._adjust_position_to_screen(tooltip_pos, tooltip.size())

        # Show tooltip
        if duration is None:
            duration = TOOLTIP_DURATION

        tooltip.show_tooltip(adjusted_pos, duration)

        # Track active tooltip
        cls._active_tooltips.append((widget, tooltip))

        truncated = message[:50]
        suffix = "..." if len(message) > 50 else ""
        logger.debug("[TooltipHelper] Showed %s tooltip: %s%s", tooltip_type, truncated, suffix)

    @classmethod
    def _setup_persistent_tooltip(cls, widget: QWidget, message: str, tooltip_type: str) -> None:
        """Setup a persistent tooltip that shows on hover (like Qt standard)."""
        # Use widget id as key to support non-hashable widgets like QStandardItem
        widget_id = id(widget)

        # Remove any existing persistent tooltip for this widget
        if widget_id in cls._persistent_tooltips:
            old_tooltip = cls._persistent_tooltips[widget_id]
            try:
                old_tooltip.hide()
                old_tooltip.deleteLater()
            except RuntimeError:
                # Qt object already deleted
                pass

        # Create persistent tooltip
        tooltip = CustomTooltip(widget.window(), message, tooltip_type, persistent=True)
        cls._persistent_tooltips[widget_id] = tooltip

        # Setup mouse tracking
        widget.setMouseTracking(True)

        # Install event filter for hover detection
        tooltip_filter = WidgetTooltipFilter(widget, tooltip, widget)
        widget.installEventFilter(tooltip_filter)

        # Store filter reference to prevent garbage collection
        widget._tooltip_filter = tooltip_filter

    @classmethod
    def _show_persistent_tooltip(cls, widget: QWidget, tooltip: CustomTooltip) -> None:
        """Show persistent tooltip on hover."""
        try:
            # Check if widget and tooltip still exist
            widget_id = id(widget)
            if (
                widget_id not in cls._persistent_tooltips
                or cls._persistent_tooltips[widget_id] != tooltip
            ):
                return

            # Calculate position and adjust to stay on screen
            tooltip_pos = cls._calculate_tooltip_position(widget)
            adjusted_pos = cls._adjust_position_to_screen(tooltip_pos, tooltip.size())

            # Show tooltip
            tooltip.show_tooltip(adjusted_pos, duration=TOOLTIP_DURATION)

        except RuntimeError as e:
            # Qt object has been deleted - remove from tracking
            logger.debug("[TooltipHelper] Tooltip object deleted during show: %s", e)
            widget_id = id(widget)
            if widget_id in cls._persistent_tooltips:
                del cls._persistent_tooltips[widget_id]
        except Exception as e:
            logger.error("[TooltipHelper] Failed to show persistent tooltip: %s", e)

    @classmethod
    def setup_tooltip(
        cls, widget: QWidget, message: str, tooltip_type: str = TooltipType.DEFAULT
    ) -> None:
        """Setup a persistent tooltip for a widget (replacement for setToolTip).

        Args:
            widget: The widget to add tooltip to
            message: Tooltip text
            tooltip_type: Type of tooltip styling

        """
        cls._setup_persistent_tooltip(widget, message, tooltip_type)

    @classmethod
    def setup_action_tooltip(
        cls, action, message: str, tooltip_type: str = TooltipType.INFO, menu: QMenu | None = None
    ) -> None:
        """Setup a custom tooltip for QAction in a QMenu.

        Args:
            action: The QAction to add tooltip to
            message: Tooltip text
            tooltip_type: Type of tooltip styling
            menu: The QMenu containing the action (required for custom tooltips)

        Note:
            If menu is not provided, falls back to standard setToolTip()

        """
        if menu is None:
            # Fallback to standard tooltip
            action.setToolTip(message)
            return

        # Install event filter on menu if not already installed
        if not hasattr(menu, "_tooltip_filter"):
            menu._tooltip_filter = ActionTooltipFilter(menu)
            menu.installEventFilter(menu._tooltip_filter)

        # Register action with custom tooltip data
        menu._tooltip_filter.register_action(action, message, tooltip_type)

    @classmethod
    def setup_item_tooltip(
        cls,
        widget: QListWidget | QTableWidget,
        item,
        message: str,
        tooltip_type: str = TooltipType.INFO,
    ) -> None:
        """Setup a custom tooltip for a QListWidgetItem or QTableWidgetItem.

        Args:
            widget: The QListWidget or QTableWidget containing the item
            item: The item to add tooltip to
            message: Tooltip text
            tooltip_type: Type of tooltip styling

        """
        # Install event filter on widget viewport if not already installed
        if not hasattr(widget, "_item_tooltip_filter"):
            widget._item_tooltip_filter = ItemTooltipFilter(widget)
            widget.viewport().installEventFilter(widget._item_tooltip_filter)

        # Register item with custom tooltip data
        widget._item_tooltip_filter.register_item(item, message, tooltip_type)

    @classmethod
    def show_error_tooltip(cls, widget: QWidget, message: str, duration: int | None = None) -> None:
        """Show error-styled tooltip on widget."""
        cls.show_tooltip(widget, message, TooltipType.ERROR, duration)

    @classmethod
    def show_warning_tooltip(
        cls, widget: QWidget, message: str, duration: int | None = None
    ) -> None:
        """Show warning-styled tooltip on widget."""
        cls.show_tooltip(widget, message, TooltipType.WARNING, duration)

    @classmethod
    def show_info_tooltip(cls, widget: QWidget, message: str, duration: int | None = None) -> None:
        """Show info-styled tooltip on widget."""
        cls.show_tooltip(widget, message, TooltipType.INFO, duration)

    @classmethod
    def show_success_tooltip(
        cls, widget: QWidget, message: str, duration: int | None = None
    ) -> None:
        """Show success-styled tooltip on widget."""
        cls.show_tooltip(widget, message, TooltipType.SUCCESS, duration)

    @classmethod
    def clear_tooltips_for_widget(cls, widget: QWidget) -> None:
        """Clear all active tooltips for a specific widget."""
        # Clear temporary tooltips
        remaining_tooltips = []
        for w, t in cls._active_tooltips:
            if w == widget:
                try:
                    t.hide_tooltip()
                    t.deleteLater()
                except RuntimeError:
                    pass
            else:
                remaining_tooltips.append((w, t))
        cls._active_tooltips = remaining_tooltips

        # Clear persistent tooltips
        widget_id = id(widget)
        if widget_id in cls._persistent_tooltips:
            tooltip = cls._persistent_tooltips[widget_id]
            try:
                # Cancel any pending timer
                if hasattr(tooltip, "_timer_id") and tooltip._timer_id:
                    from oncutf.utils.shared.timer_manager import cancel_timer

                    cancel_timer(tooltip._timer_id)
                tooltip.hide()
                tooltip.deleteLater()
            except RuntimeError:
                # Qt object already deleted
                pass
            del cls._persistent_tooltips[widget_id]

    @classmethod
    def clear_all_tooltips(cls) -> None:
        """Clear all active tooltips."""
        # Clear temporary tooltips
        try:
            for _widget, tooltip in cls._active_tooltips:
                tooltip.hide_tooltip()
        except RuntimeError:
            # Qt objects may have been deleted already
            pass
        cls._active_tooltips.clear()

        # Clear persistent tooltips
        try:
            for tooltip in cls._persistent_tooltips.values():
                # Cancel any pending timer
                if hasattr(tooltip, "_timer_id") and tooltip._timer_id:
                    from oncutf.utils.shared.timer_manager import cancel_timer

                    cancel_timer(tooltip._timer_id)
                tooltip.hide()
                tooltip.deleteLater()
        except RuntimeError:
            # Qt objects may have been deleted already
            pass
        cls._persistent_tooltips.clear()

    @classmethod
    def _adjust_position_to_screen(cls, position: QPoint, tooltip_size) -> QPoint:
        """Adjust tooltip position to stay within screen bounds."""
        try:
            # Use modern QScreen API instead of deprecated QDesktopWidget
            app = QApplication.instance()
            if not app or not hasattr(app, "primaryScreen"):
                return position

            # Find the screen containing the tooltip position
            target_screen = None
            for screen in app.screens():  # type: ignore[attr-defined]
                if screen.geometry().contains(position):
                    target_screen = screen
                    break

            # If not found on any screen, use primary screen
            if not target_screen:
                target_screen = app.primaryScreen()  # type: ignore[attr-defined]
                if not target_screen:
                    return position

            screen_geometry = target_screen.availableGeometry()

            # Adjust X position
            if position.x() + tooltip_size.width() > screen_geometry.right():
                position.setX(screen_geometry.right() - tooltip_size.width())
            if position.x() < screen_geometry.left():
                position.setX(screen_geometry.left())

            # Adjust Y position
            if position.y() + tooltip_size.height() > screen_geometry.bottom():
                position.setY(position.y() - tooltip_size.height() - 30)  # Show above widget
            if position.y() < screen_geometry.top():
                position.setY(screen_geometry.top())

            return position
        except Exception as e:
            logger.debug("[TooltipHelper] Could not adjust position to screen: %s", e)
            return position


class TreeViewTooltipFilter(QObject):
    """Event filter for QTreeView/QTableView to show custom themed tooltips.

    This filter intercepts tooltip events and replaces default Qt tooltips
    with CustomTooltip widgets that match the application theme.

    Usage:
        tree_view = QTreeView()
        tooltip_filter = TreeViewTooltipFilter(tree_view, parent=tree_view)
        tree_view.viewport().installEventFilter(tooltip_filter)

    """

    def __init__(self, view_widget, parent: QObject | None = None, tooltip_type: str = TooltipType.INFO):
        """Initialize tooltip filter for tree/table view.

        Args:
            view_widget: The QTreeView or QTableView to attach tooltip handling to
            parent: Optional parent QObject
            tooltip_type: Type of tooltip styling (default: INFO)

        """
        super().__init__(parent)
        self.view_widget = view_widget
        self.tooltip_type = tooltip_type
        self._last_row = None  # Track last row to detect mouse moves to different rows

    def eventFilter(self, obj: QObject, event) -> bool:
        """Filter events to show custom tooltips.

        Args:
            obj: The object that received the event
            event: The event to filter

        Returns:
            True if event was handled, False otherwise

        """
        # Safety check: widget might be deleted during shutdown
        try:
            viewport = self.view_widget.viewport()
        except RuntimeError:
            # Widget has been deleted (C++ object destroyed)
            return False

        if obj != viewport:
            return False

        # Handle mouse leave - clear tooltips when mouse leaves the widget
        if event.type() == QEvent.Leave:
            TooltipHelper.clear_tooltips_for_widget(self.view_widget)
            self._last_row = None
            return False

        # Handle mouse move - clear tooltip if moved to different row (not column)
        if event.type() == QEvent.MouseMove:
            try:
                pos = event.pos()
                current_index = self.view_widget.indexAt(pos)

                # Extract row from index (ignore column changes)
                current_row = current_index.row() if current_index.isValid() else None

                # If we moved to a different row, clear existing tooltips
                if current_row != self._last_row:
                    TooltipHelper.clear_tooltips_for_widget(self.view_widget)
                    self._last_row = current_row
            except RuntimeError:
                return False
            return False

        # Handle ToolTip event
        if event.type() == QEvent.ToolTip:
            from oncutf.core.pyqt_imports import QHelpEvent

            if not isinstance(event, QHelpEvent):
                return False

            # Get item at cursor position
            pos = event.pos()
            try:
                index = self.view_widget.indexAt(pos)
            except RuntimeError:
                # Widget deleted during event handling
                return False

            if not index.isValid():
                return False

            # Get tooltip text from model - use column 0 (key) for entire row
            # This ensures consistent tooltip across both key and value columns
            key_index = index.sibling(index.row(), 0)
            tooltip_text = key_index.data(Qt.ToolTipRole)
            current_row = index.row()

            if tooltip_text:
                # Only show tooltip if we're on a different row or no tooltip is showing
                # This prevents constant re-triggering on the same row
                if self._last_row != current_row:
                    # Show custom tooltip for new row
                    try:
                        TooltipHelper.show_tooltip(
                            self.view_widget,
                            tooltip_text,
                            tooltip_type=self.tooltip_type,
                            duration=5000,  # 5 seconds
                        )
                        self._last_row = current_row  # Update last row
                    except RuntimeError:
                        # Widget deleted during tooltip display
                        return False
                # Tooltip already showing for this row - do nothing, let it stay
                return True  # Event handled
            else:
                # No tooltip for this item - clear any existing tooltips
                TooltipHelper.clear_tooltips_for_widget(self.view_widget)
                self._last_row = None

            return False

        return False
