"""
name_transform_widget.py

UI widget for configuring NameTransformModule.
Provides dropdowns for case and separator transformation options.

Uses BaseRenameModule to prevent duplicate emits.

Author: Michael Economou
Date: 2025-06-04
"""

from typing import Optional

from core.qt_imports import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from modules.base_module import BaseRenameModule  # Debounced signal base


class NameTransformWidget(BaseRenameModule):
    """
    UI component for selecting case and separator transformations.
    Emits 'updated' signal only when the configuration changes.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("NameTransformWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # --- Case transformation ---
        case_layout = QHBoxLayout()
        case_label = QLabel("Case:")
        self.case_combo = QComboBox()
        self.case_combo.addItems(["original", "lower", "UPPER", "Capitalize"])
        self.case_combo.currentIndexChanged.connect(self._on_value_change)

        case_layout.addWidget(case_label)
        case_layout.addWidget(self.case_combo)
        layout.addLayout(case_layout)

        # --- Separator transformation ---
        sep_layout = QHBoxLayout()
        sep_label = QLabel("Separator:")
        self.sep_combo = QComboBox()
        self.sep_combo.addItems(["as-is", "snake_case", "kebab-case", "space"])
        self.sep_combo.currentIndexChanged.connect(self._on_value_change)

        sep_layout.addWidget(sep_label)
        sep_layout.addWidget(self.sep_combo)
        layout.addLayout(sep_layout)

    def _on_value_change(self) -> None:
        """
        Triggered when either combo box changes.
        Emits update only if the new configuration differs from the last.
        """
        current_data = str(self.get_data())
        self.emit_if_changed(current_data)

    def get_data(self) -> dict:
        """
        Returns the current name transformation configuration.
        """
        return {
            "case": self.case_combo.currentText(),
            "separator": self.sep_combo.currentText(),
        }

    def set_data(self, data: dict) -> None:
        """
        Sets the current state of the combo boxes from saved configuration.

        Args:
            data (dict): Should include keys 'case' and 'separator'.
        """
        self.case_combo.setCurrentText(data.get("case", "original"))
        self.sep_combo.setCurrentText(data.get("separator", "as-is"))
        self._last_value = str(self.get_data())  # Update internal cache
