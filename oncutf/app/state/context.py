"""Module: context.py - Qt-free application state container.

Author: Michael Economou
Date: 2026-01-25

AppContext - Pure Python state management without Qt dependencies.

This is the Qt-free core of QtAppContext, providing:
- Centralized state storage
- Manager registry
- Performance tracking
- No Qt signals/slots

For Qt-aware version with signals, see ui/adapters/qt_app_context.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.app.state.file_store import FileStore
    from oncutf.app.state.selection_store import SelectionStore
    from oncutf.app.types import MetadataCache
    from oncutf.models.file_item import FileItem

logger = get_cached_logger(__name__)


class AppContext:
    """Qt-free application state container.

    Provides centralized access to application state without Qt dependencies:
    - File state management
    - Selection handling
    - Metadata coordination
    - Manager registry
    - Performance metrics

    This is a pure Python singleton that can be used in non-Qt code.
    For Qt-aware version with signals, see QtAppContext in ui/adapters/.
    """

    _instance: AppContext | None = None

    def __init__(self):
        """Initialize singleton application context."""
        # Ensure singleton
        if AppContext._instance is not None:
            raise RuntimeError("AppContext is a singleton. Use get_instance()")
        AppContext._instance = self

        # Core stores (will be initialized gradually)
        self._file_store: FileStore | None = None
        self._selection_store: SelectionStore | None = None

        # Manager registry for centralized manager access
        self._managers: dict[str, Any] = {}

        # State containers
        self._files: list[FileItem] = []
        self._selected_rows: set[int] = set()
        self._checked_rows: set[int] = set()
        self._metadata_cache: MetadataCache = {}
        self._current_folder: str | None = None
        self._recursive_mode: bool = False

        # Performance tracking
        self._performance_metrics: dict[str, float] = {}

        # Ready flag
        self._is_ready = False

        logger.info("AppContext initialized (Qt-free)", extra={"dev_only": True})

    def initialize_stores(self) -> None:
        """Initialize core stores after basic setup is complete."""
        if self._file_store is None:
            from oncutf.app.state.file_store import FileStore

            self._file_store = FileStore()
            logger.info("FileStore initialized in AppContext", extra={"dev_only": True})

        if self._selection_store is None:
            from oncutf.app.state.selection_store import SelectionStore

            self._selection_store = SelectionStore()
            logger.info("SelectionStore initialized in AppContext", extra={"dev_only": True})

    @classmethod
    def get_instance(cls) -> AppContext:
        """Get the singleton instance.

        Returns:
            AppContext: The singleton instance

        Raises:
            RuntimeError: If instance has not been created yet

        """
        if cls._instance is None:
            raise RuntimeError("AppContext not initialized. Call create_instance() first.")
        return cls._instance

    @classmethod
    def create_instance(cls) -> AppContext:
        """Create the singleton instance.

        Returns:
            AppContext: The newly created instance

        """
        if cls._instance is not None:
            logger.warning("AppContext already exists. Returning existing instance.")
            return cls._instance

        return cls()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing)."""
        cls._instance = None

    # =====================================
    # File Management
    # =====================================

    @property
    def file_store(self) -> FileStore:
        """Get the FileStore instance, initializing if needed."""
        if self._file_store is None:
            self.initialize_stores()
        assert self._file_store is not None
        return self._file_store

    @property
    def selection_store(self) -> SelectionStore:
        """Get the SelectionStore instance, initializing if needed."""
        if self._selection_store is None:
            self.initialize_stores()
        assert self._selection_store is not None
        return self._selection_store

    def get_files(self) -> list[FileItem]:
        """Get current file list."""
        return self._files.copy()

    def set_files(self, files: list[FileItem]) -> None:
        """Set current file list."""
        self._files = files.copy()
        logger.debug("Files updated: %d items", len(files))

    def get_current_folder(self) -> str | None:
        """Get current folder path."""
        return self._current_folder

    def set_current_folder(self, folder_path: str | None, recursive: bool = False) -> None:
        """Set current folder path and recursive mode."""
        self._current_folder = folder_path
        self._recursive_mode = recursive

        if self._file_store is not None and folder_path:
            self._file_store.set_current_folder(folder_path)

        logger.debug("Current folder: %s, recursive: %s", folder_path, recursive)

    def is_recursive_mode(self) -> bool:
        """Check if current folder was loaded recursively."""
        return self._recursive_mode

    def set_recursive_mode(self, recursive: bool) -> None:
        """Set recursive mode flag."""
        self._recursive_mode = recursive

    # =====================================
    # Selection Management
    # =====================================

    def get_selected_rows(self) -> set[int]:
        """Get currently selected row indices."""
        return self.selection_store.get_selected_rows()

    def set_selected_rows(self, rows: set[int]) -> None:
        """Set selected row indices."""
        self.selection_store.set_selected_rows(rows)

    def get_checked_rows(self) -> set[int]:
        """Get currently checked row indices."""
        return self.selection_store.get_checked_rows()

    def set_checked_rows(self, rows: set[int]) -> None:
        """Set checked row indices."""
        self.selection_store.set_checked_rows(rows)

    # =====================================
    # Metadata Management
    # =====================================

    def get_metadata(self, file_path: str) -> dict[str, Any] | None:
        """Get metadata for a file."""
        return self._metadata_cache.get(file_path)

    def set_metadata(self, file_path: str, metadata: dict[str, Any]) -> None:
        """Set metadata for a file."""
        self._metadata_cache[file_path] = metadata
        logger.debug("Metadata updated for: %s", file_path)

    # =====================================
    # Manager Registry
    # =====================================

    def register_manager(self, name: str, manager: Any) -> None:
        """Register a manager in the global registry."""
        self._managers[name] = manager
        logger.debug("Manager registered: %s", name)

    def get_manager(self, name: str) -> Any | None:
        """Get a manager from the registry."""
        return self._managers.get(name)

    def has_manager(self, name: str) -> bool:
        """Check if a manager is registered."""
        return name in self._managers

    # =====================================
    # Performance Tracking
    # =====================================

    def track_performance(self, operation: str, duration_ms: float) -> None:
        """Track performance metrics for operations."""
        self._performance_metrics[operation] = duration_ms
        logger.debug("Performance: %s took %.1fms", operation, duration_ms)

    def get_performance_report(self) -> dict[str, float]:
        """Get performance metrics report."""
        return self._performance_metrics.copy()

    # =====================================
    # Lifecycle Management
    # =====================================

    def is_ready(self) -> bool:
        """Check if context is fully initialized."""
        return self._is_ready

    def mark_ready(self) -> None:
        """Mark context as fully initialized."""
        self._is_ready = True
        logger.info("AppContext is ready")

    def cleanup(self) -> None:
        """Clean up resources before shutdown."""
        self._files.clear()
        self._selected_rows.clear()
        self._checked_rows.clear()
        self._metadata_cache.clear()
        self._performance_metrics.clear()
        logger.info("AppContext cleaned up")


# Convenience function
def get_app_context() -> AppContext:
    """Get the singleton AppContext instance.

    Returns:
        AppContext: The singleton instance

    Raises:
        RuntimeError: If context not yet initialized

    """
    return AppContext.get_instance()
