"""Module: file_table_view.py - Backward compatibility re-export.

Author: Michael Economou
Date: 2026-01-04

This module provides backward compatibility for existing imports.
The FileTableView class has been moved to the file_table package.

New imports should use:
    from oncutf.ui.widgets.file_table import FileTableView
"""

from oncutf.ui.widgets.file_table import FileTableView

__all__ = ["FileTableView"]
