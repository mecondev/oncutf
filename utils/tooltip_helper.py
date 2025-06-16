"""
Module: tooltip_helper.py

Author: Michael Economou
Date: 2025-06-16

This module provides centralized tooltip management with custom styling and
configurable duration for the oncutf application. It offers a unified system
for displaying tooltips with different types (error, warning, info, success)
and consistent styling that matches the application theme.

Contains:
- CustomTooltip: Enhanced tooltip widget with custom styling
- TooltipHelper: Central management class for tooltip operations
- TooltipType: Constants for different tooltip types
- Convenience functions for easy tooltip display
"""

from typing import Optional, Union
from PyQt5.QtWidgets import QWidget, QLabel, QApplication
from PyQt5.QtCore import QTimer, Qt, QPoint
from PyQt5.QtGui import QCursor
import logging

logger = logging.getLogger(__name__)


class TooltipType:
    """Tooltip type constants"""
    DEFAULT = "default"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"


class CustomTooltip(QLabel):
    """Custom tooltip widget with enhanced styling and behavior"""

    def __init__(self, parent: QWidget, text: str, tooltip_type: str = TooltipType.DEFAULT):
        super().__init__(text, parent)
        self.tooltip_type = tooltip_type
        self._setup_ui()
        self._timer = QTimer()
        self._timer.timeout.connect(self.hide_tooltip)

    def _setup_ui(self) -> None:
        """Setup tooltip UI and styling"""
        # Set window flags for tooltip behavior
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # Apply styling based on type
        style_class = {
            TooltipType.ERROR: "ErrorTooltip",
            TooltipType.WARNING: "WarningTooltip",
            TooltipType.INFO: "InfoTooltip",
            TooltipType.SUCCESS: "SuccessTooltip",
            TooltipType.DEFAULT: "InfoTooltip"  # Default to info style
        }.get(self.tooltip_type, "InfoTooltip")

        self.setProperty("class", style_class)
        self.setStyleSheet(f"QLabel {{ qproperty-class: '{style_class}'; }}")

        # Make sure tooltip adjusts to content
        self.adjustSize()

    def show_at_position(self, position: QPoint, duration: int = 2000) -> None:
        """Show tooltip at specific position for specified duration"""
        self.move(position)
        self.show()
        self.raise_()

        # Start hide timer
        self._timer.start(duration)

    def hide_tooltip(self) -> None:
        """Hide the tooltip"""
        self._timer.stop()
        self.hide()
        self.deleteLater()


class TooltipHelper:
    """Central tooltip management utility"""

    # Active tooltips tracking
    _active_tooltips: list = []

    @classmethod
    def show_tooltip(cls,
                    widget: QWidget,
                    message: str,
                    tooltip_type: str = TooltipType.DEFAULT,
                    duration: int = None,
                    offset: tuple = (10, -25)) -> None:
        """
        Show a custom tooltip near the specified widget

        Args:
            widget: The widget to show tooltip for
            message: Tooltip text
            tooltip_type: Type of tooltip (error, warning, info, success, default)
            duration: Duration in milliseconds (None uses config default)
            offset: (x, y) offset from widget position
        """
        try:
            # Get duration from config if not specified
            if duration is None:
                from config import TOOLTIP_DURATION
                duration = TOOLTIP_DURATION

            # Clear any existing tooltips for this widget
            cls.clear_tooltips_for_widget(widget)

            # Create tooltip
            tooltip = CustomTooltip(widget.window(), message, tooltip_type)

            # Calculate position
            widget_pos = widget.mapToGlobal(QPoint(0, 0))
            tooltip_pos = QPoint(
                widget_pos.x() + offset[0],
                widget_pos.y() + offset[1]
            )

            # Ensure tooltip stays on screen
            tooltip_pos = cls._adjust_position_to_screen(tooltip_pos, tooltip.size())

            # Show tooltip
            tooltip.show_at_position(tooltip_pos, duration)

            # Track active tooltip
            cls._active_tooltips.append((widget, tooltip))

            logger.debug(f"[TooltipHelper] Showed {tooltip_type} tooltip: {message[:50]}{'...' if len(message) > 50 else ''}")

        except Exception as e:
            logger.error(f"[TooltipHelper] Failed to show tooltip: {e}")

    @classmethod
    def show_error_tooltip(cls, widget: QWidget, message: str, duration: int = None) -> None:
        """Show error tooltip - convenience method"""
        cls.show_tooltip(widget, message, TooltipType.ERROR, duration)

    @classmethod
    def show_warning_tooltip(cls, widget: QWidget, message: str, duration: int = None) -> None:
        """Show warning tooltip - convenience method"""
        cls.show_tooltip(widget, message, TooltipType.WARNING, duration)

    @classmethod
    def show_info_tooltip(cls, widget: QWidget, message: str, duration: int = None) -> None:
        """Show info tooltip - convenience method"""
        cls.show_tooltip(widget, message, TooltipType.INFO, duration)

    @classmethod
    def show_success_tooltip(cls, widget: QWidget, message: str, duration: int = None) -> None:
        """Show success tooltip - convenience method"""
        cls.show_tooltip(widget, message, TooltipType.SUCCESS, duration)

    @classmethod
    def clear_tooltips_for_widget(cls, widget: QWidget) -> None:
        """Clear all active tooltips for a specific widget"""
        to_remove = []
        for widget_ref, tooltip in cls._active_tooltips:
            if widget_ref == widget:
                tooltip.hide_tooltip()
                to_remove.append((widget_ref, tooltip))

        for item in to_remove:
            if item in cls._active_tooltips:
                cls._active_tooltips.remove(item)

    @classmethod
    def clear_all_tooltips(cls) -> None:
        """Clear all active tooltips"""
        for widget_ref, tooltip in cls._active_tooltips:
            tooltip.hide_tooltip()
        cls._active_tooltips.clear()

    @classmethod
    def _adjust_position_to_screen(cls, position: QPoint, tooltip_size) -> QPoint:
        """Adjust tooltip position to ensure it stays within screen bounds"""
        try:
            screen = QApplication.primaryScreen()
            if screen:
                screen_rect = screen.availableGeometry()

                # Adjust X position
                if position.x() + tooltip_size.width() > screen_rect.right():
                    position.setX(screen_rect.right() - tooltip_size.width())
                if position.x() < screen_rect.left():
                    position.setX(screen_rect.left())

                # Adjust Y position
                if position.y() + tooltip_size.height() > screen_rect.bottom():
                    position.setY(screen_rect.bottom() - tooltip_size.height())
                if position.y() < screen_rect.top():
                    position.setY(screen_rect.top())

        except Exception as e:
            logger.debug(f"[TooltipHelper] Could not adjust position to screen: {e}")

        return position


# Convenience functions for global access
def show_tooltip(widget: QWidget, message: str, tooltip_type: str = TooltipType.DEFAULT, duration: int = None) -> None:
    """Global convenience function for showing tooltips"""
    TooltipHelper.show_tooltip(widget, message, tooltip_type, duration)

def show_error_tooltip(widget: QWidget, message: str, duration: int = None) -> None:
    """Global convenience function for showing error tooltips"""
    TooltipHelper.show_error_tooltip(widget, message, duration)

def show_warning_tooltip(widget: QWidget, message: str, duration: int = None) -> None:
    """Global convenience function for showing warning tooltips"""
    TooltipHelper.show_warning_tooltip(widget, message, duration)

def show_info_tooltip(widget: QWidget, message: str, duration: int = None) -> None:
    """Global convenience function for showing info tooltips"""
    TooltipHelper.show_info_tooltip(widget, message, duration)

def show_success_tooltip(widget: QWidget, message: str, duration: int = None) -> None:
    """Global convenience function for showing success tooltips"""
    TooltipHelper.show_success_tooltip(widget, message, duration)
