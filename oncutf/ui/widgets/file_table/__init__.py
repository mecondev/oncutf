"""Package: file_table - FileTableView widget with extracted handlers.

Author: Michael Economou
Date: 2026-01-04

This package contains the FileTableView widget split into modular components:
- view.py: Main FileTableView class (thin shell)
- event_handler.py: Qt event handlers (mouse, keyboard, focus)
- hover_handler.py: Hover state management
- tooltip_handler.py: Custom tooltip logic
- viewport_handler.py: Scrollbar and viewport management
- utils.py: Cursor cleanup and helper functions

Architecture:
    The FileTableView uses composition with:
    - SelectionBehavior: Selection logic
    - DragDropBehavior: Drag & drop support
    - ColumnManagementBehavior: Column width/visibility
    - EventHandler: Qt event handling (NEW)
    - HoverHandler: Hover highlighting (NEW)
    - TooltipHandler: Custom tooltips (NEW)
    - ViewportHandler: Scrollbar/viewport (NEW)
"""

from oncutf.ui.widgets.file_table.view import FileTableView

__all__ = ["FileTableView"]
