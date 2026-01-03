"""Module: file_tree_view.py - Backward compatibility re-export.

DEPRECATED: The FileTreeView class has been moved to the file_tree package.
Use `oncutf.ui.widgets.file_tree` instead.
Scheduled for removal in v2.0.

Author: Michael Economou
Date: 2025-05-31 (Delegator created: 2026-01-02)
"""
import warnings

warnings.warn(
    "oncutf.ui.widgets.file_tree_view is deprecated. "
    "Use oncutf.ui.widgets.file_tree instead. "
    "This module will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2,
)

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
