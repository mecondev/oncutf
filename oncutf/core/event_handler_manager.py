"""Module: event_handler_manager.py

Author: Michael Economou
Date: 2025-05-31

Manages all event handling operations for the main window.
Handles browse, folder import, table interactions, context menus, and user actions.

This module now delegates to specialized handlers in oncutf/core/events/:
- FileEventHandlers: browse, folder import
- UIEventHandlers: header toggle, row clicks, double clicks
- ContextMenuHandlers: right-click context menu, bulk rotation, analysis
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from oncutf.core.pyqt_imports import QModelIndex
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.core.events.context_menu import ContextMenuHandlers
    from oncutf.core.events.file_event_handlers import FileEventHandlers
    from oncutf.core.events.ui_event_handlers import UIEventHandlers

logger = get_cached_logger(__name__)


class EventHandlerManager:
    """Manages all event handling operations.

    This is now a facade that delegates to specialized handlers:
    - FileEventHandlers: browse, folder import
    - UIEventHandlers: header toggle, row clicks, double clicks
    - ContextMenuHandlers: right-click context menu, bulk operations

    Features:
    - Browse and folder import handlers
    - Table interaction handlers (context menu, double click, row click)
    - Header toggle handler
    - Splitter movement handlers
    """

    def __init__(self, parent_window: Any) -> None:
        self.parent_window = parent_window

        # Lazy-initialized specialized handlers
        self._file_handlers: FileEventHandlers | None = None
        self._ui_handlers: UIEventHandlers | None = None
        self._context_menu_handlers: ContextMenuHandlers | None = None

        logger.debug("EventHandlerManager initialized", extra={"dev_only": True})

    @property
    def file_handlers(self) -> FileEventHandlers:
        """Lazy-initialized file event handlers."""
        if self._file_handlers is None:
            from oncutf.core.events.file_event_handlers import FileEventHandlers

            self._file_handlers = FileEventHandlers(self.parent_window)
        return self._file_handlers

    @property
    def ui_handlers(self) -> UIEventHandlers:
        """Lazy-initialized UI event handlers."""
        if self._ui_handlers is None:
            from oncutf.core.events.ui_event_handlers import UIEventHandlers

            self._ui_handlers = UIEventHandlers(self.parent_window)
        return self._ui_handlers

    @property
    def context_menu_handlers(self) -> ContextMenuHandlers:
        """Lazy-initialized context menu handlers."""
        if self._context_menu_handlers is None:
            from oncutf.core.events.context_menu import ContextMenuHandlers

            self._context_menu_handlers = ContextMenuHandlers(self.parent_window)
        return self._context_menu_handlers

    # Legacy properties for backward compatibility
    @property
    def hash_ops(self) -> Any:
        """Delegate to context menu handlers for hash operations."""
        return self.context_menu_handlers.hash_ops

    @property
    def metadata_ops(self) -> Any:
        """Delegate to context menu handlers for metadata operations."""
        return self.context_menu_handlers.metadata_ops

    # =====================================
    # Delegated Methods - File Events
    # =====================================

    def handle_browse(self) -> None:
        """Delegate to FileEventHandlers."""
        self.file_handlers.handle_browse()

    def handle_folder_import(self) -> None:
        """Delegate to FileEventHandlers."""
        self.file_handlers.handle_folder_import()

    # =====================================
    # Delegated Methods - UI Events
    # =====================================

    def handle_header_toggle(self, arg: Any) -> None:
        """Delegate to UIEventHandlers."""
        self.ui_handlers.handle_header_toggle(arg)

    def on_table_row_clicked(self, index: QModelIndex) -> None:
        """Delegate to UIEventHandlers."""
        self.ui_handlers.on_table_row_clicked(index)

    def handle_file_double_click(self, index: QModelIndex, modifiers: Any = None) -> None:
        """Delegate to UIEventHandlers."""
        self.ui_handlers.handle_file_double_click(index, modifiers)

    # =====================================
    # Delegated Methods - Context Menu
    # =====================================

    def handle_table_context_menu(self, position: Any) -> None:
        """Delegate to ContextMenuHandlers."""
        self.context_menu_handlers.handle_table_context_menu(position)

    # =====================================
    # Delegated Analysis Methods (for backward compatibility)
    # =====================================

    def _analyze_metadata_state(self, files: list) -> dict:
        """Delegate to ContextMenuHandlers."""
        return self.context_menu_handlers._analyze_metadata_state(files)

    def _analyze_hash_state(self, files: list) -> dict:
        """Delegate to ContextMenuHandlers."""
        return self.context_menu_handlers._analyze_hash_state(files)

    def check_files_status(
        self,
        files: list | None = None,
        check_type: str = "metadata",
        extended: bool = False,
        scope: str = "selected",
    ) -> dict:
        """Delegate to ContextMenuHandlers."""
        return self.context_menu_handlers.check_files_status(
            files=files, check_type=check_type, extended=extended, scope=scope
        )

    def get_files_without_metadata(
        self,
        files: list | None = None,
        extended: bool = False,
        scope: str = "selected",
    ) -> list:
        """Delegate to ContextMenuHandlers."""
        return self.context_menu_handlers.get_files_without_metadata(
            files=files, extended=extended, scope=scope
        )

    def get_files_without_hashes(self, files: list | None = None, scope: str = "selected") -> list:
        """Delegate to ContextMenuHandlers."""
        return self.context_menu_handlers.get_files_without_hashes(files=files, scope=scope)
