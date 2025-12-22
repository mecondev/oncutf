"""
Module: datetime_edit_dialog.py

Author: Michael Economou
Date: 2025-12-03

Dialog for editing file creation and modification dates.
Supports single or multiple file selection with calendar picker.
"""

from pathlib import Path

from oncutf.config import QLABEL_MUTED_TEXT
from oncutf.core.pyqt_imports import (
    QCheckBox,
    QDateTime,
    QDateTimeEdit,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    Qt,
    QVBoxLayout,
    QWidget,
)
from oncutf.core.theme_manager import get_theme_manager
from oncutf.utils.logger_factory import get_cached_logger
from oncutf.utils.tooltip_helper import TooltipHelper, TooltipType

logger = get_cached_logger(__name__)


class DateTimeEditDialog(QDialog):
    """Dialog for editing creation and modification dates of selected files."""

    def __init__(self, parent=None, selected_files=None, date_type="modified"):
        """
        Initialize the DateTime edit dialog.

        Args:
            parent: Parent widget
            selected_files: List of file paths (str or Path)
            date_type: "modified" or "created" - which date to edit
        """
        super().__init__(parent)
        self.selected_files = [Path(f) for f in (selected_files or [])]
        self.date_type = date_type
        self.checkboxes = {}
        self.result_files = None

        title = "Edit Creation Date" if date_type == "created" else "Edit Modification Date"
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setModal(True)
        self.setMinimumSize(500, 400)

        theme = get_theme_manager()
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {theme.get_color('dialog_background')};
                color: {theme.get_color('text')};
                font-size: 9pt; font-family: "Inter", "Segoe UI", Arial, sans-serif; font-weight: 500;
            }}
            QLabel {{
                background-color: transparent;
                color: {theme.get_color('text')};
                font-size: 9pt; font-family: "Inter", "Segoe UI", Arial, sans-serif; font-weight: 500;
                border: none;
                padding: 2px;
            }}
            QCheckBox {{
                color: {theme.get_color('text')};
                font-size: 9pt; font-family: "Inter", "Segoe UI", Arial, sans-serif; font-weight: 500;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {theme.get_color('border')};
                border-radius: 3px;
                background-color: {theme.get_color('input_bg')};
            }}
            QCheckBox::indicator:checked {{
                background-color: {theme.get_color('selected')};
                border-color: {theme.get_color('selected')};
            }}
            QDateTimeEdit {{
                background-color: {theme.get_color('input_bg')};
                color: {theme.get_color('text')};
                border: 1px solid {theme.get_color('border')};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10pt;
                min-height: 24px;
            }}
            QDateTimeEdit:hover {{
                border-color: {theme.get_color('border_hover')};
            }}
            QDateTimeEdit:focus {{
                border-color: {theme.get_color('selected')};
            }}
            QDateTimeEdit::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid {theme.get_color('border')};
            }}
            QCalendarWidget {{
                background-color: {theme.get_color('dialog_background')};
                color: {theme.get_color('text')};
            }}
            QCalendarWidget QTableView {{
                background-color: {theme.get_color('table_background')};
                alternate-background-color: {theme.get_color('table_alternate')};
                selection-background-color: {theme.get_color('selected')};
            }}
            QScrollArea {{
                background-color: {theme.get_color('background')};
                border: 1px solid {theme.get_color('border')};
                border-radius: 4px;
            }}
            QScrollArea QWidget {{
                background-color: transparent;
            }}
        """
        )

        self._setup_ui()

    def _setup_ui(self):
        """Setup the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Title and info
        title_text = f"Edit {self.date_type.title()} Date"
        title_label = QLabel(title_text)
        title_label.setStyleSheet("font-size: 12pt; font-weight: 600; margin-bottom: 4px;")
        layout.addWidget(title_label)

        info_text = f"Select files and set new {self.date_type} date/time:"
        info_label = QLabel(info_text)
        self._apply_info_label_style(info_label, QLABEL_MUTED_TEXT)
        layout.addWidget(info_label)

        # DateTime picker
        picker_layout = QHBoxLayout()
        picker_label = QLabel("New Date/Time:")
        picker_layout.addWidget(picker_label)

        self.datetime_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        picker_layout.addWidget(self.datetime_edit, 1)

        layout.addLayout(picker_layout)

        # File selection area
        files_label = QLabel(f"Select files to modify ({len(self.selected_files)} total):")
        files_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
        layout.addWidget(files_label)

        # Scrollable file list with checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(6)

        # Add checkbox for each file
        for file_path in self.selected_files:
            checkbox = QCheckBox(file_path.name)
            checkbox.setChecked(True)
            TooltipHelper.setup_tooltip(checkbox, str(file_path), TooltipType.INFO)
            self.checkboxes[str(file_path)] = checkbox
            self.content_layout.addWidget(checkbox)

        self.content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # Select/Deselect all buttons
        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self._deselect_all)
        select_layout.addWidget(select_all_btn)
        select_layout.addWidget(deselect_all_btn)
        select_layout.addStretch()
        layout.addLayout(select_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setDefault(False)
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.setFocus()
        self.cancel_button.clicked.connect(self.reject)

        theme = get_theme_manager()
        self.cancel_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {theme.get_color('button_bg')};
                color: {theme.get_color('text')};
                font-size: 9pt; font-family: "Inter", "Segoe UI", Arial, sans-serif; font-weight: 500;
                border: none;
                border-radius: 8px;
                padding: 4px 12px 4px 8px;
                min-width: 70px;
            }}
            QPushButton:hover {{
                background-color: {theme.get_color('selected')};
            }}
            QPushButton:pressed {{
                background-color: {theme.get_color('pressed')};
            }}
        """
        )

        # Apply button
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.accept)

        theme = get_theme_manager()
        self.apply_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {theme.get_color('button_bg')};
                color: {theme.get_color('text')};
                font-size: 9pt; font-family: "Inter", "Segoe UI", Arial, sans-serif; font-weight: 500;
                border: none;
                border-radius: 8px;
                padding: 4px 12px 4px 8px;
                min-width: 70px;
            }}
            QPushButton:hover {{
                background-color: {theme.get_color('button_hover_bg')};
            }}
            QPushButton:pressed {{
                background-color: {theme.get_color('pressed')};
            }}
        """
        )

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.apply_button)
        layout.addLayout(button_layout)

    def _apply_info_label_style(self, label: QLabel, color: str, opacity: str = "1.0"):
        """Apply consistent font styling to info label."""
        label.setStyleSheet(
            f"color: {color}; opacity: {opacity}; "
            f"font-size: 9pt; font-weight: 400;"
        )

    def _select_all(self):
        """Select all checkboxes."""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)

    def _deselect_all(self):
        """Deselect all checkboxes."""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)

    def get_selected_files(self):
        """Get list of files that are checked."""
        return [
            Path(file_path)
            for file_path, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        ]

    def get_new_datetime(self):
        """Get the selected datetime as a Python datetime object."""
        qdt = self.datetime_edit.dateTime()
        return qdt.toPyDateTime()

    def accept(self):
        """Handle Apply button - validate and store result."""
        selected = self.get_selected_files()
        if not selected:
            logger.warning("[DateTimeEditDialog] No files selected")
            return

        self.result_files = selected
        logger.info(
            "[DateTimeEditDialog] User selected %d files for %s date change to %s",
            len(selected),
            self.date_type,
            self.get_new_datetime(),
        )
        super().accept()

    @classmethod
    def get_datetime_edit_choice(
        cls,
        parent,
        selected_files,
        date_type="modified"
    ):
        """
        Factory method to show dialog and return selected files + datetime.

        Args:
            parent: Parent widget
            selected_files: List of file paths
            date_type: "modified" or "created"

        Returns:
            Tuple of (selected_files, new_datetime) or (None, None) if cancelled
        """
        dialog = cls(parent, selected_files, date_type)
        result = dialog.exec_()

        if result == QDialog.Accepted and dialog.result_files:
            return dialog.result_files, dialog.get_new_datetime()

        return None, None
