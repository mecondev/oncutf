"""
Drag Visual Manager - Visual feedback for drag & drop operations

Author: Michael Economou
Date: 2025-06-10

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
"""

import os
from typing import Optional, Dict, Any
from enum import Enum

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QCursor, QPixmap, QPainter, QIcon, QColor
from PyQt5.QtWidgets import QApplication, QWidget

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
    NORMAL = "normal"          # No modifiers - Replace + Shallow
    SHIFT = "shift"            # Shift only - Merge + Shallow
    CTRL = "ctrl"              # Ctrl only - Replace + Recursive
    CTRL_SHIFT = "ctrl_shift"  # Ctrl+Shift - Merge + Recursive


class DragVisualManager:
    """
    Manages visual feedback for drag & drop operations.

    Provides dynamic cursors, icons, and visual indicators based on:
    - Type of content being dragged (file/folder/multiple)
    - Current drop zone validity (legal/illegal)
    - Keyboard modifier states (normal/extended metadata)
    """

    _instance: Optional['DragVisualManager'] = None

    def __init__(self):
        # Ensure singleton
        if DragVisualManager._instance is not None:
            raise RuntimeError("DragVisualManager is a singleton. Use get_instance()")
        DragVisualManager._instance = self

        # Current drag state
        self._drag_type: Optional[DragType] = None
        self._drop_zone_state: DropZoneState = DropZoneState.NEUTRAL
        self._modifier_state: ModifierState = ModifierState.NORMAL
        self._original_cursor: Optional[QCursor] = None

        # Icon cache for different states
        self._icon_cache: Dict[str, QIcon] = {}
        self._cursor_cache: Dict[str, QCursor] = {}

        # Clear cache on initialization to ensure fresh icons
        self._clear_cache()

        logger.debug("[DragVisualManager] Initialized", extra={"dev_only": True})

    def _clear_cache(self) -> None:
        """Clear icon and cursor caches to ensure fresh renders."""
        self._icon_cache.clear()
        self._cursor_cache.clear()
        logger.debug("[DragVisualManager] Cache cleared")

    @classmethod
    def get_instance(cls) -> 'DragVisualManager':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # =====================================
    # Drag State Management
    # =====================================

    def start_drag_visual(self, drag_type: DragType, source_info: str) -> None:
        """
        Start visual feedback for a drag operation.

        Args:
            drag_type: Type of content being dragged
            source_info: Information about the source (e.g., "4 files", "folder_path")
        """
        self._drag_type = drag_type
        self._drop_zone_state = DropZoneState.NEUTRAL
        self._modifier_state = self._detect_modifier_state()

        # Store original cursor
        self._original_cursor = QApplication.overrideCursor()

        # Set appropriate drag cursor
        self._update_cursor()

        logger.debug(f"[DragVisualManager] Visual drag started: {drag_type.value} from {source_info}")

    def end_drag_visual(self) -> None:
        """End visual feedback for drag operation."""
        if self._drag_type is None:
            return

        # Restore original cursor
        self._restore_cursor()

        # Reset state
        self._drag_type = None
        self._drop_zone_state = DropZoneState.NEUTRAL
        self._modifier_state = ModifierState.NORMAL
        self._original_cursor = None

        # Clear cache to ensure fresh icons next time
        self._clear_cache()

        logger.debug("[DragVisualManager] Visual drag ended")

    def update_drop_zone_state(self, state: DropZoneState) -> None:
        """
        Update the drop zone state and refresh visual feedback.

        Args:
            state: New drop zone state
        """
        if self._drop_zone_state != state:
            self._drop_zone_state = state
            self._update_cursor()
            logger.debug(f"[DragVisualManager] Drop zone state: {state.value}", extra={"dev_only": True})

    def update_modifier_state(self) -> None:
        """Update modifier state based on current keyboard state."""
        new_state = self._detect_modifier_state()
        if self._modifier_state != new_state:
            self._modifier_state = new_state
            self._update_cursor()
            logger.debug(f"[DragVisualManager] Modifier state: {new_state.value}", extra={"dev_only": True})

    # =====================================
    # Cursor Management
    # =====================================

    def _update_cursor(self) -> None:
        """Update cursor based on current state."""
        if self._drag_type is None:
            return

        cursor_key = self._get_cursor_key()

        if cursor_key in self._cursor_cache:
            cursor = self._cursor_cache[cursor_key]
        else:
            cursor = self._create_cursor()
            self._cursor_cache[cursor_key] = cursor

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

        # Choose action icon based on drop zone state and modifiers
        if self._drop_zone_state == DropZoneState.VALID:
            if self._modifier_state == ModifierState.SHIFT:
                action_icon = "plus"  # Merge + Shallow (Shift only)
            elif self._modifier_state == ModifierState.CTRL:
                action_icon = "arrow-down"  # Replace + Recursive (Ctrl only)
            elif self._modifier_state == ModifierState.CTRL_SHIFT:
                action_icon = "plus-circle"  # Merge + Recursive (Ctrl+Shift)
            else:
                action_icon = "check"  # Replace + Shallow (Normal - no modifiers)
        else:  # INVALID or NEUTRAL - both should show "x" since neutral isn't a valid drop target
            action_icon = "x"  # Invalid drop (including neutral zones)

        # Create composite cursor
        return self._create_composite_cursor(base_icon, action_icon)

    def _create_composite_cursor(self, base_icon: str, action_icon: str) -> QCursor:
        """
        Create a composite cursor with base + action icons.

        Args:
            base_icon: Name of base icon (file/folder/copy)
            action_icon: Name of action icon (check/x/move/file-plus)
        """
        # Create 48x48 pixmap (larger canvas for bigger icons)
        pixmap = QPixmap(48, 48)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw base icon (larger, center-left)
        base_qicon = get_menu_icon(base_icon)
        if not base_qicon.isNull():
            base_pixmap = base_qicon.pixmap(28, 28)  # Increased from 20x20
            painter.drawPixmap(4, 8, base_pixmap)

        # Draw action icon (smaller, bottom-right)
        action_qicon = get_menu_icon(action_icon)
        if not action_qicon.isNull():
            action_pixmap = action_qicon.pixmap(18, 18)  # Increased from 12x12

                        # Color the action icons for better visual feedback
            if action_icon == "x":
                # Red for invalid drop zones
                colored_pixmap = QPixmap(action_pixmap.size())
                colored_pixmap.fill(Qt.transparent)

                color_painter = QPainter(colored_pixmap)
                color_painter.setRenderHint(QPainter.Antialiasing)

                # First draw the original icon
                color_painter.drawPixmap(0, 0, action_pixmap)

                # Then apply red color overlay (brighter red with added green/blue)
                color_painter.setCompositionMode(QPainter.CompositionMode_SourceAtop)
                color_painter.fillRect(colored_pixmap.rect(), QColor(220, 68, 84))  # Brighter red (+15 green, +15 blue)

                color_painter.end()
                action_pixmap = colored_pixmap

            elif action_icon == "check":
                # Green for valid drop zones
                colored_pixmap = QPixmap(action_pixmap.size())
                colored_pixmap.fill(Qt.transparent)

                color_painter = QPainter(colored_pixmap)
                color_painter.setRenderHint(QPainter.Antialiasing)

                # First draw the original icon
                color_painter.drawPixmap(0, 0, action_pixmap)

                # Then apply green color overlay (bright green)
                color_painter.setCompositionMode(QPainter.CompositionMode_SourceAtop)
                color_painter.fillRect(colored_pixmap.rect(), QColor(40, 167, 69))  # Bootstrap success green

                color_painter.end()
                action_pixmap = colored_pixmap

            painter.drawPixmap(26, 26, action_pixmap)

        painter.end()

        # Create cursor with hotspot at (12, 12) - adjusted for larger size
        return QCursor(pixmap, 12, 12)

    def _restore_cursor(self) -> None:
        """Restore the original cursor with aggressive cleanup."""
        # Remove all override cursors aggressively
        cursor_count = 0
        while QApplication.overrideCursor() and cursor_count < 10:  # Increased limit
            QApplication.restoreOverrideCursor()
            cursor_count += 1

        if cursor_count > 0:
            logger.debug(f"[DragVisualManager] Restored {cursor_count} override cursors")

        # Force set to default cursor if still stuck
        if QApplication.overrideCursor():
            QApplication.setOverrideCursor(QCursor(Qt.ArrowCursor))
            QApplication.restoreOverrideCursor()
            logger.debug("[DragVisualManager] Force-restored stuck cursor")

    # =====================================
    # State Detection
    # =====================================

    def _detect_modifier_state(self) -> ModifierState:
        """Detect current keyboard modifier state."""
        modifiers = QApplication.keyboardModifiers()

        is_ctrl = bool(modifiers & Qt.ControlModifier)
        is_shift = bool(modifiers & Qt.ShiftModifier)

        # Check for Shift+Ctrl combination first (highest priority)
        if is_ctrl and is_shift:
            result = ModifierState.CTRL_SHIFT  # Ctrl+Shift = Merge + Recursive
        elif is_shift:
            result = ModifierState.SHIFT       # Shift only = Merge + Shallow
        elif is_ctrl:
            result = ModifierState.CTRL        # Ctrl only = Replace + Recursive
        else:
            result = ModifierState.NORMAL      # No modifiers = Replace + Shallow

        logger.debug(f"[DragVisualManager] Modifiers: Ctrl={is_ctrl}, Shift={is_shift} → {result.value}", extra={"dev_only": True})
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

        Args:
            widget: Widget to check
            drag_source: Source of the drag operation

        Returns:
            True if valid drop target
        """
        if widget is None:
            return False

        widget_class = widget.__class__.__name__
        logger.debug(f"[DragVisualManager] Checking drop target: widget_class={widget_class}, drag_source={drag_source}", extra={"dev_only": True})

        # FileTreeView can only drop on FileTableView
        if drag_source == "file_tree":
            return widget_class == "FileTableView"

        # FileTableView can only drop on MetadataTreeView
        elif drag_source == "file_table":
            result = widget_class == "MetadataTreeView"
            if not result:
                logger.debug(f"[DragVisualManager] Not a MetadataTreeView: {widget_class}", extra={"dev_only": True})
            return result

        return False

    # =====================================
    # Icon Utilities
    # =====================================

    def get_status_icon(self, state: DropZoneState) -> QIcon:
        """Get icon for drop zone state."""
        icon_map = {
            DropZoneState.VALID: "check-circle",
            DropZoneState.INVALID: "x-circle",
            DropZoneState.NEUTRAL: "target"
        }

        icon_name = icon_map.get(state, "target")
        return get_menu_icon(icon_name)

    def get_modifier_icon(self, state: ModifierState) -> QIcon:
        """Get icon for modifier state."""
        icon_map = {
            ModifierState.NORMAL: "check",
            ModifierState.SHIFT: "plus",
            ModifierState.CTRL: "arrow-down",
            ModifierState.CTRL_SHIFT: "plus-circle"
        }

        icon_name = icon_map.get(state, "check")
        return get_menu_icon(icon_name)


# Global convenience functions
def start_drag_visual(drag_type: DragType, source_info: str) -> None:
    """Start visual feedback for drag operation."""
    DragVisualManager.get_instance().start_drag_visual(drag_type, source_info)

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
