"""Module: qt_app_context.py - Qt wrapper for AppContext.

Author: Michael Economou
Date: 2026-01-25

QtAppContext - Qt-aware wrapper around AppContext with signals/slots.

This adapter wraps the pure Python AppContext and adds Qt signal emissions
for state changes, enabling reactive UI updates.

For Qt-free version, see app/state/context.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt5.QtCore import QObject, pyqtSignal

from oncutf.app.state.context import AppContext
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

logger = get_cached_logger(__name__)


class QtAppContext(QObject):
    """Qt-aware wrapper for AppContext with signal emissions.

    This class wraps the pure Python AppContext and emits Qt signals
    when state changes occur, enabling reactive UI updates.

    Signals:
        files_changed: Emitted when file list changes
        selection_changed: Emitted when selection changes
        metadata_changed: Emitted when metadata updates

    Usage:
        qt_ctx = QtAppContext.get_instance()
        qt_ctx.files_changed.connect(on_files_changed)
        qt_ctx.set_files(files)  # Emits signal
    """

    # Signals for state changes
    files_changed = pyqtSignal(list)  # Emitted when file list changes
    selection_changed = pyqtSignal(list)  # Emitted when selection changes
    metadata_changed = pyqtSignal(str, dict)  # Emitted when metadata updates (path, metadata)

    _instance: QtAppContext | None = None

    def __init__(self, parent: QObject | None = None):
        """Initialize Qt wrapper around AppContext.

        Args:
            parent: Optional parent QObject

        """
        super().__init__(parent)

        # Ensure singleton
        if QtAppContext._instance is not None:
            raise RuntimeError("QtAppContext is a singleton. Use get_instance()")
        QtAppContext._instance = self

        # Get or create underlying AppContext
        try:
            self._app_context = AppContext.get_instance()
        except RuntimeError:
            self._app_context = AppContext.create_instance()

        # Connect to stores if they exist
        self._connect_stores()

        logger.info("QtAppContext initialized (Qt wrapper)", extra={"dev_only": True})

    def _connect_stores(self) -> None:
        """Connect to store signals if stores are initialized."""
        # Connect FileStore signals if available
        if self._app_context._file_store is not None:
            self._app_context._file_store.files_loaded.connect(self._on_files_loaded)
            self._app_context._file_store.folder_changed.connect(self._on_folder_changed)

        # Connect SelectionStore signals if available
        if self._app_context._selection_store is not None:
            self._app_context._selection_store.selection_changed.connect(
                self._on_selection_changed
            )
            self._app_context._selection_store.checked_changed.connect(self._on_checked_changed)

    def initialize_stores(self) -> None:
        """Initialize core stores and connect signals."""
        self._app_context.initialize_stores()
        self._connect_stores()

    def _on_files_loaded(self, files: list[Any]) -> None:
        """Handle files loaded from FileStore."""
        self.files_changed.emit(files)
        logger.debug(
            "QtAppContext: Files loaded signal relayed: %d files",
            len(files),
            extra={"dev_only": True},
        )

    def _on_folder_changed(self, folder_path: str) -> None:
        """Handle folder change from FileStore."""
        logger.debug(
            "QtAppContext: Folder changed to %s",
            folder_path,
            extra={"dev_only": True},
        )

    def _on_selection_changed(self, selected_rows: list[int]) -> None:
        """Handle selection changed from SelectionStore."""
        self.selection_changed.emit(selected_rows)
        logger.debug(
            "QtAppContext: Selection changed signal relayed: %d rows",
            len(selected_rows),
            extra={"dev_only": True},
        )

    def _on_checked_changed(self, checked_rows: list[int]) -> None:
        """Handle checked state changed from SelectionStore."""
        logger.debug("QtAppContext: Checked state changed: %d rows", len(checked_rows))

    @classmethod
    def get_instance(cls) -> QtAppContext:
        """Get the singleton instance.

        Returns:
            QtAppContext: The singleton instance

        Raises:
            RuntimeError: If instance has not been created yet

        """
        if cls._instance is None:
            raise RuntimeError("QtAppContext not initialized. Call create_instance() first.")
        return cls._instance

    @classmethod
    def create_instance(cls, parent: QObject | None = None) -> QtAppContext:
        """Create the singleton instance.

        Args:
            parent: Optional parent QObject

        Returns:
            QtAppContext: The newly created instance

        """
        if cls._instance is not None:
            logger.warning("QtAppContext already exists. Returning existing instance.")
            return cls._instance

        return cls(parent)

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing)."""
        cls._instance = None
        AppContext.reset_instance()

    # =====================================
    # Delegate all methods to AppContext
    # =====================================

    @property
    def file_store(self):
        """Get the FileStore instance."""
        return self._app_context.file_store

    @property
    def selection_store(self):
        """Get the SelectionStore instance."""
        return self._app_context.selection_store

    def get_files(self) -> list[FileItem]:
        """Get current file list."""
        return self._app_context.get_files()

    def set_files(self, files: list[FileItem]) -> None:
        """Set current file list and emit signal."""
        self._app_context.set_files(files)
        self.files_changed.emit(files)

    def get_current_folder(self) -> str | None:
        """Get current folder path."""
        return self._app_context.get_current_folder()

    def set_current_folder(self, folder_path: str | None, recursive: bool = False) -> None:
        """Set current folder path and recursive mode."""
        self._app_context.set_current_folder(folder_path, recursive)

    def is_recursive_mode(self) -> bool:
        """Check if current folder was loaded recursively."""
        return self._app_context.is_recursive_mode()

    def set_recursive_mode(self, recursive: bool) -> None:
        """Set recursive mode flag."""
        self._app_context.set_recursive_mode(recursive)

    def get_selected_rows(self) -> set[int]:
        """Get currently selected row indices."""
        return self._app_context.get_selected_rows()

    def set_selected_rows(self, rows: set[int]) -> None:
        """Set selected row indices."""
        self._app_context.set_selected_rows(rows)

    def get_checked_rows(self) -> set[int]:
        """Get currently checked row indices."""
        return self._app_context.get_checked_rows()

    def set_checked_rows(self, rows: set[int]) -> None:
        """Set checked row indices."""
        self._app_context.set_checked_rows(rows)

    def get_metadata(self, file_path: str) -> dict[str, Any] | None:
        """Get metadata for a file."""
        return self._app_context.get_metadata(file_path)

    def set_metadata(self, file_path: str, metadata: dict[str, Any]) -> None:
        """Set metadata for a file and emit signal."""
        self._app_context.set_metadata(file_path, metadata)
        self.metadata_changed.emit(file_path, metadata)

    def register_manager(self, name: str, manager: Any) -> None:
        """Register a manager in the global registry."""
        self._app_context.register_manager(name, manager)

    def get_manager(self, name: str) -> Any | None:
        """Get a manager from the registry."""
        return self._app_context.get_manager(name)

    def has_manager(self, name: str) -> bool:
        """Check if a manager is registered."""
        return self._app_context.has_manager(name)

    def track_performance(self, operation: str, duration_ms: float) -> None:
        """Track performance metrics for operations."""
        self._app_context.track_performance(operation, duration_ms)

    def get_performance_report(self) -> dict[str, float]:
        """Get performance metrics report."""
        return self._app_context.get_performance_report()

    def is_ready(self) -> bool:
        """Check if context is fully initialized."""
        return self._app_context.is_ready()

    def mark_ready(self) -> None:
        """Mark context as fully initialized."""
        self._app_context.mark_ready()

    def cleanup(self) -> None:
        """Clean up resources before shutdown."""
        self._app_context.cleanup()


# Convenience function
def get_qt_app_context() -> QtAppContext:
    """Get the singleton QtAppContext instance.

    Returns:
        QtAppContext: The singleton instance

    Raises:
        RuntimeError: If context not yet initialized

    """
    return QtAppContext.get_instance()
