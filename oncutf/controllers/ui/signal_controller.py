"""Signal Controller.

Author: Michael Economou
Date: 2026-01-02

Handles signal connections between UI components.
"""

from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAction, QLineEdit, QMenu

from oncutf.controllers.ui.protocols import SignalContext
from oncutf.ui.helpers.icons_loader import get_menu_icon
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import (
    schedule_selection_update,
    schedule_ui_update,
)

logger = get_cached_logger(__name__)


class SignalController:
    """Controller for UI signal connections.

    Responsibilities:
    - Connect all UI signals to handlers
    - Event handler setup
    - Signal routing between components
    - Search field handlers
    """

    def __init__(self, parent_window: SignalContext):
        """Initialize controller with parent window reference.

        Args:
            parent_window: The main application window

        """
        self.parent_window = parent_window
        logger.debug("SignalController initialized", extra={"dev_only": True})

    def setup(self) -> None:
        """Connect all UI signals to their handlers."""
        self._setup_event_filter()
        self._setup_header_signals()
        self._setup_button_signals()
        self._setup_folder_tree_signals()
        self._setup_splitter_signals()
        self._setup_file_table_signals()
        self._setup_thumbnail_viewport_signals()
        self._setup_metadata_signals()
        self._setup_rename_signals()
        self._setup_preview_signals()
        self._enable_selection_store()

    def _setup_event_filter(self) -> None:
        """Install event filter on main window."""
        self.parent_window.installEventFilter(self.parent_window)

    def _setup_header_signals(self) -> None:
        """Connect header signals."""
        self.parent_window.header.sectionClicked.connect(self.parent_window.sort_by_column)

    def _setup_button_signals(self) -> None:
        """Connect button signals."""
        self.parent_window.select_folder_button.clicked.connect(
            self.parent_window.handle_folder_import
        )
        self.parent_window.browse_folder_button.clicked.connect(self.parent_window.handle_browse)
        self.parent_window.rename_button.clicked.connect(self.parent_window.rename_files)

    def _setup_folder_tree_signals(self) -> None:
        """Connect folder tree signals."""
        self.parent_window.folder_tree.folder_selected.connect(
            self.parent_window.handle_folder_import
        )

    def _setup_splitter_signals(self) -> None:
        """Connect splitter signals."""
        # Connect to SplitterManager
        self.parent_window.horizontal_splitter.splitterMoved.connect(
            self.parent_window.splitter_manager.on_horizontal_splitter_moved
        )
        self.parent_window.vertical_splitter.splitterMoved.connect(
            self.parent_window.splitter_manager.on_vertical_splitter_moved
        )
        self.parent_window.lower_section_splitter.splitterMoved.connect(
            self.parent_window.splitter_manager.on_lower_section_splitter_moved
        )

        # Connect callbacks for tree view
        self.parent_window.horizontal_splitter.splitterMoved.connect(
            self.parent_window.folder_tree.on_horizontal_splitter_moved
        )
        self.parent_window.vertical_splitter.splitterMoved.connect(
            self.parent_window.folder_tree.on_vertical_splitter_moved
        )

        # Connect callbacks for file table view
        self.parent_window.horizontal_splitter.splitterMoved.connect(
            self.parent_window.file_table_view.on_horizontal_splitter_moved
        )
        self.parent_window.vertical_splitter.splitterMoved.connect(
            self.parent_window.file_table_view.on_vertical_splitter_moved
        )

        # Connect to preview tables view
        self.parent_window.vertical_splitter.splitterMoved.connect(
            self.parent_window.preview_tables_view.handle_splitter_moved
        )

    def _setup_file_table_signals(self) -> None:
        """Connect file table signals."""
        self.parent_window.file_table_view.clicked.connect(self.parent_window.on_table_row_clicked)
        # NOTE: selection_changed connection is handled in initialization_manager.py
        self.parent_window.file_table_view.files_dropped.connect(
            self.parent_window.load_files_from_dropped_items
        )
        self.parent_window.file_model.sort_changed.connect(
            self.parent_window.request_preview_update
        )
        self.parent_window.file_table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.parent_window.file_table_view.customContextMenuRequested.connect(
            self.parent_window.handle_table_context_menu
        )

        # Connect F5 refresh request
        self.parent_window.file_table_view.refresh_requested.connect(self._refresh_file_table)

    def _setup_thumbnail_viewport_signals(self) -> None:
        """Connect thumbnail viewport signals."""
        # Check if thumbnail_viewport exists (may not be created in all contexts)
        if not hasattr(self.parent_window, "thumbnail_viewport"):
            logger.debug("[SignalController] thumbnail_viewport not found, skipping signal setup")
            return

        # Connect files dropped signal to the same handler as file table
        self.parent_window.thumbnail_viewport.files_dropped.connect(
            self.parent_window.load_files_from_dropped_items
        )
        logger.debug("[SignalController] Thumbnail viewport signals connected")

    def _setup_metadata_signals(self) -> None:
        """Connect metadata tree signals."""
        self.parent_window.metadata_tree_view.value_edited.connect(
            self.parent_window.on_metadata_value_edited
        )
        self.parent_window.metadata_tree_view.value_reset.connect(
            self.parent_window.on_metadata_value_reset
        )
        self.parent_window.metadata_tree_view.value_copied.connect(
            self.parent_window.on_metadata_value_copied
        )

        # Connect search field signals
        self.parent_window.clear_search_action.triggered.connect(self._clear_metadata_search)
        self.parent_window.metadata_search_field.textChanged.connect(
            self._on_metadata_search_text_changed
        )
        self.parent_window.metadata_search_field.customContextMenuRequested.connect(
            lambda pos: self._show_search_context_menu(
                pos, self.parent_window.metadata_search_field
            )
        )

    def _setup_preview_signals(self) -> None:
        """Connect preview view signals."""
        self.parent_window.preview_tables_view.status_updated.connect(
            self.parent_window._update_status_from_preview
        )
        self.parent_window.preview_tables_view.refresh_requested.connect(
            self.parent_window.request_preview_update
        )

    def _setup_rename_signals(self) -> None:
        """Connect rename modules and final transform signals."""
        # Debounce preview updates from module config changes
        self.parent_window.rename_modules_area.updated.connect(
            self.parent_window.request_preview_update_debounced
        )
        self.parent_window.rename_modules_area.updated.connect(
            self.parent_window.utility_manager.clear_preview_cache
        )

        # Final transform container signals
        self.parent_window.final_transform_container.updated.connect(
            self.parent_window.request_preview_update_debounced
        )
        self.parent_window.final_transform_container.updated.connect(
            self.parent_window.utility_manager.clear_preview_cache
        )
        self.parent_window.final_transform_container.add_module_requested.connect(
            self.parent_window.rename_modules_area.add_module
        )
        self.parent_window.final_transform_container.remove_module_requested.connect(
            self.parent_window.rename_modules_area.remove_last_module
        )

        # Update remove button state
        self.parent_window.rename_modules_area.updated.connect(
            lambda: self.parent_window.final_transform_container.set_remove_button_enabled(
                len(self.parent_window.rename_modules_area.module_widgets) > 1
            )
        )

    def _enable_selection_store(self) -> None:
        """Enable SelectionStore mode after signals are connected."""
        schedule_selection_update(self.parent_window._enable_selection_store_mode, 100)

    def _refresh_file_table(self) -> None:
        """Refresh file table (F5) - reloads files and clears ALL state."""
        from oncutf.ui.adapters.qt_app_context import get_qt_app_context
        from oncutf.ui.helpers.cursor_helper import wait_cursor
        from oncutf.ui.helpers.file_table_state_helper import FileTableStateHelper

        logger.info("[FileTable] F5 pressed - refreshing file table with full state reset")

        with wait_cursor():
            metadata_tree_view = getattr(self.parent_window, "metadata_tree_view", None)

            context = get_qt_app_context()
            if context:
                FileTableStateHelper.clear_all_state(
                    self.parent_window.file_table_view, context, metadata_tree_view
                )

            self.parent_window.force_reload()

            if hasattr(self.parent_window, "status_manager"):
                self.parent_window.status_manager.set_file_operation_status(
                    "File table refreshed", success=True, auto_reset=True
                )

    def _show_search_context_menu(self, position: Any, line_edit: QLineEdit) -> None:
        """Show custom context menu for the search field."""
        menu = QMenu(line_edit)

        from oncutf.ui.helpers.stylesheet_utils import inject_font_family

        menu_qss = """
            QMenu {
                background-color: #232323;
                color: #f0ebd8;
                border: none;
                border-radius: 8px;
                font-family: "Inter", "Segoe UI", Arial, sans-serif;
                font-size: 9pt;
                padding: 6px 4px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 3px 16px 3px 8px;
                margin: 1px 2px;
                border-radius: 4px;
                min-height: 16px;
                icon-size: 16px;
            }
            QMenu::item:selected {
                background-color: #748cab;
                color: #0d1321;
            }
            QMenu::item:disabled {
                color: #888888;
            }
            QMenu::icon {
                padding-left: 6px;
                padding-right: 6px;
            }
            QMenu::separator {
                background-color: #5a5a5a;
                height: 1px;
                margin: 4px 8px;
            }
        """
        menu_qss = inject_font_family(menu_qss)
        menu.setStyleSheet(menu_qss)

        undo_action = QAction("Undo", menu)
        undo_action.setIcon(get_menu_icon("undo"))
        undo_action.triggered.connect(line_edit.undo)
        undo_action.setEnabled(line_edit.isUndoAvailable())
        menu.addAction(undo_action)

        redo_action = QAction("Redo", menu)
        redo_action.setIcon(get_menu_icon("redo"))
        redo_action.triggered.connect(line_edit.redo)
        redo_action.setEnabled(line_edit.isRedoAvailable())
        menu.addAction(redo_action)

        menu.addSeparator()

        cut_action = QAction("Cut", menu)
        cut_action.setIcon(get_menu_icon("content_cut"))
        cut_action.triggered.connect(line_edit.cut)
        cut_action.setEnabled(line_edit.hasSelectedText())
        menu.addAction(cut_action)

        copy_action = QAction("Copy", menu)
        copy_action.setIcon(get_menu_icon("content_copy"))
        copy_action.triggered.connect(line_edit.copy)
        copy_action.setEnabled(line_edit.hasSelectedText())
        menu.addAction(copy_action)

        paste_action = QAction("Paste", menu)
        paste_action.setIcon(get_menu_icon("content_paste"))
        paste_action.triggered.connect(line_edit.paste)
        menu.addAction(paste_action)

        menu.addSeparator()

        select_all_action = QAction("Select All", menu)
        select_all_action.setIcon(get_menu_icon("check_box"))
        select_all_action.triggered.connect(line_edit.selectAll)
        select_all_action.setEnabled(bool(line_edit.text()))
        menu.addAction(select_all_action)

        global_pos = line_edit.mapToGlobal(position)
        menu.exec_(global_pos)

    def _on_metadata_search_text_changed(self) -> None:
        """Handle text changes in the metadata search field."""
        text = self.parent_window.metadata_search_field.text()
        self.parent_window.clear_search_action.setVisible(bool(text))
        self.parent_window._metadata_search_text = text

        self.parent_window.metadata_proxy_model.setFilterRegExp(text)

        # Always expand all groups after filtering
        schedule_ui_update(self.parent_window.metadata_tree_view.expandAll, 10)

    def _clear_metadata_search(self) -> None:
        """Clear the metadata search field."""
        self.parent_window.metadata_search_field.clear()
        self.parent_window.clear_search_action.setVisible(False)
        self.parent_window._metadata_search_text = ""
        self.parent_window.metadata_proxy_model.setFilterRegExp("")

        schedule_ui_update(self.parent_window.metadata_tree_view.expandAll, 10)

    def restore_metadata_search_text(self) -> None:
        """Restore the metadata search text from session storage."""
        if (
            hasattr(self.parent_window, "_metadata_search_text")
            and self.parent_window._metadata_search_text
        ):
            self.parent_window.metadata_search_field.setText(
                self.parent_window._metadata_search_text
            )
            self.parent_window.metadata_proxy_model.setFilterRegExp(
                self.parent_window._metadata_search_text
            )
