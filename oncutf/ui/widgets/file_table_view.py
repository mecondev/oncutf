"""Module: file_table_view.py - Backward compatibility re-export.

DEPRECATED: The FileTableView class has been moved to the file_table package.
Use `oncutf.ui.widgets.file_table` instead.
Scheduled for removal in v2.0.

Author: Michael Economou
Date: 2026-01-04
"""
import warnings

warnings.warn(
    "oncutf.ui.widgets.file_table_view is deprecated. "
    "Use oncutf.ui.widgets.file_table instead. "
    "This module will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2,
)

from oncutf.ui.widgets.file_table import FileTableView

__all__ = ["FileTableView"]
