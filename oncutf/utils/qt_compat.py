"""Qt compatibility utilities for core modules.

Author: Michael Economou
Date: 2026-02-03

Provides Qt-free fallbacks for operations that core modules may need.
This allows core modules to remain testable and Qt-independent while
still supporting UI responsiveness when Qt is available.
"""

from typing import Any


def process_events() -> None:
    """Process pending Qt events if Qt is available, otherwise no-op.

    This is a compatibility shim that allows core modules to request
    UI updates without directly depending on PyQt5. When Qt is not
    available (e.g., in tests or CLI mode), this safely does nothing.

    Usage in core modules:
        from oncutf.utils.qt_compat import process_events

        for item in large_dataset:
            # ... process item ...
            process_events()  # Keep UI responsive
    """
    try:
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            app.processEvents()
    except (ImportError, RuntimeError):
        # Qt not available or no QApplication instance - safe to ignore
        pass


def get_item_data_roles() -> dict[str, Any]:
    """Get Qt ItemDataRole constants if Qt is available, otherwise placeholders.

    Returns:
        Dictionary with role constants (DecorationRole, ToolTipRole, etc.)
        If Qt is not available, returns integer placeholders.

    """
    try:
        from PyQt5.QtCore import Qt
    except ImportError:
        # Fallback to standard Qt role values (for non-Qt contexts)
        return {
            "DecorationRole": 1,
            "ToolTipRole": 3,
            "DisplayRole": 0,
            "EditRole": 2,
        }
    else:
        return {
            "DecorationRole": Qt.DecorationRole,
            "ToolTipRole": Qt.ToolTipRole,
            "DisplayRole": Qt.DisplayRole,
            "EditRole": Qt.EditRole,
        }
