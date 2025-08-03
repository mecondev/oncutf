"""Drag Visual Manager - Visual feedback for drag & drop operations.

This module provides visual feedback for drag & drop operations including:
- Legal/illegal drop zone indicators
- File/folder type cursors
- Modifier state indicators (normal/extended metadata)
- Dynamic cursor and overlay management

Features:
- Icon-based cursors with state awareness
- Real-time drop zone validation
- Keyboard modifier detection
- Theme-aware icons from feather set

Author: Michael Economou
Date: 2025-05-31
"""

import os
from enum import Enum

from config import ICON_SIZES
from core.pyqt_imports import QApplication, QColor, QCursor, QIcon, QPainter, QPixmap, Qt, QWidget
from utils.icons_loader import get_menu_icon
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class DragType(Enum):
    """Types of items being dragged"""

    FILE = "file"
    FOLDER = "folder"
    MULTIPLE = "multiple"


class DropZoneState(Enum):
    """States of drop zones"""

    VALID = "valid"
    INVALID = "invalid"
    NEUTRAL = "neutral"


class ModifierState(Enum):
    """Keyboard modifier states for drag operations"""

    NORMAL = "normal"  # No modifiers - Replace + Shallow
    SHIFT = "shift"  # Shift only - Merge + Shallow
    CTRL = "ctrl"  # Ctrl only - Replace + Recursive
    CTRL_SHIFT = "ctrl_shift"  # Ctrl+Shift - Merge + Recursive


class DragVisualManager:
    """
    Manages visual feedback for drag & drop operations.

    Provides dynamic cursors, icons, and visual indicators based on:
    - Type of content being dragged (file/folder/multiple)
    - Current drop zone validity (legal/illegal)
    - Keyboard modifier states (normal/extended metadata)
    """

    _instance: "DragVisualManager | None" = None

    def __init__(self):
        # Ensure singleton
        if DragVisualManager._instance is not None:
            raise RuntimeError("DragVisualManager is a singleton. Use get_instance()")
        DragVisualManager._instance = self

        # Current drag state
        self._drag_type: DragType | None = None
        self._drop_zone_state: DropZoneState = DropZoneState.NEUTRAL
        self._modifier_state: ModifierState = ModifierState.NORMAL
        self._original_cursor: QCursor | None = None
        self._drag_source: str | None = None

        # Icon cache for different states
        self._icon_cache: dict[str, QIcon] = {}
        self._cursor_cache: dict[str, QCursor] = {}

        # Clear cache on initialization
        self._clear_cache()

    def _clear_cache(self) -> None:
        """Clear icon and cursor caches."""
        self._icon_cache.clear()
        self._cursor_cache.clear()

    @classmethod
    def get_instance(cls) -> "DragVisualManager":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # =====================================
    # Drag State Management
    # =====================================

    def start_drag_visual(
        self, drag_type: DragType, source_info: str, drag_source: str = None
    ) -> None:
        """
        Start visual feedback for a drag operation.

        Args:
            drag_type: Type of content being dragged
            source_info: Description of the source (e.g., filename, folder path)
            drag_source: Source widget identifier (e.g., "file_table", "file_tree")
        """
        self._drag_type = drag_type
        self._drag_source = drag_source

        # Start with VALID state to show action icons immediately (File Explorer UX)
        if drag_source in ("file_tree", "file_table"):
            self._drop_zone_state = DropZoneState.VALID
        else:
            self._drop_zone_state = DropZoneState.NEUTRAL

        self._modifier_state = self._detect_modifier_state()

        # Clear cursor cache and update cursor
        self._clear_cache()
        self._update_cursor()

    def end_drag_visual(self) -> None:
        """End visual feedback for drag operation."""
        if self._drag_type is not None:
            # Restore original cursor
            self._restore_cursor()

            # Clear state
            self._drag_type = None
            self._drag_source = None
            self._drop_zone_state = DropZoneState.NEUTRAL
            self._modifier_state = ModifierState.NORMAL

            # Clear cache
            self._clear_cache()

    def update_drop_zone_state(self, state: DropZoneState) -> None:
        """
        Update drop zone state and refresh cursor.

        Args:
            state: New drop zone state
        """
        if self._drop_zone_state != state:
            self._drop_zone_state = state
            self._clear_cache()
            self._update_cursor()

    def update_modifier_state(self) -> None:
        """Update modifier state and refresh cursor if needed."""
        new_state = self._detect_modifier_state()
        if self._modifier_state != new_state:
            self._modifier_state = new_state
            self._clear_cache()
            self._update_cursor()

    def update_drag_feedback_for_widget(self, source_widget, drag_source: str) -> bool:
        """
        Update drag feedback based on cursor position - common logic for all widgets.

        Args:
            source_widget: The widget that started the drag (FileTreeView or FileTableView)
            drag_source: String identifier ("file_tree" or "file_table")

        Returns:
            bool: True to continue drag, False to end drag
        """
        # Update modifier state first (for Ctrl/Shift changes during drag)
        update_modifier_state()

        # Get widget under cursor
        widget_under_cursor = QApplication.widgetAt(QCursor.pos())
        if not widget_under_cursor:
            # Cursor is outside application window - this should end the drag
            return False  # Signal to end drag

        # Check if cursor is still over the source widget
        current_widget = widget_under_cursor
        still_over_source = False

        while current_widget:
            if current_widget is source_widget:
                still_over_source = True
                break
            current_widget = current_widget.parent()

        # If still over source widget, show NEUTRAL (can't drop on self)
        if still_over_source:
            update_drop_zone_state(DropZoneState.NEUTRAL)
            return True  # Continue drag

        # Check if over valid drop target
        is_valid = self.is_valid_drop_target(widget_under_cursor, drag_source)

        if is_valid:
            update_drop_zone_state(DropZoneState.VALID)
        else:
            update_drop_zone_state(DropZoneState.INVALID)

        return True  # Continue drag

    # =====================================
    # Cursor Management
    # =====================================

    def _update_cursor(self) -> None:
        """Update cursor based on current drag state."""
        if self._drag_type is None:
            return

        cursor_key = self._get_cursor_key()

        # Check cache first
        if cursor_key in self._cursor_cache:
            cursor = self._cursor_cache[cursor_key]
        else:
            cursor = self._create_cursor()
            self._cursor_cache[cursor_key] = cursor

        # Set cursor
        QApplication.setOverrideCursor(cursor)

    def _get_cursor_key(self) -> str:
        """Generate cache key for current cursor state."""
        return f"{self._drag_type.value}_{self._drop_zone_state.value}_{self._modifier_state.value}"

    def _create_cursor(self) -> QCursor:
        """Create cursor for current state."""
        # Choose base icon based on drag type
        if self._drag_type == DragType.FILE:
            base_icon = "file"
        elif self._drag_type == DragType.FOLDER:
            base_icon = "folder"
        else:  # MULTIPLE
            base_icon = "copy"

        # Check if dragging to metadata tree
        is_metadata_drop = self._drag_source is not None and self._drag_source == "file_table"

        # Choose action icons based on context
        if is_metadata_drop:
            if self._drop_zone_state == DropZoneState.INVALID:
                action_icons = ["x"]
            else:  # VALID or NEUTRAL
                action_icons = ["info"]
        else:
            # Normal file/folder drops
            if self._drop_zone_state == DropZoneState.INVALID:
                action_icons = ["x"]
            elif self._drop_zone_state == DropZoneState.VALID:
                # For files, ignore recursive modifiers (no subdirectories)
                if self._drag_type == DragType.FILE:
                    if self._modifier_state in [ModifierState.SHIFT, ModifierState.CTRL_SHIFT]:
                        if self._modifier_state == ModifierState.CTRL_SHIFT:
                            action_icons = ["plus", "layers"]  # Merge + Recursive
                        else:
                            action_icons = ["plus"]  # Merge + Shallow
                    else:
                        action_icons = ["download"]  # Replace + Shallow
                else:
                    # For folders and multiple items
                    if self._modifier_state == ModifierState.SHIFT:
                        action_icons = ["plus"]  # Merge + Shallow
                    elif self._modifier_state == ModifierState.CTRL:
                        action_icons = ["layers"]  # Replace + Recursive
                    elif self._modifier_state == ModifierState.CTRL_SHIFT:
                        action_icons = ["plus", "layers"]  # Merge + Recursive
                    else:
                        action_icons = ["download"]  # Replace + Shallow
            else:  # NEUTRAL - show preview
                if self._drag_type == DragType.FILE:
                    if self._modifier_state in [ModifierState.SHIFT, ModifierState.CTRL_SHIFT]:
                        if self._modifier_state == ModifierState.CTRL_SHIFT:
                            action_icons = ["plus", "layers"]
                        else:
                            action_icons = ["plus"]
                    else:
                        action_icons = ["download"]
                else:
                    if self._modifier_state == ModifierState.SHIFT:
                        action_icons = ["plus"]
                    elif self._modifier_state == ModifierState.CTRL:
                        action_icons = ["layers"]
                    elif self._modifier_state == ModifierState.CTRL_SHIFT:
                        action_icons = ["plus", "layers"]
                    else:
                        action_icons = ["download"]

        return self._create_composite_cursor(base_icon, action_icons)

    def _create_composite_cursor(self, base_icon: str, action_icons: list) -> QCursor:
        """
        Create a composite cursor with base + action icons.

        Args:
            base_icon: Name of base icon (file/folder/copy)
            action_icons: List of action icon names (e.g., ["plus", "layers"])
        """
        # Create wider canvas for multiple action icons
        canvas_width = 48 if len(action_icons) <= 1 else 70
        pixmap = QPixmap(canvas_width, 48)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw base icon
        base_qicon = get_menu_icon(base_icon)
        if not base_qicon.isNull():
            base_pixmap = base_qicon.pixmap(ICON_SIZES["LARGE"], ICON_SIZES["LARGE"])
            painter.drawPixmap(4, 8, base_pixmap)

        # Draw action icons side by side
        if action_icons:
            icon_size = ICON_SIZES["MEDIUM"]
            start_x = 24 if len(action_icons) <= 1 else 26

            for i, action_icon in enumerate(action_icons):
                if action_icon is None:
                    continue

                action_qicon = get_menu_icon(action_icon)
                if not action_qicon.isNull():
                    action_pixmap = action_qicon.pixmap(icon_size, icon_size)

                    # Apply color overlays for visual feedback
                    if action_icon == "x":
                        # Red for invalid zones
                        colored_pixmap = QPixmap(action_pixmap.size())
                        colored_pixmap.fill(Qt.transparent)

                        color_painter = QPainter(colored_pixmap)
                        color_painter.setRenderHint(QPainter.Antialiasing)
                        color_painter.drawPixmap(0, 0, action_pixmap)
                        color_painter.setCompositionMode(QPainter.CompositionMode_SourceAtop)
                        color_painter.fillRect(colored_pixmap.rect(), QColor(220, 68, 84))
                        color_painter.end()
                        action_pixmap = colored_pixmap

                    elif (
                        action_icon in ["download", "download-cloud"]
                        and self._drag_source == "file_table"
                    ):
                        # Green for metadata drops
                        colored_pixmap = QPixmap(action_pixmap.size())
                        colored_pixmap.fill(Qt.transparent)

                        color_painter = QPainter(colored_pixmap)
                        color_painter.setRenderHint(QPainter.Antialiasing)
                        color_painter.drawPixmap(0, 0, action_pixmap)
                        color_painter.setCompositionMode(QPainter.CompositionMode_SourceAtop)
                        color_painter.fillRect(colored_pixmap.rect(), QColor(40, 167, 69))
                        color_painter.end()
                        action_pixmap = colored_pixmap

                    elif action_icon == "info":
                        # Color based on modifier state
                        colored_pixmap = QPixmap(action_pixmap.size())
                        colored_pixmap.fill(Qt.transparent)

                        color_painter = QPainter(colored_pixmap)
                        color_painter.setRenderHint(QPainter.Antialiasing)
                        color_painter.drawPixmap(0, 0, action_pixmap)

                        if self._modifier_state == ModifierState.SHIFT:
                            color = QColor(255, 140, 0)  # Orange for extended metadata
                        else:
                            color = QColor(46, 204, 113)  # Green for fast metadata

                        color_painter.setCompositionMode(QPainter.CompositionMode_SourceAtop)
                        color_painter.fillRect(colored_pixmap.rect(), color)
                        color_painter.end()
                        action_pixmap = colored_pixmap

                    # Position icons with minimal spacing
                    if len(action_icons) > 1:
                        x_pos = start_x + (i * (icon_size - 4))  # Overlap to reduce visual spacing
                    else:
                        x_pos = start_x
                    y_pos = 24
                    painter.drawPixmap(x_pos, y_pos, action_pixmap)

        painter.end()

        # Create cursor with adjusted hotspot
        hotspot_x = 12 if canvas_width <= 48 else 16
        return QCursor(pixmap, hotspot_x, 12)

    def _restore_cursor(self) -> None:
        """Restore the original cursor with cleanup."""
        # Remove all override cursors
        cursor_count = 0
        while QApplication.overrideCursor() and cursor_count < 10:
            QApplication.restoreOverrideCursor()
            cursor_count += 1

        # Force set to default cursor if still stuck
        if QApplication.overrideCursor():
            QApplication.setOverrideCursor(QCursor(Qt.ArrowCursor))
            QApplication.restoreOverrideCursor()

    # =====================================
    # State Detection
    # =====================================

    def _detect_modifier_state(self) -> ModifierState:
        """Detect current keyboard modifier state."""
        modifiers = QApplication.keyboardModifiers()

        is_ctrl = bool(modifiers & Qt.ControlModifier)
        is_shift = bool(modifiers & Qt.ShiftModifier)

        # Special handling for metadata drops (file_table -> metadata_tree)
        if self._drag_source == "file_table":
            # For metadata drops, only Shift matters (ignore Ctrl)
            if is_shift:
                result = ModifierState.SHIFT  # Extended metadata
            else:
                result = ModifierState.NORMAL  # Fast metadata
            return result

        # Normal drag operations (file/folder drops)
        # Check for Shift+Ctrl combination first (highest priority)
        if is_ctrl and is_shift:
            result = ModifierState.CTRL_SHIFT  # Ctrl+Shift = Merge + Recursive
        elif is_shift:
            result = ModifierState.SHIFT  # Shift only = Merge + Shallow
        elif is_ctrl:
            result = ModifierState.CTRL  # Ctrl only = Replace + Recursive
        else:
            result = ModifierState.NORMAL  # No modifiers = Replace + Shallow

        return result

    def get_drag_type_from_path(self, path: str) -> DragType:
        """
        Determine drag type from file path.

        Args:
            path: Path to analyze

        Returns:
            Appropriate DragType
        """
        if os.path.isdir(path):
            return DragType.FOLDER
        else:
            return DragType.FILE

    def is_valid_drop_target(self, widget: QWidget, drag_source: str) -> bool:
        """
        Check if widget is a valid drop target for the given drag source.
        Walks up the parent hierarchy to find valid targets.

        Args:
            widget: Widget to check (can be child widget)
            drag_source: Source of the drag operation

        Returns:
            True if valid drop target
        """
        if widget is None:
            return False

        # Walk up the parent hierarchy to find valid targets
        current_widget = widget
        while current_widget:
            widget_class = current_widget.__class__.__name__

            # FileTreeView can only drop on FileTableView
            if drag_source == "file_tree":
                if widget_class == "FileTableView":
                    return True

            # FileTableView can only drop on MetadataTreeView
            elif drag_source == "file_table":
                if widget_class == "MetadataTreeView":
                    return True

            # Move to parent widget
            current_widget = current_widget.parent()

        return False

    # =====================================
    # Icon Utilities
    # =====================================

    def get_status_icon(self, state: DropZoneState) -> QIcon:
        """Get icon for drop zone state."""
        icon_map = {
            DropZoneState.VALID: "check-circle",
            DropZoneState.INVALID: "x-circle",
            DropZoneState.NEUTRAL: "target",
        }

        icon_name = icon_map.get(state, "target")
        return get_menu_icon(icon_name)

    def get_modifier_icon(self, state: ModifierState) -> QIcon:
        """Get icon for modifier state."""
        icon_map = {
            ModifierState.NORMAL: "check",
            ModifierState.SHIFT: "plus",
            ModifierState.CTRL: "arrow-down",
            ModifierState.CTRL_SHIFT: "plus-circle",
        }

        icon_name = icon_map.get(state, "check")
        return get_menu_icon(icon_name)


# Global convenience functions
def start_drag_visual(drag_type: DragType, source_info: str, drag_source: str = None) -> None:
    """Start visual feedback for drag operation."""
    DragVisualManager.get_instance().start_drag_visual(drag_type, source_info, drag_source)


def end_drag_visual() -> None:
    """End visual feedback for drag operation."""
    DragVisualManager.get_instance().end_drag_visual()


def update_drop_zone_state(state: DropZoneState) -> None:
    """Update drop zone state."""
    DragVisualManager.get_instance().update_drop_zone_state(state)


def update_modifier_state() -> None:
    """Update modifier state."""
    DragVisualManager.get_instance().update_modifier_state()


def is_valid_drop_target(widget: QWidget, drag_source: str) -> bool:
    """Check if widget is valid drop target."""
    return DragVisualManager.get_instance().is_valid_drop_target(widget, drag_source)


def update_drag_feedback_for_widget(source_widget, drag_source: str) -> bool:
    """
    Update drag feedback for a widget - convenience function.

    Args:
        source_widget: The widget that started the drag
        drag_source: String identifier ("file_tree" or "file_table")

    Returns:
        bool: True to continue drag, False to end drag
    """
    return DragVisualManager.get_instance().update_drag_feedback_for_widget(
        source_widget, drag_source
    )
