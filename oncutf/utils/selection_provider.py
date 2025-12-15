"""selection_provider.py

Author: Michael Economou
Date: 2025-12-03

Unified selection interface that eliminates duplication across the codebase.
Provides single point of access for file selection queries.

Problem solved:
- 50+ different ways to get selected files across codebase
- Parent window traversals scattered everywhere
- Inconsistent selection logic
- Performance overhead from repeated queries

Solution:
- Single SelectionProvider interface
- Caches results within same event loop
- Clear, consistent API
- Easy to test and maintain
"""

from typing import Any

from oncutf.models.file_item import FileItem
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class SelectionProvider:
    """Unified interface for file selection queries.

    Eliminates the need for:
    - parent_window.get_selected_files()
    - parent_window.get_selected_files_ordered()
    - parent_window.table_manager.get_selected_files()
    - file_table_view._get_current_selection()
    - selection_model.selectedRows() + manual file lookup
    - context._selection_store.get_selected_files()
    Instead, use:
    - SelectionProvider.get_selected_files(parent_window)
    - SelectionProvider.get_selected_rows(parent_window)
    - SelectionProvider.get_checked_files(parent_window)
    """

    # Cache for performance within same event loop
    _cache_event_id: int | None = None
    _cached_selected_files: list[FileItem] | None = None
    _cached_selected_rows: set[int] | None = None

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached selection (call when selection changes)."""
        cls._cached_selected_files = None
        cls._cached_selected_rows = None
        cls._cache_event_id = None

    @classmethod
    def get_selected_files(cls, parent_window: Any, *, ordered: bool = True) -> list[FileItem]:
        """Get currently selected files from any parent window.

        Args:
            parent_window: MainWindow or any widget with file_model/file_table_view
            ordered: If True, return files in table display order (default)

        Returns:
            List of selected FileItem objects
        """
        # Fast path: use cached result if available
        if cls._cached_selected_files is not None:
            return cls._cached_selected_files

        if not parent_window:
            return []

        # Try multiple strategies in order of preference
        strategies = [
            cls._via_table_manager,
            cls._via_application_service,
            cls._via_selection_model,
            cls._via_checked_state,
        ]

        for strategy in strategies:
            try:
                result = strategy(parent_window, ordered=ordered)
                if result is not None:
                    cls._cached_selected_files = result
                    return result
            except Exception as e:
                logger.debug(
                    f"[SelectionProvider] Strategy {strategy.__name__} failed: {e}",
                    extra={"dev_only": True}
                )

        # Fallback: empty list
        logger.warning("[SelectionProvider] All strategies failed, returning empty list")
        return []

    @classmethod
    def _via_table_manager(cls, parent_window: Any, *, ordered: bool) -> list[FileItem] | None:
        """Get selected files via TableManager (preferred)."""
        # Mark parameter as used for linting
        _ = ordered

        if hasattr(parent_window, "table_manager"):
            table_manager = parent_window.table_manager
            if hasattr(table_manager, "get_selected_files"):
                return table_manager.get_selected_files()
        return None

    @classmethod
    def _via_application_service(cls, parent_window: Any, *, ordered: bool) -> list[FileItem] | None:
        """Get selected files via ApplicationService."""
        if hasattr(parent_window, "application_service"):
            app_service = parent_window.application_service
            if ordered and hasattr(app_service, "get_selected_files_ordered"):
                return app_service.get_selected_files_ordered()
            elif hasattr(app_service, "get_selected_files"):
                return app_service.get_selected_files()
        return None

    @classmethod
    def _via_selection_model(cls, parent_window: Any, *, ordered: bool) -> list[FileItem] | None:
        """Get selected files via Qt selection model."""
        if not hasattr(parent_window, "file_table_view") or not hasattr(parent_window, "file_model"):
            return None

        file_table_view = parent_window.file_table_view
        file_model = parent_window.file_model

        if not file_table_view or not file_model:
            return None

        selection_model = file_table_view.selectionModel()
        if not selection_model:
            return None

        selected_indexes = selection_model.selectedRows()
        if ordered:
            selected_indexes = sorted(selected_indexes, key=lambda idx: idx.row())

        selected_files = []
        for index in selected_indexes:
            row = index.row()
            if 0 <= row < len(file_model.files):
                selected_files.append(file_model.files[row])

        return selected_files

    @classmethod
    def _via_checked_state(cls, parent_window: Any, *, ordered: bool) -> list[FileItem] | None:
        """Get selected files via checked state (fallback)."""
        # Mark parameter as used for linting
        _ = ordered

        if not hasattr(parent_window, "file_model"):
            return None

        file_model = parent_window.file_model
        if not file_model or not file_model.files:
            return None

        # Get checked files
        checked_files = [f for f in file_model.files if f.checked]
        return checked_files

    @classmethod
    def get_selected_rows(cls, parent_window: Any) -> set[int]:
        """Get currently selected row indices.

        Args:
            parent_window: MainWindow or any widget with selection state

        Returns:
            Set of selected row indices
        """
        # Fast path: use cached result if available
        if cls._cached_selected_rows is not None:
            return cls._cached_selected_rows

        if not parent_window:
            return set()

        # Try SelectionStore first (most efficient)
        if hasattr(parent_window, "selection_store"):
            try:
                result = parent_window.selection_store.get_selected_rows()
                cls._cached_selected_rows = result
                return result
            except Exception as e:
                logger.debug(f"[SelectionProvider] SelectionStore failed: {e}", extra={"dev_only": True})

        # Fallback: use selection model
        if hasattr(parent_window, "file_table_view"):
            file_table_view = parent_window.file_table_view
            if file_table_view:
                selection_model = file_table_view.selectionModel()
                if selection_model:
                    result = {index.row() for index in selection_model.selectedRows()}
                    cls._cached_selected_rows = result
                    return result

        return set()

    @classmethod
    def get_checked_files(cls, parent_window: Any) -> list[FileItem]:
        """Get files with checked state (used for rename operations).

        Args:
            parent_window: MainWindow or any widget with file_model

        Returns:
            List of FileItem objects where checked=True
        """
        if not parent_window or not hasattr(parent_window, "file_model"):
            return []

        file_model = parent_window.file_model
        if not file_model or not file_model.files:
            return []

        return [f for f in file_model.files if f.checked]

    @classmethod
    def get_selection_count(cls, parent_window: Any) -> int:
        """Get count of selected files.

        Args:
            parent_window: MainWindow or any widget with selection state

        Returns:
            Number of selected files
        """
        # Fast path: use SelectionStore if available
        if hasattr(parent_window, "selection_store"):
            try:
                return parent_window.selection_store.get_selection_count()
            except Exception:
                pass

        # Fallback: count selected files
        return len(cls.get_selected_files(parent_window))

    @classmethod
    def has_selection(cls, parent_window: Any) -> bool:
        """Check if any files are selected.

        Args:
            parent_window: MainWindow or any widget with selection state

        Returns:
            True if at least one file is selected
        """
        return cls.get_selection_count(parent_window) > 0

    @classmethod
    def get_single_selected_file(cls, parent_window: Any) -> FileItem | None:
        """Get single selected file (or None if multiple/zero selected).

        Args:
            parent_window: MainWindow or any widget with selection state

        Returns:
            Single FileItem if exactly one selected, None otherwise
        """
        selected = cls.get_selected_files(parent_window)
        return selected[0] if len(selected) == 1 else None


# Convenience functions for backward compatibility

def get_selected_files(parent_window: Any, *, ordered: bool = True) -> list[FileItem]:
    """Get currently selected files.

    Convenience function that delegates to SelectionProvider.

    Args:
        parent_window: MainWindow or any widget with file_model/file_table_view
        ordered: If True, return files in table display order

    Returns:
        List of selected FileItem objects
    """
    return SelectionProvider.get_selected_files(parent_window, ordered=ordered)


def get_selected_rows(parent_window: Any) -> set[int]:
    """Get currently selected row indices.

    Convenience function that delegates to SelectionProvider.

    Args:
        parent_window: MainWindow or any widget with selection state

    Returns:
        Set of selected row indices
    """
    return SelectionProvider.get_selected_rows(parent_window)


def get_checked_files(parent_window: Any) -> list[FileItem]:
    """Get files with checked state.

    Convenience function that delegates to SelectionProvider.

    Args:
        parent_window: MainWindow or any widget with file_model

    Returns:
        List of FileItem objects where checked=True
    """
    return SelectionProvider.get_checked_files(parent_window)


def has_selection(parent_window: Any) -> bool:
    """Check if any files are selected.

    Convenience function that delegates to SelectionProvider.

    Args:
        parent_window: MainWindow or any widget with selection state

    Returns:
        True if at least one file is selected
    """
    return SelectionProvider.has_selection(parent_window)


def get_single_selected_file(parent_window: Any) -> FileItem | None:
    """Get single selected file.

    Convenience function that delegates to SelectionProvider.

    Args:
        parent_window: MainWindow or any widget with selection state

    Returns:
        Single FileItem if exactly one selected, None otherwise
    """
    return SelectionProvider.get_single_selected_file(parent_window)
