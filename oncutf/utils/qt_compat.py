"""Qt compatibility utilities for core modules.

Author: Michael Economou
Date: 2026-02-03

Provides Qt-free fallbacks for operations that core modules may need.
This allows core modules to remain testable and Qt-independent while
still supporting UI responsiveness when Qt is available.
"""

import platform
import subprocess
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


def open_file_location(file_path: str) -> bool:
    """Open file location in system file manager.

    This is a Qt-free alternative to QDesktopServices.openUrl().
    Uses platform-specific commands to open the file manager.

    Args:
        file_path: Path to file or folder to open

    Returns:
        True if operation succeeded, False otherwise

    """
    try:
        from pathlib import Path

        system = platform.system()
        path = Path(file_path).resolve()

        if system == "Windows":
            # Windows: use explorer with /select flag to highlight file
            if path.is_file():
                subprocess.Popen(["explorer", "/select,", str(path)])
            else:
                subprocess.Popen(["explorer", str(path)])
        elif system == "Darwin":  # macOS
            # macOS: use 'open' command
            if path.is_file():
                # Reveal file in Finder
                subprocess.Popen(["open", "-R", str(path)])
            else:
                subprocess.Popen(["open", str(path)])
        else:  # Linux and others
            # Linux: use xdg-open (works on most DEs)
            if path.is_file():
                # Open parent directory
                subprocess.Popen(["xdg-open", str(path.parent)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        return False
    else:
        return True


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
        # Qt.ItemDataRole enum values (standard Qt constants)
        # Using literals to avoid mypy attr-defined errors in Qt namespace
        return {
            "DecorationRole": 1,
            "ToolTipRole": 3,
            "DisplayRole": 0,
            "EditRole": 2,
        }
