"""Module: drag_zone_validator.py.

Author: Michael Economou
Date: 2025-06-10

Drag Zone Validator - Common logic for drag & drop zone validation
This module provides shared logic for validating drop zones during drag operations,
eliminating code duplication between FileTreeView and FileTableView.
"""

from typing import ClassVar

from oncutf.core.drag.drag_visual_manager import DropZoneState, update_drop_zone_state
from oncutf.core.pyqt_imports import QApplication, QCursor
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class DragZoneValidator:
    """Centralized logic for validating drag & drop zones.

    Provides consistent validation rules across different source widgets.
    Features "left and returned" logic for improved UX.
    """

    # Define valid/invalid drop zones for each source type
    ZONE_RULES: ClassVar[dict[str, dict[str, list[str]]]] = {
        "file_tree": {"valid": ["FileTableView"], "invalid": ["FileTreeView", "MetadataTreeView"]},
        "file_table": {"valid": ["MetadataTreeView"], "invalid": ["FileTreeView", "FileTableView"]},
    }

    # Track initial drag positions and "left and returned" state
    _initial_drag_widgets: ClassVar[dict[str, str]] = {}
    _has_left_initial: ClassVar[dict[str, bool]] = {}  # Track if drag has left initial widget

    @classmethod
    def set_initial_drag_widget(cls, drag_source: str, widget_class_name: str) -> None:
        """Set the initial widget where drag started and reset left state."""
        cls._initial_drag_widgets[drag_source] = widget_class_name
        cls._has_left_initial[drag_source] = False  # Reset the "has left" flag
        logger.debug(
            "[DragZoneValidator] Initial drag widget set: %s (source: %s)",
            widget_class_name,
            drag_source,
            extra={"dev_only": True},
        )

    @classmethod
    def clear_initial_drag_widget(cls, drag_source: str) -> None:
        """Clear the initial drag widget when drag ends."""
        cls._initial_drag_widgets.pop(drag_source, None)
        cls._has_left_initial.pop(drag_source, None)

    @classmethod
    def validate_drop_zone(cls, drag_source: str, log_prefix: str) -> None:
        """Validate current drop zone and update visual feedback with "left and returned" logic.

        Args:
            drag_source: Source of the drag operation ("file_tree" or "file_table")
            log_prefix: Prefix for log messages (e.g., "[FileTreeView]")

        """
        # Get widget under cursor
        widget_under_cursor = QApplication.widgetAt(QCursor.pos())
        if not widget_under_cursor:
            return

        widget_class_name = widget_under_cursor.__class__.__name__
        logger.debug(
            "%s Widget under cursor: %s",
            log_prefix,
            widget_class_name,
            extra={"dev_only": True},
        )
        logger.debug(
            "%s Initial widget: %s, Has left: %s",
            log_prefix,
            cls._initial_drag_widgets.get(drag_source),
            cls._has_left_initial.get(drag_source),
            extra={"dev_only": True},
        )

        # Check if this is the initial drag widget
        initial_widget = cls._initial_drag_widgets.get(drag_source)
        is_initial_widget = initial_widget == widget_class_name

        # Update "has left initial" state
        if not is_initial_widget and not cls._has_left_initial.get(drag_source, False):
            cls._has_left_initial[drag_source] = True
            logger.debug(
                "%s Left initial widget (%s) - enabling invalid state on return",
                log_prefix,
                initial_widget,
                extra={"dev_only": True},
            )

        # Special handling for initial drag widget with "left and returned" logic
        if is_initial_widget:
            has_left = cls._has_left_initial.get(drag_source, False)

            if not has_left:
                # Still in initial widget and haven't left yet - show as VALID (with action icons)
                cls._set_cursor_state(DropZoneState.VALID)
                logger.debug(
                    "%s VALID zone (initial drag widget, haven't left): %s",
                    log_prefix,
                    widget_class_name,
                    extra={"dev_only": True},
                )
                return
            else:
                # Returned to initial widget after leaving - now show as INVALID
                cls._set_cursor_state(DropZoneState.INVALID)
                logger.debug(
                    "%s INVALID zone (returned to initial after leaving): %s",
                    log_prefix,
                    widget_class_name,
                    extra={"dev_only": True},
                )
                return

        # Normal validation logic for non-initial widgets
        rules = cls.ZONE_RULES.get(drag_source, {})
        valid_zones = rules.get("valid", [])
        invalid_zones = rules.get("invalid", [])

        if widget_class_name in valid_zones:
            cls._set_cursor_state(DropZoneState.VALID)
            logger.debug(
                "%s VALID drop zone detected: %s",
                log_prefix,
                widget_class_name,
                extra={"dev_only": True},
            )
        elif widget_class_name in invalid_zones:
            cls._set_cursor_state(DropZoneState.INVALID)
            logger.debug(
                "%s INVALID drop zone detected: %s",
                log_prefix,
                widget_class_name,
                extra={"dev_only": True},
            )
        else:
            # Unknown widget - treat as neutral
            cls._set_cursor_state(DropZoneState.NEUTRAL)
            logger.debug(
                "%s NEUTRAL zone (unknown widget): %s",
                log_prefix,
                widget_class_name,
                extra={"dev_only": True},
            )

    @classmethod
    def get_valid_zones(cls, drag_source: str) -> list[str]:
        """Get list of valid drop zone widget names for a drag source."""
        return cls.ZONE_RULES.get(drag_source, {}).get("valid", [])

    @classmethod
    def get_invalid_zones(cls, drag_source: str) -> list[str]:
        """Get list of invalid drop zone widget names for a drag source."""
        return cls.ZONE_RULES.get(drag_source, {}).get("invalid", [])

    @classmethod
    def is_valid_zone(cls, drag_source: str, widget_class_name: str) -> bool | None:
        """Check if a widget class is valid/invalid for a drag source.

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
    def _set_cursor_state(cls, state: DropZoneState) -> None:
        """Set the cursor state using the visual manager."""
        update_drop_zone_state(state)
