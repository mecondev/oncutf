"""Application Context - Centralized state management.

This module provides centralized access to application state, eliminating
the need for complex parent-child traversal patterns throughout the codebase.
Current implementation is a skeleton that will gradually replace
distributed state management across widgets.

Author: Michael Economou
Date: 2025-05-31
"""

from typing import TYPE_CHECKING, Any

from oncutf.core.pyqt_imports import QObject, pyqtSignal
from oncutf.core.type_aliases import MetadataCache
from oncutf.utils.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.core.file_store import FileStore
    from oncutf.core.selection_store import SelectionStore

logger = get_cached_logger(__name__)


class ApplicationContext(QObject):
    """
    Centralized application state and coordination hub.

    This singleton provides fast access to all application state,
    eliminating expensive parent widget traversals and improving performance.

    Features:
    - Centralized file state management
    - Unified selection handling
    - Metadata store coordination
    - Event-driven architecture
    """

    # Signals for state changes
    files_changed = pyqtSignal(list)  # Emitted when file list changes
    selection_changed = pyqtSignal(list)  # Emitted when selection changes
    metadata_changed = pyqtSignal(str, dict)  # Emitted when metadata updates (path, metadata)

    _instance: "ApplicationContext | None" = None

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # Ensure singleton
        if ApplicationContext._instance is not None:
            raise RuntimeError("ApplicationContext is a singleton. Use get_instance()")
        ApplicationContext._instance = self

        # Core stores (will be initialized gradually)
        self._file_store: FileStore | None = None
        self._selection_store: SelectionStore | None = None

        # Manager registry (Phase 2: centralized manager access)
        self._managers: dict[str, Any] = {}

        # Legacy state containers (will be removed gradually)
        self._files: list[Any] = []  # TODO: Replace with FileItem when available
        self._selected_rows: set[int] = set()
        self._metadata_cache: MetadataCache = {}
        self._current_folder: str | None = None
        self._recursive_mode: bool = False  # Track if folder loaded recursively

        # Performance tracking
        self._performance_metrics: dict[str, float] = {}

        # Ready flag (will be used to ensure proper initialization)
        self._is_ready = False

        logger.info("ApplicationContext initialized (skeleton mode)", extra={"dev_only": True})

    def initialize_stores(self) -> None:
        """
        Initialize core stores. Called after basic setup is complete.
        This allows for proper dependency injection and delayed initialization.
        """
        if self._file_store is None:
            # Import here to avoid circular dependencies
            from oncutf.core.file_store import FileStore

            self._file_store = FileStore(parent=self)
            # Connect FileStore signals to ApplicationContext signals
            self._file_store.files_loaded.connect(self._on_files_loaded)
            self._file_store.folder_changed.connect(self._on_folder_changed)

            logger.info("FileStore initialized in ApplicationContext", extra={"dev_only": True})

        if self._selection_store is None:
            # Import here to avoid circular dependencies
            from oncutf.core.selection.selection_store import SelectionStore

            self._selection_store = SelectionStore(parent=self)
            # Connect SelectionStore signals to ApplicationContext signals
            self._selection_store.selection_changed.connect(self._on_selection_changed)
            self._selection_store.checked_changed.connect(self._on_checked_changed)

            logger.info(
                "SelectionStore initialized in ApplicationContext", extra={"dev_only": True}
            )

    def _on_files_loaded(self, files: list[Any]) -> None:
        """Handle files loaded from FileStore."""
        self._files = files.copy()
        self.files_changed.emit(self._files)
        logger.debug(
            "ApplicationContext: Files loaded signal relayed: %d files",
            len(files),
            extra={"dev_only": True},
        )

    def _on_folder_changed(self, folder_path: str) -> None:
        """Handle folder change from FileStore."""
        self._current_folder = folder_path
        logger.debug(
            "ApplicationContext: Folder changed to %s",
            folder_path,
            extra={"dev_only": True},
        )

    def _on_selection_changed(self, selected_rows: list[int]) -> None:
        """Handle selection changed from SelectionStore."""
        self._selected_rows = set(selected_rows)  # Convert back to set for internal storage

        # Emit with backward compatibility check
        try:
            self.selection_changed.emit(selected_rows)
        except TypeError:
            # Fallback: convert to set if the signal expects set type
            logger.debug(
                "ApplicationContext: Converting list to set for signal compatibility",
                extra={"dev_only": True},
            )
            self.selection_changed.emit(set(selected_rows))

        logger.debug(
            "ApplicationContext: Selection changed signal relayed: %d rows",
            len(selected_rows),
            extra={"dev_only": True},
        )

    def _on_checked_changed(self, checked_rows: list[int]) -> None:
        """Handle checked state changed from SelectionStore."""
        # For now, just log it - will be used by file model updates later
        logger.debug("ApplicationContext: Checked state changed: %d rows", len(checked_rows))

    @classmethod
    def get_instance(cls) -> "ApplicationContext":
        """
        Get the singleton instance of ApplicationContext.

        Returns:
            ApplicationContext: The singleton instance

        Raises:
            RuntimeError: If instance has not been created yet
        """
        if cls._instance is None:
            raise RuntimeError("ApplicationContext not initialized. Call create_instance() first.")
        return cls._instance

    @classmethod
    def create_instance(cls, parent: QObject | None = None) -> "ApplicationContext":
        """
        Create the singleton instance of ApplicationContext.

        Args:
            parent: Optional parent QObject

        Returns:
            ApplicationContext: The newly created instance
        """
        if cls._instance is not None:
            logger.warning("ApplicationContext already exists. Returning existing instance.")
            return cls._instance

        return cls(parent)

    # =====================================
    # File Management (Delegated to FileStore)
    # =====================================

    @property
    def file_store(self) -> "FileStore":
        """Get the FileStore instance, initializing if needed."""
        if self._file_store is None:
            self.initialize_stores()
        assert self._file_store is not None  # For mypy
        return self._file_store

    @property
    def selection_store(self) -> "SelectionStore":
        """Get the SelectionStore instance, initializing if needed."""
        if self._selection_store is None:
            self.initialize_stores()
        assert self._selection_store is not None  # For mypy
        return self._selection_store

    def get_files(self) -> list[Any]:  # TODO: Replace with list[FileItem]
        """Get current file list."""
        return self._files.copy()

    def set_files(self, files: list[Any]) -> None:  # TODO: Replace with list[FileItem]
        """Set current file list (legacy method)."""
        self._files = files.copy()
        self.files_changed.emit(self._files)
        logger.debug("Files updated (legacy): %d items", len(files))

    def get_current_folder(self) -> str | None:
        """Get current folder path."""
        return self._current_folder

    def set_current_folder(self, folder_path: str | None, recursive: bool = False) -> None:
        """
        Set current folder path and recursive mode.

        Args:
            folder_path: Path to the folder, or None to clear
            recursive: Whether the folder was loaded recursively
        """
        self._current_folder = folder_path
        self._recursive_mode = recursive

        # Update FileStore if available
        if self._file_store is not None and folder_path:
            self._file_store.set_current_folder(folder_path)

        logger.debug("Current folder: %s, recursive: %s", folder_path, recursive)

    def is_recursive_mode(self) -> bool:
        """Check if current folder was loaded recursively."""
        return self._recursive_mode

    def set_recursive_mode(self, recursive: bool) -> None:
        """Set recursive mode flag."""
        self._recursive_mode = recursive
        logger.debug("Recursive mode set to: %s", recursive)

    # =====================================
    # Selection Management (Delegated to SelectionStore)
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
    # Metadata Management (Skeleton)
    # =====================================

    def get_metadata(self, file_path: str) -> dict[str, Any] | None:
        """Get metadata for a file (placeholder implementation)."""
        return self._metadata_cache.get(file_path)

    def set_metadata(self, file_path: str, metadata: dict[str, Any]) -> None:
        """Set metadata for a file (placeholder implementation)."""
        self._metadata_cache[file_path] = metadata
        self.metadata_changed.emit(file_path, metadata)
        logger.debug("Metadata updated for: %s", file_path)

    # =====================================
    # Performance Tracking
    # =====================================

    def track_performance(self, operation: str, duration_ms: float) -> None:
        """Track performance metrics for operations."""
        self._performance_metrics[operation] = duration_ms
        logger.debug("Performance: %s took %.1fms", operation, duration_ms)

    def get_performance_report(self) -> dict[str, float]:
        """Get performance metrics report."""
        base_metrics = self._performance_metrics.copy()

        # Add FileStore metrics if available
        if self._file_store is not None:
            file_store_metrics = self._file_store.get_performance_stats()
            base_metrics.update({f"filestore_{k}": v for k, v in file_store_metrics.items()})

        return base_metrics

    # =====================================
    # Manager Registry (Phase 2)
    # =====================================

    def register_manager(self, name: str, manager: Any) -> None:
        """
        Register a manager in the centralized registry.

        This allows components to access managers through the context instead of
        traversing the widget hierarchy (parent_window.some_manager).

        Args:
            name: Unique identifier for the manager (e.g., 'table', 'metadata', 'rename')
            manager: The manager instance to register

        Example:
            context.register_manager('table', TableManager(self))
            context.register_manager('metadata', get_unified_metadata_manager(self))
        """
        if name in self._managers:
            logger.warning(
                "Manager '%s' already registered, overwriting",
                name,
                extra={"dev_only": True},
            )
        self._managers[name] = manager
        logger.debug(
            "Manager '%s' registered: %s",
            name,
            type(manager).__name__,
            extra={"dev_only": True},
        )

    def get_manager(self, name: str) -> Any:
        """
        Get a manager from the registry by name.

        Args:
            name: Manager identifier (e.g., 'table', 'metadata', 'rename')

        Returns:
            The registered manager instance

        Raises:
            KeyError: If manager is not registered

        Example:
            table_mgr = context.get_manager('table')
            metadata_mgr = context.get_manager('metadata')
        """
        if name not in self._managers:
            available = ", ".join(sorted(self._managers.keys()))
            raise KeyError(
                f"Manager '{name}' not registered. Available managers: {available or 'none'}"
            )
        return self._managers[name]

    def has_manager(self, name: str) -> bool:
        """
        Check if a manager is registered.

        Args:
            name: Manager identifier to check

        Returns:
            True if manager is registered, False otherwise
        """
        return name in self._managers

    def list_managers(self) -> list[str]:
        """
        Get list of all registered manager names.

        Returns:
            List of manager names in alphabetical order
        """
        return sorted(self._managers.keys())

    # =====================================
    # Utility Methods
    # =====================================

    def is_ready(self) -> bool:
        """Check if context is fully initialized."""
        return self._is_ready

    def mark_ready(self) -> None:
        """Mark context as fully initialized."""
        self._is_ready = True
        logger.info("ApplicationContext is ready", extra={"dev_only": True})

    def cleanup(self) -> None:
        """Clean up resources before shutdown."""
        # Clean up FileStore
        if self._file_store is not None:
            self._file_store.clear_files()
            self._file_store.clear_cache()

        # Clean up legacy state
        self._files.clear()
        self._selected_rows.clear()
        self._metadata_cache.clear()
        self._performance_metrics.clear()
        logger.info("ApplicationContext cleaned up", extra={"dev_only": True})


# Convenience function for getting the singleton
def get_app_context() -> ApplicationContext:
    """
    Convenience function to get the ApplicationContext singleton.

    Returns:
        ApplicationContext: The singleton instance
    """
    return ApplicationContext.get_instance()
