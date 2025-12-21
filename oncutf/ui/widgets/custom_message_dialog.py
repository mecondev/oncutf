"""
Module: custom_msgdialog.py

Author: Michael Economou
Date: 2025-05-07

custom_msgdialog.py
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

from oncutf.core.pyqt_imports import (
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    Qt,
    QVBoxLayout,
    QWidget,
)

# Initialize Logger
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class CustomMessageDialog(QDialog):
    """
    A custom-styled message dialog to replace QMessageBox.
    Supports question dialogs and information dialogs.
    """

    def __init__(
        self,
        title: str,
        message: str,
        buttons: list[str] | None = None,
        parent: QWidget | None = None,
        show_progress: bool = False,
        show_checkbox: bool = False,
    ):
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
        show_progress : bool, optional
            Whether to include a progress bar
        show_checkbox : bool, optional
            Whether to show an 'Apply to all' style checkbox

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

        self.progress_bar = None
        if show_progress:
            self.progress_bar = QProgressBar(self)
            self.progress_bar.setRange(0, 0)  # Indeterminate
            # DPI-aware progress bar height (8px at 96 DPI)
            from PyQt5.QtWidgets import QApplication

            dpi_scale = (
                QApplication.instance().devicePixelRatio() if QApplication.instance() else 1.0
            )
            progress_height = max(6, int(8 * dpi_scale))  # Minimum 6px, scaled for DPI
            self.progress_bar.setFixedHeight(progress_height)
            layout.addWidget(self.progress_bar)

        self.label = QLabel(message)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        # Optional checkbox
        self.checkbox = None
        if show_checkbox:
            self.checkbox = QCheckBox("Apply this choice to all remaining conflicts")
            layout.addWidget(self.checkbox)

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

    def showEvent(self, event):
        """Handle show event to ensure proper positioning on multiscreen setups."""
        super().showEvent(event)
        # Ensure dialog appears centered on the same screen as its parent
        from oncutf.utils.multiscreen_helper import position_dialog_relative_to_parent

        position_dialog_relative_to_parent(self)

        # Force normal cursor on the dialog and all its children
        self.setCursor(Qt.ArrowCursor)  # type: ignore[arg-type]

        # Apply normal cursor to all child widgets recursively
        for child in self.findChildren(QWidget):
            child.setCursor(Qt.ArrowCursor)  # type: ignore[arg-type]

        # Process events to ensure cursor change takes effect
        from oncutf.core.pyqt_imports import QApplication

        QApplication.processEvents()

        # Don't clear wait cursor from parent - let it remain on the main window
        # The wait cursor should be visible on the main window but not on the dialog
        # We need to ensure the dialog has normal cursor while parent keeps wait cursor

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

    def is_checkbox_checked(self) -> bool:
        return self.checkbox is not None and self.checkbox.isChecked()

    @staticmethod
    def question(
        parent: QWidget, title: str, message: str, yes_text: str = "Yes", no_text: str = "No"
    ) -> bool:
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

        # Ensure proper positioning on multiscreen setups before showing
        if parent:
            from oncutf.utils.multiscreen_helper import ensure_dialog_on_parent_screen

            ensure_dialog_on_parent_screen(dlg, parent)

        dlg.exec_()
        return dlg.selected == yes_text if dlg.selected else False

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

        # Ensure proper positioning on multiscreen setups before showing
        if parent:
            from oncutf.utils.multiscreen_helper import ensure_dialog_on_parent_screen

            ensure_dialog_on_parent_screen(dlg, parent)

        dlg.exec_()

    @staticmethod
    def unsaved_changes(
        parent: QWidget,
        title: str = "Unsaved Changes",
        message: str = "You have unsaved metadata changes. What would you like to do?",
    ) -> str:
        """
        Displays a dialog for handling unsaved changes with three options.

        Parameters
        ----------
        parent : QWidget
            Parent widget
        title : str, optional
            Dialog title
        message : str, optional
            Dialog message

        Returns
        -------
        str
            One of: 'save_and_close', 'close_without_saving', 'cancel'
        """
        buttons = ["Save & Close", "Close without saving", "Cancel"]
        dlg = CustomMessageDialog(title, message, buttons, parent)

        # Ensure proper positioning on multiscreen setups before showing
        if parent:
            from oncutf.utils.multiscreen_helper import ensure_dialog_on_parent_screen

            ensure_dialog_on_parent_screen(dlg, parent)

        dlg.exec_()

        # Map button text to return values
        button_map = {
            "Save & Close": "save_and_close",
            "Close without saving": "close_without_saving",
            "Cancel": "cancel",
        }

        return button_map.get(dlg.selected, "cancel")

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
        logger.debug("[Dialog] set_progress called with value=%d, total=%s", value, total)
        if not self.progress_bar:
            logger.warning("[Dialog] Progress bar is missing!")
            return

        if total is not None:
            logger.debug("[Dialog] Progress bar range set to 0-%d", total)
            self.progress_bar.setRange(0, total)

        self.progress_bar.setValue(value)
        logger.debug("[Dialog] Progress bar value set to %d", value)

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
            One of: 'overwrite', 'skip', 'skip_all', 'cancel'
        """
        message = f"The file '{filename}' already exists.\nWhat would you like to do?"
        buttons = ["Overwrite", "Skip", "Skip All", "Cancel"]

        dlg = CustomMessageDialog("File Conflict", message, buttons=buttons, parent=parent)

        # Ensure proper positioning on multiscreen setups before showing
        if parent:
            from oncutf.utils.multiscreen_helper import ensure_dialog_on_parent_screen

            ensure_dialog_on_parent_screen(dlg, parent)

        dlg.exec_()

        label_map = {
            "Overwrite": "overwrite",
            "Skip": "skip",
            "Skip All": "skip_all",
            "Cancel": "cancel",
        }

        return label_map.get(dlg.selected, "cancel")  # fallback = cancel

    def set_message(self, msg: str) -> None:
        """
        Updates the dialog's label with the given message.

        Parameters
        ----------
        msg : str
            The new message to display in the dialog.
        """
        logger.debug("Dialog message updated: %s", msg)
        self.label.setText(msg)

    @staticmethod
    def show_waiting(parent: QWidget, message: str = "Please wait...") -> "CustomMessageDialog":
        """
        Shows a modal waiting dialog with a progress bar.

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
        logger.debug("Creating waiting dialog: %s", message)

        dlg = CustomMessageDialog(
            "Please Wait", message, buttons=None, parent=parent, show_progress=True
        )
        # dlg.setModal(True)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        QApplication.processEvents()
        return dlg

    def set_progress_range(self, total: int) -> None:
        """
        Sets the progress bar range to (0, total).
        """
        if self.progress_bar:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(0)

    def keyPressEvent(self, event):
        logger.warning("[CustomMessageDialog] keyPressEvent: %s", event.key())
        if event.key() == Qt.Key_Escape:
            self.set_message("Canceling metadata scan...")
            self.reject()
            QApplication.processEvents()
        else:
            super().keyPressEvent(event)

    @staticmethod
    def choice_with_apply_all(
        parent: QWidget, title: str, message: str, buttons: dict[str, str]
    ) -> tuple[str, bool]:
        """
        Show a custom dialog using CustomMessageDialog with a checkbox.
        Returns (selected_key, apply_to_all)
        """
        dlg = CustomMessageDialog(
            title=title,
            message=message,
            buttons=list(buttons.keys()),
            parent=parent,
            show_checkbox=True,
        )

        # Ensure proper positioning on multiscreen setups before showing
        if parent:
            from oncutf.utils.multiscreen_helper import ensure_dialog_on_parent_screen

            ensure_dialog_on_parent_screen(dlg, parent)

        dlg.exec_()
        selected = dlg.selected or "Cancel"
        apply_to_all = dlg.is_checkbox_checked()
        return buttons.get(selected, "cancel"), apply_to_all

    def closeEvent(self, event):
        """
        Handles window close (X) button by treating it as 'Cancel'.
        """
        self.selected = "Cancel"
        event.accept()

    def reject(self):
        logger.warning("[CustomMessageDialog] reject() CALLED via ESC or close")
        super().reject()
        self.close()
