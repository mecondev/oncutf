"""MainWindow delegate classes.

Author: Michael Economou
Date: 2026-01-10

This package contains delegate classes that group MainWindow's methods
by concern, reducing the main_window.py file from 695 to ~150 lines.

Each delegate class contains only forwarding methods to handlers/managers.
No business logic exists in these classes.
"""

from oncutf.ui.main_window_delegates.event_delegates import EventDelegates
from oncutf.ui.main_window_delegates.file_operation_delegates import FileOperationDelegates
from oncutf.ui.main_window_delegates.metadata_delegates import MetadataDelegates
from oncutf.ui.main_window_delegates.preview_delegates import PreviewDelegates
from oncutf.ui.main_window_delegates.selection_delegates import SelectionDelegates
from oncutf.ui.main_window_delegates.table_delegates import TableDelegates
from oncutf.ui.main_window_delegates.utility_delegates import UtilityDelegates
from oncutf.ui.main_window_delegates.validation_delegates import ValidationDelegates
from oncutf.ui.main_window_delegates.window_delegates import WindowDelegates

__all__ = [
    "EventDelegates",
    "FileOperationDelegates",
    "MetadataDelegates",
    "PreviewDelegates",
    "SelectionDelegates",
    "TableDelegates",
    "UtilityDelegates",
    "ValidationDelegates",
    "WindowDelegates",
]
