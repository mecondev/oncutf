"""
Drag Zone Validator - Common logic for drag & drop zone validation

Author: Michael Economou
Date: 2025-06-22

This module provides shared logic for validating drop zones during drag operations,
eliminating code duplication between FileTreeView and FileTableView.
"""

from typing import Dict, List, Optional, Set
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication

from core.drag_visual_manager import DropZoneState, update_drop_zone_state
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class DragZoneValidator:
    """
    Centralized logic for validating drag & drop zones.

    Provides consistent validation rules across different source widgets.
    """

    # Define valid/invalid drop zones for each source type
    ZONE_RULES: Dict[str, Dict[str, List[str]]] = {
        "file_tree": {
            "valid": ["FileTableView"],
            "invalid": [
                "FileTreeView", "MetadataTreeView", "MetadataWidget",
                "RenameModuleWidget", "RenameModulesArea", "NameTransformWidget",
                "OriginalNameWidget", "PreviewTableWidget", "PreviewTablesView",
                "CompactWaitingWidget", "InteractiveHeader", "QLabel",
                "QSplitter", "QFrame", "QPushButton", "QScrollBar", "QScrollArea"
            ]
        },
        "file_table": {
            "valid": ["MetadataTreeView"],
            "invalid": [
                "FileTreeView", "FileTableView", "MetadataWidget",
                "RenameModuleWidget", "RenameModulesArea", "NameTransformWidget",
                "OriginalNameWidget", "PreviewTableWidget", "PreviewTablesView",
                "CompactWaitingWidget", "InteractiveHeader", "QLabel",
                "QSplitter", "QFrame", "QPushButton", "QScrollBar", "QScrollArea"
            ]
        }
    }

    # Track initial drag positions to avoid immediate invalid state
    _initial_drag_widgets: Dict[str, str] = {}

    @classmethod
    def set_initial_drag_widget(cls, drag_source: str, widget_class_name: str) -> None:
        """Set the initial widget where drag started to avoid immediate invalid state."""
        cls._initial_drag_widgets[drag_source] = widget_class_name

    @classmethod
    def clear_initial_drag_widget(cls, drag_source: str) -> None:
        """Clear the initial drag widget when drag ends."""
        cls._initial_drag_widgets.pop(drag_source, None)

    @classmethod
    def validate_drop_zone(cls, drag_source: str, log_prefix: str) -> None:
        """
        Validate current drop zone and update visual feedback.

        Args:
            drag_source: Source of the drag operation ("file_tree" or "file_table")
            log_prefix: Prefix for log messages (e.g., "[FileTreeView]")
        """
        logger.debug(f"{log_prefix} validate_drop_zone called", extra={"dev_only": True})

        # Get widget under cursor
        widget_under_cursor = QApplication.widgetAt(QCursor.pos())
        if not widget_under_cursor:
            return

        widget_class_name = widget_under_cursor.__class__.__name__

        # Check if this is the initial drag widget (neutral zone)
        if cls._is_initial_drag_widget(drag_source, widget_class_name):
            cls._set_cursor_state(DropZoneState.NEUTRAL)
            return

        # Special case: Allow drops on widgets in placeholder mode
        # Even if they are normally invalid zones (like QLabel placeholders)
        if hasattr(widget_under_cursor, 'property') and widget_under_cursor.property("placeholder"):
            # This is a placeholder widget - check if it's a valid target
            parent_widget = widget_under_cursor.parent()
            while parent_widget:
                parent_class_name = parent_widget.__class__.__name__
                if parent_class_name in cls.ZONE_RULES[drag_source]["valid"]:
                    cls._set_cursor_state(DropZoneState.VALID)
                    logger.debug(f"{log_prefix} VALID drop zone detected: {parent_class_name} (placeholder mode)", extra={"dev_only": True})
                    return
                parent_widget = parent_widget.parent()

        # Normal validation logic
        rules = cls.ZONE_RULES.get(drag_source, {})
        valid_zones = rules.get("valid", [])
        invalid_zones = rules.get("invalid", [])

        if widget_class_name in valid_zones:
            cls._set_cursor_state(DropZoneState.VALID)
            logger.debug(f"{log_prefix} VALID drop zone detected: {widget_class_name}", extra={"dev_only": True})
        elif widget_class_name in invalid_zones:
            cls._set_cursor_state(DropZoneState.INVALID)
            logger.debug(f"{log_prefix} INVALID drop zone detected: {widget_class_name}", extra={"dev_only": True})
        else:
            # Unknown widget - treat as neutral
            cls._set_cursor_state(DropZoneState.NEUTRAL)

    @classmethod
    def get_valid_zones(cls, drag_source: str) -> List[str]:
        """Get list of valid drop zone widget names for a drag source."""
        return cls.ZONE_RULES.get(drag_source, {}).get("valid", [])

    @classmethod
    def get_invalid_zones(cls, drag_source: str) -> List[str]:
        """Get list of invalid drop zone widget names for a drag source."""
        return cls.ZONE_RULES.get(drag_source, {}).get("invalid", [])

    @classmethod
    def is_valid_zone(cls, drag_source: str, widget_class_name: str) -> Optional[bool]:
        """
        Check if a widget class is valid/invalid for a drag source.

        Returns:
            True if valid, False if invalid, None if neutral
        """
        if drag_source not in cls.ZONE_RULES:
            return None

        rules = cls.ZONE_RULES[drag_source]

        if widget_class_name in rules["valid"]:
            return True
        elif widget_class_name in rules["invalid"]:
            return False
        else:
            return None

    @classmethod
    def _is_initial_drag_widget(cls, drag_source: str, widget_class_name: str) -> bool:
        """Check if the widget is the initial drag widget (should be neutral)."""
        initial_widget = cls._initial_drag_widgets.get(drag_source)
        return initial_widget == widget_class_name

    @classmethod
    def _set_cursor_state(cls, state: DropZoneState) -> None:
        """Set the cursor state using the visual manager."""
        from core.drag_visual_manager import update_drop_zone_state
        update_drop_zone_state(state)
