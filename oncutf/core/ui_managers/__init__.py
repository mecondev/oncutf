"""UI managers package.

Author: Michael Economou
Date: 2025-01-19

This package provides UI-related managers for the oncutf application,
including main UI management, column configuration, status bar, table view,
shortcuts, splitters, and window configuration.
"""

from __future__ import annotations

from .column_manager import ColumnManager
from .shortcut_manager import ShortcutManager
from .splitter_manager import SplitterManager
from .status_manager import StatusManager
from .table_manager import TableManager
from .ui_manager import UIManager
from .window_config_manager import WindowConfigManager

__all__ = [
    'ColumnManager',
    'ShortcutManager',
    'SplitterManager',
    'StatusManager',
    'TableManager',
    'UIManager',
    'WindowConfigManager',
]
