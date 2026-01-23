"""Drag state service - manage drag & drop state without direct UI dependencies.

Author: Michael Economou
Date: 2026-01-22

Provides facade for drag & drop state management, allowing core modules
to clear drag state without direct coupling to UI validation classes.

Part of Phase A edge cases cleanup (250121_summary.md).

Usage:
    from oncutf.app.services.drag_state import clear_drag_state

    # Clear drag state when loading files
    clear_drag_state("file_tree")
    clear_drag_state("file_table")
"""


def clear_drag_state(drag_source: str) -> None:
    """Clear drag state for a specific drag source.

    Facade for DragZoneValidator.clear_initial_drag_widget().

    Args:
        drag_source: Source of the drag operation ("file_tree" or "file_table")

    """
    from oncutf.utils.ui.drag_zone_validator import DragZoneValidator

    DragZoneValidator.clear_initial_drag_widget(drag_source)
