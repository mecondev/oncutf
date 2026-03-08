"""Qt implementation of MetadataUIBridge.

Wraps the parent_window reference to provide cache access, model updates,
display updates, and status bar operations for MetadataLoader.

Author: Michael Economou
Date: 2026-03-08
"""

from __future__ import annotations

from typing import Any

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class QtMetadataUIBridge:
    """MetadataUIBridge implementation backed by a Qt MainWindow."""

    def __init__(self, parent_window: Any) -> None:
        """Wrap *parent_window* as a MetadataUIBridge."""
        self._window = parent_window

    # -- dialog parent --------------------------------------------------------

    @property
    def dialog_parent(self) -> Any:
        return self._window

    # -- cache operations -----------------------------------------------------

    def cache_get_entries_batch(self, paths: list[str]) -> dict[str, Any]:
        if self._window and hasattr(self._window, "metadata_cache"):
            return self._window.metadata_cache.get_entries_batch(paths)
        return {}

    def cache_get_entry(self, path: str) -> Any:
        if self._window and hasattr(self._window, "metadata_cache"):
            return self._window.metadata_cache.get_entry(path)
        return None

    def cache_set(self, path: str, data: dict[str, Any], *, is_extended: bool) -> None:
        if self._window and hasattr(self._window, "metadata_cache"):
            self._window.metadata_cache.set(path, data, is_extended=is_extended)

    # -- model operations -----------------------------------------------------

    def refresh_model_icons(self) -> None:
        if self._window and hasattr(self._window, "file_model"):
            self._window.file_model.refresh_icons()

    def emit_data_changed(self, full_path: str) -> None:
        if not self._window or not hasattr(self._window, "file_model"):
            return
        try:
            from oncutf.app.services.ui_events import get_item_data_roles
            from oncutf.utils.filesystem.path_utils import paths_equal

            roles = get_item_data_roles()
            for j, file in enumerate(self._window.file_model.files):
                if paths_equal(file.full_path, full_path):
                    top_left = self._window.file_model.index(j, 0)
                    bottom_right = self._window.file_model.index(
                        j, self._window.file_model.columnCount() - 1
                    )
                    self._window.file_model.dataChanged.emit(
                        top_left,
                        bottom_right,
                        [roles["DecorationRole"], roles["ToolTipRole"]],
                    )
                    break
        except Exception:
            logger.warning(
                "[QtMetadataUIBridge] Failed to emit dataChanged for %s",
                full_path,
                exc_info=True,
            )

    # -- selection / display --------------------------------------------------

    def get_selection_count(self) -> int:
        # Try SelectionStore first (most reliable)
        try:
            from oncutf.app.state.context import get_app_context

            context = get_app_context()
            if context and hasattr(context, "selection_store"):
                return len(context.selection_store.get_selected_rows())
        except Exception:
            pass

        # Fallback: check file_list_view selection
        if self._window and hasattr(self._window, "file_list_view"):
            selection_model = self._window.file_list_view.selectionModel()
            if selection_model:
                return len(selection_model.selectedRows())

        return 0

    def display_metadata(
        self, metadata: dict[str, Any] | None, selection_count: int, context: str
    ) -> None:
        tree_view = None
        if self._window and hasattr(self._window, "metadata_tree_view"):
            tree_view = self._window.metadata_tree_view
        if not tree_view:
            return

        if hasattr(tree_view, "smart_display_metadata_or_empty_state"):
            tree_view.smart_display_metadata_or_empty_state(metadata, selection_count, context)
        elif selection_count == 1 and metadata:
            if hasattr(tree_view, "display_metadata"):
                tree_view.display_metadata(metadata, context)
        elif hasattr(tree_view, "show_empty_state"):
            if selection_count > 1:
                tree_view.show_empty_state(f"{selection_count} files selected")
            elif selection_count == 0:
                tree_view.show_empty_state("No file selected")
            else:
                tree_view.show_empty_state("No metadata available")

    # -- status ---------------------------------------------------------------

    def set_metadata_status(
        self,
        message: str,
        *,
        operation_type: str = "",
        file_count: int = 0,
        auto_reset: bool = False,
    ) -> None:
        if self._window and hasattr(self._window, "status_manager"):
            self._window.status_manager.set_metadata_status(
                message,
                operation_type=operation_type,
                file_count=file_count,
                auto_reset=auto_reset,
            )
