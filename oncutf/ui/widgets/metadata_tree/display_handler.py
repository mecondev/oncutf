"""Display handler facade for MetadataTreeView.

This module provides backward compatibility by re-exporting from
the split render and ui_state handlers.

Author: Michael Economou
Date: 2025-12-01
Updated: 2026-01-02 - Converted to thin facade delegating to render_handler and ui_state_handler
"""

from typing import TYPE_CHECKING, Any

from oncutf.ui.widgets.metadata_tree.render_handler import TreeRenderHandler
from oncutf.ui.widgets.metadata_tree.ui_state_handler import TreeUiStateHandler
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_tree.view import MetadataTreeView

logger = get_cached_logger(__name__)


class DisplayHandler:
    """Facade for display operations - delegates to render and ui_state handlers.

    This class maintains backward compatibility while the actual logic
    is now split between:
    - TreeRenderHandler: Tree model building and rendering
    - TreeUiStateHandler: UI state, placeholders, and information label

    New code should use the specific handlers directly via view properties:
    - view._render_handler
    - view._ui_state_handler
    """

    def __init__(self, view: "MetadataTreeView") -> None:
        """Initialize the display handler facade.

        Args:
            view: The MetadataTreeView instance
        """
        self.view = view
        # Create the actual handlers
        self._render_handler = TreeRenderHandler(view)
        self._ui_state_handler = TreeUiStateHandler(view)

    # =========================================================================
    # Properties for direct handler access
    # =========================================================================

    @property
    def render(self) -> TreeRenderHandler:
        """Access the render handler directly."""
        return self._render_handler

    @property
    def ui_state(self) -> TreeUiStateHandler:
        """Access the UI state handler directly."""
        return self._ui_state_handler

    # =========================================================================
    # Render Handler Delegations
    # =========================================================================

    def emit_rebuild_tree(self, metadata: dict[str, Any], context: str = "") -> None:
        """Delegate to render handler."""
        self._render_handler.emit_rebuild_tree(metadata, context)

    def rebuild_tree_from_metadata(self, metadata: dict[str, Any], context: str = "") -> None:
        """Delegate to render handler."""
        self._render_handler.rebuild_tree_from_metadata(metadata, context)

    def get_file_path_from_metadata(self, metadata: dict[str, Any]) -> str | None:
        """Delegate to render handler."""
        return self._render_handler.get_file_path_from_metadata(metadata)

    def rebuild_metadata_tree_with_stats(self, display_data: dict[str, Any]) -> None:
        """Delegate to render handler."""
        self._render_handler.rebuild_metadata_tree_with_stats(display_data)

    # =========================================================================
    # UI State Handler Delegations
    # =========================================================================

    def display_placeholder(self, message: str = "No file selected") -> None:
        """Delegate to UI state handler."""
        self._ui_state_handler.display_placeholder(message)

    def clear_tree(self) -> None:
        """Delegate to UI state handler."""
        self._ui_state_handler.clear_tree()

    def display_metadata(self, metadata: dict[str, Any] | None, context: str = "") -> None:
        """Delegate to UI state handler."""
        self._ui_state_handler.display_metadata(metadata, context)

    def update_information_label(self, display_data: dict[str, Any]) -> None:
        """Delegate to UI state handler."""
        self._ui_state_handler.update_information_label(display_data)

    def set_current_file_from_metadata(self, metadata: dict[str, Any]) -> None:
        """Delegate to UI state handler."""
        self._ui_state_handler.set_current_file_from_metadata(metadata)

    def display_file_metadata(self, file_item: Any, context: str = "file_display") -> None:
        """Delegate to UI state handler."""
        self._ui_state_handler.display_file_metadata(file_item, context)

    def cleanup_on_folder_change(self) -> None:
        """Delegate to UI state handler."""
        self._ui_state_handler.cleanup_on_folder_change()

    def sync_placeholder_state(self) -> None:
        """Delegate to UI state handler."""
        self._ui_state_handler.sync_placeholder_state()
