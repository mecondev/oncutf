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
            "invalid": ["FileTreeView", "MetadataTreeView"]
        },
        "file_table": {
            "valid": ["MetadataTreeView"],
            "invalid": ["FileTreeView", "FileTableView"]
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
    def validate_drop_zone(cls, drag_source: str, log_prefix: str = "") -> DropZoneState:
        """
        Validate the current drop zone based on widget under cursor.

        Args:
            drag_source: Source of the drag operation ("file_tree" or "file_table")
            log_prefix: Prefix for debug messages (e.g., "[FileTableView]")

        Returns:
            DropZoneState: Current drop zone state
        """
        if drag_source not in cls.ZONE_RULES:
            logger.warning(f"Unknown drag source: {drag_source}")
            return DropZoneState.NEUTRAL

        # Get widget under cursor
        cursor_pos = QCursor.pos()
        widget_under_cursor = QApplication.widgetAt(cursor_pos)

        if not widget_under_cursor:
            update_drop_zone_state(DropZoneState.NEUTRAL)
            return DropZoneState.NEUTRAL

        # Get rules for this drag source
        rules = cls.ZONE_RULES[drag_source]
        valid_zones = rules["valid"]
        invalid_zones = rules["invalid"]

        # Walk up parent hierarchy to find drop targets
        current_widget = widget_under_cursor

        while current_widget:
            widget_class = current_widget.__class__.__name__

            # Check for valid targets
            if widget_class in valid_zones:
                update_drop_zone_state(DropZoneState.VALID)
                if log_prefix:
                    logger.debug(f"{log_prefix} VALID drop zone detected: {widget_class}")
                return DropZoneState.VALID

            # Check for invalid targets, but ignore initial drag widget
            elif widget_class in invalid_zones:
                # If this is the initial drag widget, treat as neutral instead of invalid
                initial_widget = cls._initial_drag_widgets.get(drag_source)
                if initial_widget == widget_class:
                    update_drop_zone_state(DropZoneState.NEUTRAL)
                    return DropZoneState.NEUTRAL
                else:
                    update_drop_zone_state(DropZoneState.INVALID)
                    if log_prefix:
                        logger.debug(f"{log_prefix} INVALID drop zone detected: {widget_class}")
                    return DropZoneState.INVALID

            current_widget = current_widget.parent()

        # No specific target found - neutral state
        update_drop_zone_state(DropZoneState.NEUTRAL)
        return DropZoneState.NEUTRAL

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
