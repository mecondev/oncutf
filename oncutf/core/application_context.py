"""Module: application_context.py.

Author: Michael Economou
Date: 2025-05-31

DEPRECATED: Backward compatibility wrapper for ApplicationContext.

This module provides backward compatibility for code using the old
ApplicationContext location. New code should use:
- app/state/context.py (AppContext) for Qt-free code
- ui/adapters/qt_app_context.py (QtAppContext) for Qt-aware code

This wrapper will be removed in v2.0.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt5.QtCore import QObject, pyqtSignal
from typing_extensions import deprecated

from oncutf.ui.adapters.qt_app_context import QtAppContext
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.core.file.store import FileStore
    from oncutf.core.selection.selection_store import SelectionStore
    from oncutf.models.file_item import FileItem

logger = get_cached_logger(__name__)


@deprecated(
    "Use QtAppContext from ui.adapters or AppContext from app.state. Will be removed in v2.0."
)
class ApplicationContext(QObject):
    """DEPRECATED: Backward compatibility wrapper for QtAppContext.

    This class delegates all operations to QtAppContext.
    Use QtAppContext directly for new code.

    Migration path:
    - UI code: Use QtAppContext from oncutf.ui.adapters
    - Non-UI code: Use AppContext from oncutf.app.state
    """

    # Signals - delegate to QtAppContext
    files_changed = pyqtSignal(list)
    selection_changed = pyqtSignal(list)
    metadata_changed = pyqtSignal(str, dict)

    _instance: ApplicationContext | None = None

    def __init__(self, parent: QObject | None = None):
        """Initialize wrapper around QtAppContext."""
        super().__init__(parent)

        if ApplicationContext._instance is not None:
            raise RuntimeError("ApplicationContext is a singleton. Use get_instance()")
        ApplicationContext._instance = self

        # Get or create QtAppContext
        try:
            self._qt_context = QtAppContext.get_instance()
        except RuntimeError:
            self._qt_context = QtAppContext.create_instance(parent)

        # Connect signals
        self._qt_context.files_changed.connect(self.files_changed.emit)
        self._qt_context.selection_changed.connect(self.selection_changed.emit)
        self._qt_context.metadata_changed.connect(self.metadata_changed.emit)

        logger.warning(
            "ApplicationContext is deprecated. Use QtAppContext or AppContext instead.",
            extra={"dev_only": True},
        )

        logger.warning(
            "ApplicationContext is deprecated. Use QtAppContext or AppContext instead.",
            extra={"dev_only": True},
        )

    def initialize_stores(self) -> None:
        """Initialize core stores - delegates to QtAppContext."""
        self._qt_context.initialize_stores()

    @classmethod
    def get_instance(cls) -> ApplicationContext:
        """Get the singleton instance."""
        if cls._instance is None:
            raise RuntimeError("ApplicationContext not initialized. Call create_instance() first.")
        return cls._instance

    @classmethod
    def create_instance(cls, parent: QObject | None = None) -> ApplicationContext:
        """Create the singleton instance."""
        if cls._instance is not None:
            logger.warning("ApplicationContext already exists. Returning existing instance.")
            return cls._instance
        return cls(parent)

    # =====================================
    # Delegate all methods to QtAppContext
    # =====================================

    @property
    def file_store(self) -> FileStore:
        """Get the FileStore instance."""
        return self._qt_context.file_store

    @property
    def selection_store(self) -> SelectionStore:
        """Get the SelectionStore instance."""
        return self._qt_context.selection_store

    def get_files(self) -> list[FileItem]:
        """Get current file list."""
        return self._qt_context.get_files()

    @deprecated("Use FileStore.set_loaded_files() instead. Will be removed in v2.0.")
    def set_files(self, files: list[FileItem]) -> None:
        """Set current file list."""
        self._qt_context.set_files(files)

    def get_current_folder(self) -> str | None:
        """Get current folder path."""
        return self._qt_context.get_current_folder()

    def set_current_folder(self, folder_path: str | None, recursive: bool = False) -> None:
        """Set current folder path and recursive mode."""
        self._qt_context.set_current_folder(folder_path, recursive)

    def is_recursive_mode(self) -> bool:
        """Check if current folder was loaded recursively."""
        return self._qt_context.is_recursive_mode()

    def set_recursive_mode(self, recursive: bool) -> None:
        """Set recursive mode flag."""
        self._qt_context.set_recursive_mode(recursive)

    def get_selected_rows(self) -> set[int]:
        """Get currently selected row indices."""
        return self._qt_context.get_selected_rows()

    def set_selected_rows(self, rows: set[int]) -> None:
        """Set selected row indices."""
        self._qt_context.set_selected_rows(rows)

    def get_checked_rows(self) -> set[int]:
        """Get currently checked row indices."""
        return self._qt_context.get_checked_rows()

    def set_checked_rows(self, rows: set[int]) -> None:
        """Set checked row indices."""
        self._qt_context.set_checked_rows(rows)

    def get_metadata(self, file_path: str) -> dict[str, Any] | None:
        """Get metadata for a file."""
        return self._qt_context.get_metadata(file_path)

    def set_metadata(self, file_path: str, metadata: dict[str, Any]) -> None:
        """Set metadata for a file."""
        self._qt_context.set_metadata(file_path, metadata)

    def register_manager(self, name: str, manager: Any) -> None:
        """Register a manager in the global registry."""
        self._qt_context.register_manager(name, manager)

    def get_manager(self, name: str) -> Any | None:
        """Get a manager from the registry."""
        return self._qt_context.get_manager(name)

    def has_manager(self, name: str) -> bool:
        """Check if a manager is registered."""
        return self._qt_context.has_manager(name)

    def track_performance(self, operation: str, duration_ms: float) -> None:
        """Track performance metrics for operations."""
        self._qt_context.track_performance(operation, duration_ms)

    def get_performance_report(self) -> dict[str, float]:
        """Get performance metrics report."""
        return self._qt_context.get_performance_report()

    def is_ready(self) -> bool:
        """Check if context is fully initialized."""
        return self._qt_context.is_ready()

    def mark_ready(self) -> None:
        """Mark context as fully initialized."""
        self._qt_context.mark_ready()

    def cleanup(self) -> None:
        """Clean up resources before shutdown."""
        self._qt_context.cleanup()


# Convenience function (deprecated)
@deprecated("Use get_qt_app_context() or get_app_context(). Will be removed in v2.0.")
def get_app_context() -> ApplicationContext:
    """Get the singleton ApplicationContext instance.

    DEPRECATED: Use get_qt_app_context() from ui.adapters
    or get_app_context() from app.state instead.
    """
    return ApplicationContext.get_instance()
