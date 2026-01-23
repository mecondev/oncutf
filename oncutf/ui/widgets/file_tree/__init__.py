"""Package: file_tree.

Author: Michael Economou
Date: 2026-01-02

File tree view widget package for folder navigation.

This package provides the FileTreeView widget split into focused modules:
- view.py: Main view widget (thin shell, Qt integration)
- filesystem_handler.py: Filesystem monitoring setup and callbacks
- state_handler.py: State persistence (expand/collapse/selection)
- drag_handler.py: Custom drag & drop implementation
- event_handler.py: Key, scroll, and wheel event handling
- utils.py: Helper classes (DragCancelFilter)
"""

from oncutf.ui.widgets.file_tree.utils import DragCancelFilter, get_drag_cancel_filter
from oncutf.ui.widgets.file_tree.view import FileTreeView

__all__ = [
    "DragCancelFilter",
    "FileTreeView",
    "get_drag_cancel_filter",
]
