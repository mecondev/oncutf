"""
custom_msgdialog.py

Author: Michael Economou
Date: 2025-05-01

This module defines the CustomMessageDialog class, a flexible and styled alternative
to QMessageBox for use in the oncutf application.

It provides support for various types of dialogs including:
- Question dialogs with custom button labels
- Informational dialogs with an OK button
- Non-blocking waiting dialogs with optional progress bar
- Conflict resolution dialogs for rename operations (e.g., Skip, Overwrite)

This dialog is intended for consistent and modern user feedback across the application,
and is used instead of standard QMessageBox to allow greater control over layout,
behavior, and styling.
"""

from typing import Optional
from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget,
    QProgressBar, QApplication
)


from PyQt5.QtCore import Qt

# Initialize Logger
from logger_helper import get_logger
logger = get_logger(__name__)


class CustomMessageDialog(QDialog):
    """
    A custom-styled message dialog to replace QMessageBox.
    Supports question dialogs and information dialogs.
    """

    def __init__(self, title: str, message: str, buttons: Optional[list[str]] = None,
                parent: Optional[QWidget] = None, show_progress: bool = False):
        """
        Initialize a CustomMessageDialog.

        Parameters
        ----------
        title : str
            Dialog title
        message : str
            Dialog message
        buttons : list[str]
            List of button texts
        parent : QWidget, optional
            Parent widget

        Notes
        -----
        The dialog is modal and removes the window help button.
        Button text is used as the key to access the corresponding button
        in the instance's _buttons dictionary.
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Progress bar
        self.progress_bar = None
        if show_progress:
            self.progress_bar = QProgressBar(self)
            self.progress_bar.setRange(0, 0)  # Indeterminate
            layout.addWidget(self.progress_bar)
        else:
            self.progress_bar = None

        # Message label
        self.label = QLabel(message)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._buttons = {}
        if buttons:
            for btn_text in buttons:
                btn = QPushButton(btn_text)
                btn.setFixedWidth(100)
                btn.clicked.connect(lambda _, b=btn_text: self._on_button(b))
                btn_layout.addWidget(btn)
                self._buttons[btn_text] = btn

        layout.addLayout(btn_layout)

        self.selected = None

    def _on_button(self, btn_text: str):
        """
        Handles button click events, setting the selected button text
        and closing the dialog with acceptance.

        Parameters
        ----------
        btn_text : str
            The text of the button that was clicked.
        """

        self.selected = btn_text
        self.accept()

    @staticmethod
    def question(parent: QWidget, title: str, message: str,
                 yes_text: str = "Yes", no_text: str = "No") -> bool:
        """
        Displays a question dialog, returning True if the "Yes" button was
        clicked and False if the "No" button was clicked.

        Parameters
        ----------
        parent : QWidget
            Parent widget
        title : str
            Dialog title
        message : str
            Dialog message
        yes_text : str, optional
            Text of the "Yes" button
        no_text : str, optional
            Text of the "No" button

        Returns
        -------
        bool
            True if the "Yes" button was clicked, False if the "No" button was clicked.
        """
        dlg = CustomMessageDialog(title, message, [yes_text, no_text], parent)
        dlg.exec_()
        return dlg.selected == yes_text

    @staticmethod
    def information(parent: QWidget, title: str, message: str, ok_text: str = "OK") -> None:
        """
        Displays an information dialog with the given title, message, and
        "OK" button. The dialog is modal and removes the window help button.

        Parameters
        ----------
        parent : QWidget
            Parent widget
        title : str
            Dialog title
        message : str
            Dialog message
        ok_text : str, optional
            Text of the "OK" button

        Returns
        -------
        None
        """
        dlg = CustomMessageDialog(title, message, [ok_text], parent)
        dlg.exec_()

    @staticmethod
    def rename_conflict_dialog(parent: QWidget, filename: str) -> str:
        """
        Shows a dialog with options for renaming conflict resolution.

        Parameters
        ----------
        parent : QWidget
            The parent widget.
        filename : str
            The filename that is causing the conflict.

        Returns
        -------
        str
            One of "Skip", "Skip All", "Cancel", "Overwrite"
        """
        message = f"The file '{filename}' already exists.\nWhat would you like to do?"
        options = ["Skip", "Skip All", "Cancel", "Overwrite"]
        dlg = CustomMessageDialog("File Conflict", message, buttons=options, parent=parent)
        dlg.exec_()
        return dlg.selected

    def set_progress(self, value: int, total: int = None):
        """
        Updates the progress bar with the current progress value.

        Parameters
        ----------
        value : int
            The current progress value to set on the progress bar.
        total : int, optional
            The total value for the progress bar range. If provided,
            updates the progress bar range to (0, total).
        """

        if self.progress_bar:
            if total is not None:
                self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(value)

    def set_message(self, msg: str) -> None:
        """
        Updates the dialog's label with the given message.

        Parameters
        ----------
        msg : str
            The new message to display in the dialog.
        """
        self.label.setText(msg)

    @staticmethod
    def show_waiting(parent: QWidget, message: str = "Please wait...") -> "CustomMessageDialog":
        """
        Shows a non-modal waiting dialog with a progress bar.

        Parameters
        ----------
        parent : QWidget
            The parent widget.
        message : str, optional
            The message to display in the dialog.

        Returns
        -------
        CustomMessageDialog
            The waiting dialog.
        """
        logger.debug("CustomMessageDialog.show_waiting: creating dialog")

        dlg = CustomMessageDialog("Please Wait", message, buttons=None, parent=parent, show_progress=True)
        dlg.setModal(False)
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.show()
        return dlg

    def set_progress_range(self, total: int) -> None:
        """
        Sets the progress bar range to (0, total).
        """
        if self.progress_bar:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(0)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.set_message("Canceling metadata scan...")
            self.accept()  # or just close()
            QApplication.processEvents()
        else:
            super().keyPressEvent(event)

