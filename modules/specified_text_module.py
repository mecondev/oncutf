"""
Module: specified_text_module.py

Author: Michael Economou
Date: 2025-05-31

This module defines a rename module that inserts user-specified text
into filenames. It allows users to prepend, append, or inject static
text at a defined position within the filename.
Used in the oncutf application as one of the modular renaming components.
"""
import os
from typing import Optional

from core.qt_imports import Qt, pyqtSignal, QAction, QLabel, QMenu, QVBoxLayout, QWidget, QApplication

from config import QLABEL_DARK_BG, QLABEL_DARK_BORDER, QLABEL_ERROR_TEXT, QLABEL_INFO_TEXT
from modules.base_module import BaseRenameModule
from utils.filename_validator import validate_filename_part
from utils.icons_loader import get_menu_icon

# initialize logger
from utils.logger_factory import get_cached_logger
from widgets.validated_line_edit import ValidatedLineEdit

logger = get_cached_logger(__name__)


class SpecifiedTextModule(BaseRenameModule):
    """
    A module for inserting user-defined text in filenames.
    """
    updated = pyqtSignal(object)

    def __init__(self, parent: Optional[QWidget]=None) -> None:
        super().__init__(parent)

        # Store reference to current file for "Original Name" feature
        self._current_file = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)  # Match final transformer margins
        layout.setSpacing(0)  # Match final transformer spacing

        self.text_input = ValidatedLineEdit()
        self.text_input.setPlaceholderText("Enter custom text")
        self.text_input.setMaxLength(240)
        # Remove fixed height to prevent clipping
        self._last_value = ""  # Initialize to prevent first empty emit
        self.text_input.textChanged.connect(self.validate_input)

        # Connect validation state change to update module state
        self.text_input.validation_changed.connect(self._on_validation_changed)

        # Set up custom context menu
        self.text_input.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_input.customContextMenuRequested.connect(self._show_context_menu)

        # Add widget with vertical centering
        layout.addStretch()  # Top stretch for centering
        layout.addWidget(self.text_input, 0, Qt.AlignVCenter)
        layout.addStretch()  # Bottom stretch for centering

        # Track if field has ever had content to control empty styling
        self._has_had_content = False

        # Track validation state
        self._is_input_valid = True

    def set_current_file(self, file_item) -> None:
        """
        Set the current file item for the "Original Name" context menu option.

        Args:
            file_item: The FileItem object representing the currently selected file
        """
        self._current_file = file_item

    def _show_context_menu(self, position) -> None:
        """
        Show custom context menu for the text input field.

        Args:
            position: The position where the context menu was requested
        """
        menu = QMenu(self.text_input)

        # Original Name action (always visible, enabled only if we have a current file)
        original_name_action = QAction("Original Name", menu)
        original_name_action.setIcon(get_menu_icon("file"))
        original_name_action.triggered.connect(self._insert_original_name)
        original_name_action.setEnabled(self._current_file is not None)
        menu.addAction(original_name_action)
        menu.addSeparator()

        # Standard editing actions
        undo_action = QAction("Undo", menu)
        undo_action.setIcon(get_menu_icon("rotate-ccw"))
        undo_action.triggered.connect(self.text_input.undo)
        undo_action.setEnabled(self.text_input.isUndoAvailable())
        menu.addAction(undo_action)

        redo_action = QAction("Redo", menu)
        redo_action.setIcon(get_menu_icon("rotate-cw"))
        redo_action.triggered.connect(self.text_input.redo)
        redo_action.setEnabled(self.text_input.isRedoAvailable())
        menu.addAction(redo_action)

        menu.addSeparator()

        cut_action = QAction("Cut", menu)
        cut_action.setIcon(get_menu_icon("scissors"))
        cut_action.triggered.connect(self.text_input.cut)
        cut_action.setEnabled(self.text_input.hasSelectedText())
        menu.addAction(cut_action)

        copy_action = QAction("Copy", menu)
        copy_action.setIcon(get_menu_icon("copy"))
        copy_action.triggered.connect(self.text_input.copy)
        copy_action.setEnabled(self.text_input.hasSelectedText())
        menu.addAction(copy_action)

        paste_action = QAction("Paste", menu)
        paste_action.setIcon(get_menu_icon("clipboard"))  # Using clipboard as paste icon
        paste_action.triggered.connect(self.text_input.paste)
        menu.addAction(paste_action)

        menu.addSeparator()

        select_all_action = QAction("Select All", menu)
        select_all_action.setIcon(get_menu_icon("check-square"))
        select_all_action.triggered.connect(self.text_input.selectAll)
        select_all_action.setEnabled(bool(self.text_input.text()))
        menu.addAction(select_all_action)

        # Show the menu at the cursor position
        global_pos = self.text_input.mapToGlobal(position)
        menu.exec_(global_pos)

    def _insert_original_name(self) -> None:
        """
        Insert the original filename (without extension) at the current cursor position.
        """
        if not self._current_file:
            return

        # Get the original filename without extension
        original_name = os.path.splitext(self._current_file.filename)[0]

        # Insert at current cursor position
        cursor_pos = self.text_input.cursorPosition()
        current_text = self.text_input.text()
        new_text = current_text[:cursor_pos] + original_name + current_text[cursor_pos:]

        self.text_input.setText(new_text)
        # Move cursor to end of inserted text
        self.text_input.setCursorPosition(cursor_pos + len(original_name))

    def validate_input(self, text: str) -> None:
        """Validate and emit signal when text changes with improved styling.

        Args:
            text (str): The text entered by the user.
        """
        # Track if field has ever had content
        if text and not self._has_had_content:
            self._has_had_content = True

        # Determine validation state and apply appropriate styling using properties
        if len(text) >= 240:
            # At character limit - info styling
            self.text_input.setProperty("error", False)
            self.text_input.setProperty("warning", True)
            self.text_input.setProperty("info", True)
        elif not text and self._has_had_content:
            # Empty after having content - warning styling
            self.text_input.setProperty("error", False)
            self.text_input.setProperty("warning", True)
            self.text_input.setProperty("info", False)
        elif not text:
            # Empty initially - no special styling
            self.text_input.setProperty("error", False)
            self.text_input.setProperty("warning", False)
            self.text_input.setProperty("info", False)
        else:
            # Check validation using new system
            is_valid, _ = validate_filename_part(text)
            if not is_valid:
                # Invalid characters - error styling
                self.text_input.setProperty("error", True)
                self.text_input.setProperty("warning", False)
                self.text_input.setProperty("info", False)
            else:
                # Valid - default styling
                self.text_input.setProperty("error", False)
                self.text_input.setProperty("warning", False)
                self.text_input.setProperty("info", False)

        # Force style update
        style = QApplication.instance().style()
        if style:
            style.unpolish(self.text_input)
            style.polish(self.text_input)

        # Always emit the signal (like CounterModule does)
        logger.debug(f"[SpecifiedText] Text changed to: '{text}' (len={len(text)}), emitting signal", extra={"dev_only": True})
        self.updated.emit(self)

    def _on_validation_changed(self, is_valid: bool) -> None:
        """
        Handle validation state changes from the ValidatedLineEdit

        Args:
            is_valid: True if input is valid, False otherwise
        """
        self._is_input_valid = is_valid
        logger.debug(f"[SpecifiedText] Validation state changed: {is_valid}", extra={"dev_only": True})

        # Emit update signal so preview can refresh
        self.updated.emit(self)

    def get_data(self) -> dict:
        """
        Retrieves the current configuration of the specified text module.

        :return: A dictionary containing the type and the user-specified text.
        """

        return {
            "type": "specified_text",
            "text": self.text_input.text()
        }

    def reset(self) -> None:
        self._has_had_content = False  # Reset tracking
        self._is_input_valid = True   # Reset validation state
        self.text_input.clear()
        self.text_input.reset_validation_state()  # Reset ValidatedLineEdit state

    def apply(self, file_item, index=0, metadata_cache=None) -> str:
        return self.apply_from_data(self.get_data(), file_item, index, metadata_cache)

    @staticmethod
    def apply_from_data(data: dict, file_item, index: int = 0, metadata_cache: Optional[dict] = None) -> str:
        logger.debug(f"[SpecifiedTextModule] Called with data={data}, index={index}", extra={"dev_only": True})
        text = data.get("text", "")

        if not text:
            logger.debug("[SpecifiedTextModule] Empty text input, returning empty string.", extra={"dev_only": True})
            return ""

        # Validate using new system
        is_valid, validated_text = validate_filename_part(text)
        if not is_valid:
            logger.warning(f"[SpecifiedTextModule] Invalid filename text: '{text}'")
            from config import INVALID_FILENAME_MARKER
            return INVALID_FILENAME_MARKER

        # Return the text exactly as entered by the user
        return text

    @staticmethod
    def is_effective(data: dict) -> bool:
        return bool(data.get('text', ''))




