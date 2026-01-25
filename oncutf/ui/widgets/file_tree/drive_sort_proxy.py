"""Drive sort proxy model for file tree.

Author: Michael Economou
Date: 2026-01-25

Ensures stable drive ordering on Windows while keeping default sorting
for normal files and folders.
"""

from __future__ import annotations

import os
import platform
from typing import Any

from PyQt5.QtCore import QSortFilterProxyModel, Qt

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class DriveSortProxyModel(QSortFilterProxyModel):
    """Proxy model that enforces drive ordering on Windows root."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setDynamicSortFilter(True)
        self.setSortCaseSensitivity(Qt.CaseInsensitive)

    def filePath(self, index) -> str:
        """Return file path for proxy index."""
        source = self.sourceModel()
        if not source or not index.isValid():
            return ""
        return source.filePath(self.mapToSource(index))

    def index_from_path(self, path: str) -> Any:
        """Return proxy index for a file system path."""
        source = self.sourceModel()
        if not source:
            return super().index(0, 0)
        return self.mapFromSource(source.index(path))

    def rootPath(self) -> str:
        """Return root path from source model when available."""
        source = self.sourceModel()
        if source and hasattr(source, "rootPath"):
            try:
                return source.rootPath()
            except Exception:
                return ""
        return ""

    def setRootPath(self, path: str) -> None:
        """Set root path on source model if supported."""
        source = self.sourceModel()
        if source and hasattr(source, "setRootPath"):
            source.setRootPath(path)

    def lessThan(self, left, right) -> bool:
        """Custom ordering for Windows drives at root level."""
        try:
            source = self.sourceModel()
            if not source:
                return super().lessThan(left, right)

            if platform.system() == "Windows":
                left_parent = left.parent()
                right_parent = right.parent()

                if not left_parent.isValid() and not right_parent.isValid():
                    left_path = source.filePath(left)
                    right_path = source.filePath(right)
                    left_key = self._drive_sort_key(left_path)
                    right_key = self._drive_sort_key(right_path)
                    if left_key != right_key:
                        return left_key < right_key

            left_is_dir = source.isDir(left)
            right_is_dir = source.isDir(right)
            if left_is_dir != right_is_dir:
                return left_is_dir

            return super().lessThan(left, right)
        except Exception as e:
            logger.debug(
                "[DriveSortProxyModel] lessThan fallback: %s",
                e,
                extra={"dev_only": True},
            )
            return super().lessThan(left, right)

    def _drive_sort_key(self, path: str) -> tuple[int, int, str]:
        if not path:
            return (2, 0, "")

        letter = ""
        if len(path) >= 2 and path[1] == ":":
            letter = path[0].upper()

        if letter:
            system_drive = os.environ.get("SYSTEMDRIVE", "C:").upper()
            system_letter = system_drive[0] if system_drive else "C"
            priority = 0 if letter == system_letter else 1
            return (0, priority, letter)

        return (1, 0, path.lower())
