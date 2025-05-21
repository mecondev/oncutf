"""
Module: checkbox_header.py

Author: Michael Economou
Date: 2025-05-01

This module defines a custom QHeaderView subclass that adds a checkbox
to the first column header of a QTableView. The checkbox allows users
to select or deselect all rows in the table with a single click.

Used in the oncutf UI to streamline batch actions and improve usability
when working with large file lists.

Features:
- Syncs header checkbox state with row checkboxes
- Emits signals when selection state changes
- Visually updates based on user interaction
"""

from typing import Optional
from PyQt5.QtWidgets import QHeaderView, QStyleOptionButton, QStyle
from PyQt5.QtCore import Qt, QRect, QModelIndex
from PyQt5.QtGui import QPainter

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)


class CheckBoxHeader(QHeaderView):
    """
    Custom QHeaderView with a checkbox in the first column header
    to control the check/uncheck state of all file rows.
    """

    def __init__(self, orientation, parent=None, parent_window: Optional[object] = None):
        super().__init__(orientation, parent)
        self.parent_window = parent_window
        self.check_state = Qt.Unchecked  # Initial checkbox state
        self.setSectionsClickable(True)

    def update_state(self, files: list) -> None:
        """
        Update the checkbox state (Checked, Unchecked, PartiallyChecked)
        based on how many files are selected.
        """
        total_files = len(files)

        if total_files == 0:
            self.check_state = Qt.Unchecked
            self.updateSection(0)
            logger.debug("No files — checkbox state reset to Unchecked.")
            return  # do not call generate_preview_names

        checked_count = sum(1 for file in files if file.checked is True or file.checked == Qt.Checked)

        logger.info(f"Checked count: {checked_count} out of {total_files} files.")

        if checked_count == total_files:
            self.check_state = Qt.Checked
        elif checked_count == 0:
            self.check_state = Qt.Unchecked
        else:
            self.check_state = Qt.PartiallyChecked

        self.updateSection(0)

        # only trigger preview when files exist
        if self.parent_window:
            self.parent_window.generate_preview_names()

    def mousePressEvent(self, event) -> None:
        """
        Detect click on header and toggle all row checkboxes.
        """
        index = self.logicalIndexAt(event.pos())
        if index == 0:
            self.toggle_check_state()
            self.updateSection(0)  # Force checkbox repaint
            if self.parent_window:
                self.parent_window.handle_header_toggle(self.check_state)
        else:
            super().mousePressEvent(event)

    def toggle_check_state(self) -> None:
        """
        Toggle the internal checkbox state and apply it to all files in the model.
        """
        if not self.parent_window:
            return

        model = self.parent_window.model

        if self.check_state == Qt.Checked:
            new_state = False
            self.check_state = Qt.Unchecked
        else:
            new_state = True
            self.check_state = Qt.Checked

        # Ensure state changes only once
        if all(file.checked == new_state for file in model.files):
            return  # Skip if no change in check state

        # Update each file's checked state
        for file in model.files:
            file.checked = new_state

        # Refresh header and preview
        self.update_state(model.files)
        model.layoutChanged.emit()

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole) -> bool:
        """
        Called when the user interacts with a checkbox (column 0).
        Updates the 'checked' state and triggers UI updates.
        """
        if not index.isValid():
            logger.info("setData Fired but no index")
            return False
        logger.info("setData Fired!")
        row = index.row()
        col = index.column()
        file = self.parent_window.model.files[row]

        if role == Qt.CheckStateRole and col == 0:
            file.checked = (value == Qt.Checked)
            logger.info(f"File at row {row} marked as {'checked' if file.checked else 'unchecked'}.")

            self.parent_window.model.dataChanged.emit(index, index, [Qt.CheckStateRole])

            # Trigger preview & header checkbox state update
            if self.parent_window:
                self.parent_window.header.update_state(self.parent_window.model.files)
                self.parent_window.update_files_label()
                self.parent_window.generate_preview_names()

            return True

        return False
