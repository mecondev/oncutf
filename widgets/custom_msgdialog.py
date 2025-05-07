# custom_msgdialog.py
# Author: Firstname Lastname
# Date: 2025-05-01
# Description: Custom message dialog widget


from PyQt5.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget
from PyQt5.QtCore import Qt

class CustomMessageDialog(QDialog):
    """
    A custom-styled message dialog to replace QMessageBox.
    Supports question dialogs and information dialogs.
    """
    def __init__(self, title: str, message: str, buttons: list[str], parent: QWidget = None):
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

        # Message label
        label = QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._buttons = {}
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




