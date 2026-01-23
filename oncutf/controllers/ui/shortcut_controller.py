"""Shortcut Controller.

Author: Michael Economou
Date: 2026-01-02

Handles keyboard shortcut registration and management.
"""

from typing import cast

from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut, QWidget

from oncutf.controllers.ui.protocols import ShortcutContext
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ShortcutController:
    """Controller for keyboard shortcut registration.

    Responsibilities:
    - Register file table shortcuts
    - Register global shortcuts
    - Register dialog shortcuts
    """

    def __init__(self, parent_window: ShortcutContext):
        """Initialize controller with parent window reference.

        Args:
            parent_window: The main application window

        """
        self.parent_window = parent_window
        logger.debug("ShortcutController initialized", extra={"dev_only": True})

    def setup(self) -> None:
        """Initialize all keyboard shortcuts."""
        self.parent_window.shortcuts = []

        self._setup_file_table_shortcuts()
        self._setup_global_shortcuts()
        self._setup_other_shortcuts()

    def _setup_file_table_shortcuts(self) -> None:
        """Setup file table shortcuts (selection-based, widget-specific)."""
        from oncutf.config import FILE_TABLE_SHORTCUTS

        file_table_shortcuts = [
            (FILE_TABLE_SHORTCUTS["SELECT_ALL"], self.parent_window.select_all_rows),
            (FILE_TABLE_SHORTCUTS["CLEAR_SELECTION"], self.parent_window.clear_all_selection),
            (FILE_TABLE_SHORTCUTS["INVERT_SELECTION"], self.parent_window.invert_selection),
            (
                FILE_TABLE_SHORTCUTS["CALCULATE_HASH"],
                self.parent_window.shortcut_calculate_hash_selected,
            ),
            # NOTE: REFRESH (F5) removed - now handled via FileTableView.keyPressEvent
            # NOTE: LOAD_METADATA and LOAD_EXTENDED_METADATA moved to global shortcuts
        ]

        for key, handler in file_table_shortcuts:
            shortcut = QShortcut(QKeySequence(key), self.parent_window.file_table_view)
            shortcut.activated.connect(handler)
            self.parent_window.shortcuts.append(shortcut)

    def _setup_global_shortcuts(self) -> None:
        """Setup global shortcuts (attached to main window, work regardless of focus)."""
        from oncutf.config import FILE_TABLE_SHORTCUTS, GLOBAL_SHORTCUTS

        global_shortcuts = [
            (GLOBAL_SHORTCUTS["BROWSE_FOLDER"], self.parent_window.handle_browse),
            (GLOBAL_SHORTCUTS["SAVE_METADATA"], self.parent_window.shortcut_save_all_metadata),
            (GLOBAL_SHORTCUTS["CANCEL_DRAG"], self.parent_window.force_drag_cleanup),
            (GLOBAL_SHORTCUTS["CLEAR_FILE_TABLE"], self.parent_window.clear_file_table_shortcut),
            (GLOBAL_SHORTCUTS["UNDO"], self.parent_window.global_undo),
            (GLOBAL_SHORTCUTS["REDO"], self.parent_window.global_redo),
            (GLOBAL_SHORTCUTS["SHOW_HISTORY"], self.parent_window.show_command_history),
            # Metadata shortcuts - global so they work in both file table and thumbnail views
            (FILE_TABLE_SHORTCUTS["LOAD_METADATA"], self.parent_window.shortcut_load_metadata),
            (
                FILE_TABLE_SHORTCUTS["LOAD_EXTENDED_METADATA"],
                self.parent_window.shortcut_load_extended_metadata,
            ),
        ]

        for key, handler in global_shortcuts:
            shortcut = QShortcut(QKeySequence(key), cast("QWidget", self.parent_window))
            shortcut.activated.connect(handler)
            self.parent_window.shortcuts.append(shortcut)

    def _setup_other_shortcuts(self) -> None:
        """Setup other dialog and utility shortcuts."""
        from oncutf.config import UNDO_REDO_SETTINGS

        other_shortcuts = [
            (
                UNDO_REDO_SETTINGS.get("RESULTS_HASH_LIST_SHORTCUT", "Ctrl+L"),
                self.parent_window.shortcut_manager.show_results_hash_list,
            ),
            (
                "Ctrl+Shift+C",
                self.parent_window.shortcut_manager.auto_color_by_folder_shortcut,
            ),
        ]

        for key, handler in other_shortcuts:
            shortcut = QShortcut(QKeySequence(key), cast("QWidget", self.parent_window))
            shortcut.activated.connect(handler)
            self.parent_window.shortcuts.append(shortcut)
