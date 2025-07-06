"""
Module: tooltip_helper.py

Author: Michael Economou
Date: 2025-07-06

This module provides centralized tooltip management with custom styling and
behavior. It supports both temporary tooltips (with auto-hide) and persistent
tooltips (that behave like Qt standard tooltips) for displaying tooltips with
different types (error, warning, info, success) and consistent styling across
the application.
Classes:
- CustomTooltip: Enhanced tooltip widget with custom styling
- TooltipHelper: Central management class for tooltip operations
- TooltipType: Constants for different tooltip types
- Convenience functions for easy tooltip display
"""
from typing import Optional, Tuple
from PyQt5.QtCore import QPoint, QTimer, Qt, QEvent
from PyQt5.QtWidgets import QApplication, QLabel, QWidget

from config import TOOLTIP_DURATION, TOOLTIP_POSITION_OFFSET
from utils.logger_helper import get_logger

logger = get_logger(__name__)


class TooltipType:
    """Tooltip type constants"""
    DEFAULT = "default"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"


class CustomTooltip(QLabel):
    """Custom tooltip widget with enhanced styling and behavior"""

    def __init__(self, parent: QWidget, text: str, tooltip_type: str = TooltipType.DEFAULT, persistent: bool = False):
        super().__init__(text, parent)
        self.tooltip_type = tooltip_type
        self.persistent = persistent
        self._timer = QTimer()
        self._timer.timeout.connect(self.hide_tooltip)
        self._setup_ui()

    def _setup_ui(self):
        """Setup tooltip UI and styling"""
        # Set window flags for tooltip behavior
        if self.persistent:
            # Persistent tooltips behave like Qt standard tooltips
            self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint) # type: ignore[attr-defined]
        else:
            # Temporary tooltips with auto-hide
            self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint) # type: ignore[attr-defined]

        # Apply styling based on tooltip type
        style_classes = {
            TooltipType.ERROR: "ErrorTooltip",
            TooltipType.WARNING: "WarningTooltip",
            TooltipType.INFO: "InfoTooltip",
            TooltipType.SUCCESS: "SuccessTooltip",
            TooltipType.DEFAULT: "InfoTooltip"  # Default to info style
        }.get(self.tooltip_type, "InfoTooltip")

        self.setProperty("class", style_classes)
        self.setWordWrap(True)
        self.setMargin(2)  # Reduced from 3 to 2 pixels

        # Set size constraints for better text layout
        self.setMinimumWidth(180)  # Increased from 120 to 180 pixels for longer lines
        self.setMaximumWidth(400)  # Maximum width to prevent too wide tooltips

        # Make sure tooltip adjusts to content
        self.adjustSize()

    def show_tooltip(self, position: QPoint, duration: Optional[int] = None):
        """Show tooltip at specific position for specified duration"""
        if not self.persistent and duration is not None and duration > 0:
            self._timer.start(duration)

        self.move(position)
        self.show()
        self.raise_()

    def hide_tooltip(self) -> None:
        """Hide the tooltip"""
        self._timer.stop()
        self.hide()


class TooltipHelper:
    """Central tooltip management utility"""

    # Active tooltips tracking
    _active_tooltips: list = []
    _persistent_tooltips: dict = {}  # widget -> tooltip mapping for persistent tooltips

    @classmethod
    def show_tooltip(cls,
                    widget: QWidget,
                    message: str,
                    tooltip_type: str = TooltipType.DEFAULT,
                    duration: Optional[int] = None,
                    persistent: bool = False) -> None:
        """
        Show a custom tooltip near the specified widget

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
            logger.error(f"[TooltipHelper] Failed to show tooltip: {e}")

    @classmethod
    def _show_temporary_tooltip(cls, widget: QWidget, message: str, tooltip_type: str, duration: Optional[int]) -> None:
        """Show a temporary tooltip that auto-hides"""
        # Clear any existing tooltip for this widget
        cls.clear_tooltips_for_widget(widget)

        # Create new tooltip
        tooltip = CustomTooltip(widget.window(), message, tooltip_type, persistent=False)

                        # Calculate position relative to cursor for better UX
        from PyQt5.QtGui import QCursor
        try:
            # Get current cursor position
            global_pos = QCursor.pos()
        except:
            # Fallback to widget position if cursor position not available
            global_pos = widget.mapToGlobal(widget.rect().center())

        offset_x, offset_y = TOOLTIP_POSITION_OFFSET
        tooltip_pos = QPoint(global_pos.x() + offset_x, global_pos.y() + offset_y)

        # Adjust position to stay on screen
        adjusted_pos = cls._adjust_position_to_screen(tooltip_pos, tooltip.size())

        # Show tooltip
        if duration is None:
            duration = TOOLTIP_DURATION

        tooltip.show_tooltip(adjusted_pos, duration)

        # Track active tooltip
        cls._active_tooltips.append((widget, tooltip))

        logger.debug(f"[TooltipHelper] Showed {tooltip_type} tooltip: {message[:50]}{'...' if len(message) > 50 else ''}")

    @classmethod
    def _setup_persistent_tooltip(cls, widget: QWidget, message: str, tooltip_type: str) -> None:
        """Setup a persistent tooltip that shows on hover (like Qt standard)"""
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

        # Setup hover events
        widget.setMouseTracking(True)

                # Store original event handlers
        original_enter = getattr(widget, 'enterEvent', None)
        original_leave = getattr(widget, 'leaveEvent', None)

        # Store timer ID for cleanup
        tooltip._timer_id = None

        def enter_event(event: QEvent):
            if original_enter:
                original_enter(event)
            # Schedule tooltip show with 600ms delay using global timer manager
            from utils.timer_manager import schedule_ui_update
            tooltip._timer_id = schedule_ui_update(
                lambda: cls._show_persistent_tooltip(widget, tooltip),
                delay=600,
                timer_id=f"tooltip_show_{id(widget)}"
            )

        def leave_event(event: QEvent):
            try:
                if original_leave:
                    original_leave(event)
                # Cancel the timer if still running
                if hasattr(tooltip, '_timer_id') and tooltip._timer_id:
                    from utils.timer_manager import cancel_timer
                    cancel_timer(tooltip._timer_id)
                    tooltip._timer_id = None
                # Check if tooltip still exists before trying to hide it
                widget_id = id(widget)
                if widget_id in cls._persistent_tooltips and cls._persistent_tooltips[widget_id] == tooltip:
                    tooltip.hide()
            except RuntimeError as e:
                # Qt object has been deleted - remove from tracking
                logger.debug(f"[TooltipHelper] Tooltip object deleted, cleaning up: {e}")
                widget_id = id(widget)
                if widget_id in cls._persistent_tooltips:
                    del cls._persistent_tooltips[widget_id]

        # Replace event handlers
        widget.enterEvent = enter_event  # type: ignore
        widget.leaveEvent = leave_event  # type: ignore

    @classmethod
    def _show_persistent_tooltip(cls, widget: QWidget, tooltip: CustomTooltip) -> None:
        """Show persistent tooltip on hover"""
        try:
            # Check if widget and tooltip still exist
            widget_id = id(widget)
            if widget_id not in cls._persistent_tooltips or cls._persistent_tooltips[widget_id] != tooltip:
                return

            # Calculate position relative to cursor for better UX
            from PyQt5.QtGui import QCursor
            try:
                # Get current cursor position
                global_pos = QCursor.pos()
            except:
                # Fallback to widget position if cursor position not available
                global_pos = widget.mapToGlobal(widget.rect().center())

            offset_x, offset_y = TOOLTIP_POSITION_OFFSET
            tooltip_pos = QPoint(global_pos.x() + offset_x, global_pos.y() + offset_y)

            # Adjust position to stay on screen
            adjusted_pos = cls._adjust_position_to_screen(tooltip_pos, tooltip.size())

            # Show tooltip
            tooltip.move(adjusted_pos)
            tooltip.show()
            tooltip.raise_()

        except RuntimeError as e:
            # Qt object has been deleted - remove from tracking
            logger.debug(f"[TooltipHelper] Tooltip object deleted during show: {e}")
            widget_id = id(widget)
            if widget_id in cls._persistent_tooltips:
                del cls._persistent_tooltips[widget_id]
        except Exception as e:
            logger.error(f"[TooltipHelper] Failed to show persistent tooltip: {e}")

    @classmethod
    def setup_tooltip(cls, widget: QWidget, message: str, tooltip_type: str = TooltipType.DEFAULT) -> None:
        """
        Setup a persistent tooltip for a widget (replacement for setToolTip)

        Args:
            widget: The widget to add tooltip to
            message: Tooltip text
            tooltip_type: Type of tooltip styling
        """
        cls._setup_persistent_tooltip(widget, message, tooltip_type)

    @classmethod
    def show_error_tooltip(cls, widget: QWidget, message: str, duration: Optional[int] = None) -> None:
        cls.show_tooltip(widget, message, TooltipType.ERROR, duration)

    @classmethod
    def show_warning_tooltip(cls, widget: QWidget, message: str, duration: Optional[int] = None) -> None:
        cls.show_tooltip(widget, message, TooltipType.WARNING, duration)

    @classmethod
    def show_info_tooltip(cls, widget: QWidget, message: str, duration: Optional[int] = None) -> None:
        cls.show_tooltip(widget, message, TooltipType.INFO, duration)

    @classmethod
    def show_success_tooltip(cls, widget: QWidget, message: str, duration: Optional[int] = None) -> None:
        cls.show_tooltip(widget, message, TooltipType.SUCCESS, duration)

    @classmethod
    def clear_tooltips_for_widget(cls, widget: QWidget) -> None:
        """Clear all active tooltips for a specific widget"""
        # Clear temporary tooltips
        cls._active_tooltips = [(w, t) for w, t in cls._active_tooltips if w != widget]

        # Clear persistent tooltips
        widget_id = id(widget)
        if widget_id in cls._persistent_tooltips:
            tooltip = cls._persistent_tooltips[widget_id]
            try:
                # Cancel any pending timer
                if hasattr(tooltip, '_timer_id') and tooltip._timer_id:
                    from utils.timer_manager import cancel_timer
                    cancel_timer(tooltip._timer_id)
                tooltip.hide()
                tooltip.deleteLater()
            except RuntimeError:
                # Qt object already deleted
                pass
            del cls._persistent_tooltips[widget_id]

    @classmethod
    def clear_all_tooltips(cls) -> None:
        """Clear all active tooltips"""
        # Clear temporary tooltips
        try:
            for widget, tooltip in cls._active_tooltips:
                tooltip.hide_tooltip()
        except RuntimeError:
            # Qt objects may have been deleted already
            pass
        cls._active_tooltips.clear()

        # Clear persistent tooltips
        try:
            for tooltip in cls._persistent_tooltips.values():
                # Cancel any pending timer
                if hasattr(tooltip, '_timer_id') and tooltip._timer_id:
                    from utils.timer_manager import cancel_timer
                    cancel_timer(tooltip._timer_id)
                tooltip.hide()
                tooltip.deleteLater()
        except RuntimeError:
            # Qt objects may have been deleted already
            pass
        cls._persistent_tooltips.clear()

    @classmethod
    def _adjust_position_to_screen(cls, position: QPoint, tooltip_size) -> QPoint:
        """Adjust tooltip position to stay within screen bounds"""
        try:
            # Use modern QScreen API instead of deprecated QDesktopWidget
            app = QApplication.instance()
            if not app or not hasattr(app, 'primaryScreen'):
                return position

            # Find the screen containing the tooltip position
            target_screen = None
            for screen in app.screens(): # type: ignore[attr-defined]
                if screen.geometry().contains(position):
                    target_screen = screen
                    break

            # If not found on any screen, use primary screen
            if not target_screen:
                target_screen = app.primaryScreen() # type: ignore[attr-defined]
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
            logger.debug(f"[TooltipHelper] Could not adjust position to screen: {e}")
            return position


# =====================================
# Global Convenience Functions
# =====================================

def show_tooltip(widget: QWidget, message: str, tooltip_type: str = TooltipType.DEFAULT, duration: Optional[int] = None) -> None:
    """Global convenience function to show tooltip"""
    TooltipHelper.show_tooltip(widget, message, tooltip_type, duration)

def show_error_tooltip(widget: QWidget, message: str, duration: Optional[int] = None) -> None:
    """Global convenience function to show error tooltip"""
    TooltipHelper.show_error_tooltip(widget, message, duration)

def show_warning_tooltip(widget: QWidget, message: str, duration: Optional[int] = None) -> None:
    """Global convenience function to show warning tooltip"""
    TooltipHelper.show_warning_tooltip(widget, message, duration)

def show_info_tooltip(widget: QWidget, message: str, duration: Optional[int] = None) -> None:
    """Global convenience function to show info tooltip"""
    TooltipHelper.show_info_tooltip(widget, message, duration)

def show_success_tooltip(widget: QWidget, message: str, duration: Optional[int] = None) -> None:
    """Global convenience function to show success tooltip"""
    TooltipHelper.show_success_tooltip(widget, message, duration)

def setup_tooltip(widget: QWidget, message: str, tooltip_type: str = TooltipType.DEFAULT) -> None:
    """Global convenience function to setup persistent tooltip (replacement for setToolTip)"""
    TooltipHelper.setup_tooltip(widget, message, tooltip_type)
