"""
Module: original_name_widget.py

Rename module that reuses original filename with optional Greek-to-Greeklish conversion.

Author: Michael Economou
Date: 2025-06-04
"""

from PyQt5.QtWidgets import QVBoxLayout, QLabel, QCheckBox, QHBoxLayout
from PyQt5.QtCore import Qt
from modules.base_module import BaseRenameModule  # NEW
from utils.logger_helper import get_logger

logger = get_logger(__name__)


class OriginalNameWidget(BaseRenameModule):
    """
    Rename module widget for reusing the original filename.

    Provides a checkbox for optional Greek-to-Greeklish conversion.
    Emits signal only when state actually changes.
    """

    LABEL_WIDTH = 120
    DROPDOWN_WIDTH = 128

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("module", True)
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self.checkbox = QCheckBox("Convert Greek to Greeklish")
        self.checkbox.toggled.connect(self._on_checkbox_toggled)

        row.addWidget(self.checkbox)
        row.addStretch()
        layout.addLayout(row)
        layout.addStretch()

    def _on_checkbox_toggled(self, checked: bool) -> None:
        """
        Emits signal only if state has changed from last known.
        """
        data_str = str(self.get_data())
        logger.debug(f"[OriginalNameWidget] Toggled checkbox → {data_str}")
        self.emit_if_changed(data_str)

    def get_data(self) -> dict:
        return {
            "type": "original_name",
            "greeklish": self.checkbox.isChecked()
        }

    def set_data(self, data: dict) -> None:
        self.checkbox.setChecked(data.get("greeklish", False))
        self._last_value = str(self.get_data())  # update debounce state
