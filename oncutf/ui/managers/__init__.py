"""UI managers package.

Author: Michael Economou
Date: 2025-01-19
Updated: 2026-01-03

This package provides UI-related managers for the oncutf application,
including column configuration, status bar, table view, shortcuts,
splitters, and window configuration.

Note: UIManager was removed in favor of direct controller usage.
See oncutf/controllers/ui/ for the new architecture.
"""

from __future__ import annotations

from .column_manager import ColumnManager
from .column_service import (
    ColumnAlignment,
    ColumnConfig,
    UnifiedColumnService,
    get_column_service,
)
from .shortcut_manager import ShortcutManager
from .splitter_manager import SplitterManager
from .status_manager import StatusManager
from .table_manager import TableManager
from .window_config_manager import WindowConfigManager

__all__ = [
    "ColumnAlignment",
    "ColumnConfig",
    "ColumnManager",
    "ShortcutManager",
    "SplitterManager",
    "StatusManager",
    "TableManager",
    "UnifiedColumnService",
    "WindowConfigManager",
    "get_column_service",
]
