"""Module: file_event_handlers.py.

Author: Michael Economou
Date: 2025-12-20

File-related event handlers - browse, folder import, file operations.
Extracted from event_handler_manager.py for better separation of concerns.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PyQt5.QtWidgets import QApplication

from oncutf.core.modifier_handler import decode_modifiers_to_flags
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class FileEventHandlers:
    """Handles file-related events.

    Responsibilities:
    - Browse folder selection
    - Folder import from tree
    - File loading operations
    """

    def __init__(self, parent_window: Any) -> None:
        """Initialize file event handlers with parent window reference."""
        self.parent_window = parent_window
        logger.debug("FileEventHandlers initialized", extra={"dev_only": True})

    def handle_browse(self) -> None:
        """Opens a file dialog to select a folder and loads its files.
        Supports modifier keys for different loading modes:
        - Normal: Replace + shallow (skip metadata)
        - Ctrl: Replace + recursive (skip metadata)
        - Shift: Merge + shallow (skip metadata)
        - Ctrl+Shift: Merge + recursive (skip metadata).
        """
        from oncutf.ui.services.folder_selection import select_folder

        folder_path = select_folder(
            self.parent_window,
            "Select Folder",
            self.parent_window.current_folder_path or str(Path.home()),
        )

        if folder_path:
            # Get current modifiers at time of selection
            modifiers = QApplication.keyboardModifiers()
            merge_mode, recursive, action_type = decode_modifiers_to_flags(modifiers)

            logger.info("User selected folder: %s (%s)", folder_path, action_type)

            # Use controller for orchestration (proper architecture)
            if Path(folder_path).is_dir():
                self.parent_window.file_load_controller.load_folder(
                    folder_path, merge_mode, recursive
                )

            # Update folder tree selection if replace mode
            if (
                not merge_mode
                and hasattr(self.parent_window, "dir_model")
                and hasattr(self.parent_window, "folder_tree")
                and hasattr(self.parent_window.dir_model, "index")
            ):
                index = self.parent_window.dir_model.index(folder_path)
                self.parent_window.folder_tree.setCurrentIndex(index)
        else:
            logger.debug("User cancelled folder selection", extra={"dev_only": True})

    def handle_folder_import(self) -> None:
        """Handle folder import from browse button."""
        selected_path = self.parent_window.folder_tree.get_selected_path()
        if not selected_path:
            logger.debug("No folder selected", extra={"dev_only": True})
            return

        # Get current modifiers
        modifiers = QApplication.keyboardModifiers()
        merge_mode, recursive, _ = decode_modifiers_to_flags(modifiers)

        # Use controller for orchestration (proper architecture)
        self.parent_window.file_load_controller.load_folder(selected_path, merge_mode, recursive)
