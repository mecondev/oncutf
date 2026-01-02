"""Module: file_tree_view.py

Author: Michael Economou
Date: 2025-05-31 (Delegator created: 2026-01-02)

Delegator module for backward compatibility.

This module re-exports FileTreeView and DragCancelFilter from their new
locations in the file_tree package. The implementation has been split into:
- oncutf.ui.widgets.file_tree.view - Main FileTreeView class
- oncutf.ui.widgets.file_tree.utils - DragCancelFilter and utilities
- oncutf.ui.widgets.file_tree.filesystem_handler - Filesystem monitoring
- oncutf.ui.widgets.file_tree.state_handler - State persistence
- oncutf.ui.widgets.file_tree.drag_handler - Drag & drop handling
- oncutf.ui.widgets.file_tree.event_handler - Event handling

For new code, import directly from oncutf.ui.widgets.file_tree instead.
"""

# Re-export for backward compatibility
from oncutf.ui.widgets.file_tree import (
    DragCancelFilter,
    FileTreeView,
    get_drag_cancel_filter,
)

# For backward compatibility with direct access to global instance
_drag_cancel_filter = get_drag_cancel_filter()

__all__ = [
    "FileTreeView",
    "DragCancelFilter",
    "_drag_cancel_filter",
]
