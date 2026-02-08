"""Open file locations using platform-native tools.

Author: Michael Economou
Date: 2026-02-08
"""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path


def open_file_location(file_path: str) -> bool:
    """Open file location in system file manager.

    Args:
        file_path: Path to file or folder to open

    Returns:
        True if operation succeeded, False otherwise

    """
    try:
        system = platform.system()
        path = Path(file_path).resolve()

        if system == "Windows":
            # Windows: use explorer with /select flag to highlight file
            if path.is_file():
                subprocess.Popen(["explorer", "/select,", str(path)])
            else:
                subprocess.Popen(["explorer", str(path)])
        elif system == "Darwin":
            # macOS: use 'open' command
            if path.is_file():
                subprocess.Popen(["open", "-R", str(path)])
            else:
                subprocess.Popen(["open", str(path)])
        else:
            # Linux: use xdg-open (works on most DEs)
            if path.is_file():
                subprocess.Popen(["xdg-open", str(path.parent)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        return False
    else:
        return True
