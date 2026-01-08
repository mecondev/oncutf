"""Module: name_transform_widget.py

Author: Michael Economou
Date: 2025-05-27

name_transform_widget.py
UI widget for configuring NameTransformModule.
Provides options for Greek to Greeklish conversion, case and separator transformation.
Uses BaseRenameModule to prevent duplicate emits.
"""

from oncutf.core.pyqt_imports import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    Qt,
    QVBoxLayout,
    QWidget,
)
from oncutf.modules.base_module import BaseRenameModule  # Debounced signal base
from oncutf.ui.widgets.styled_combo_box import StyledComboBox


class NameTransformWidget(BaseRenameModule):
    """UI component for selecting Greek to Greeklish conversion, case and separator transformations.
    Emits 'updated' signal only when the configuration changes.
    """

    LABEL_WIDTH = 70  # Reduce label width to bring controls more to the left

    def __init__(self, parent: QWidget | None = None):
        """Initialize the name transform widget with Greeklish, case, and separator controls."""
        super().__init__(parent)
        self.setObjectName("NameTransformWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)  # Control spacing manually like metadata dialog

        # --- Greek to Greeklish conversion ---
        greeklish_layout = QHBoxLayout()
        greeklish_layout.setContentsMargins(0, 0, 0, 0)
        greeklish_layout.setSpacing(8)

        greeklish_label = QLabel("Greeklish:")
        greeklish_label.setFixedWidth(self.LABEL_WIDTH)
        greeklish_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.greeklish_checkbox = QCheckBox("Convert Greek to Greeklish")
        self.greeklish_checkbox.toggled.connect(self._on_value_change)

        greeklish_layout.addWidget(greeklish_label)
        greeklish_layout.addWidget(self.greeklish_checkbox)
        greeklish_layout.addStretch()
        layout.addLayout(greeklish_layout)

        # Space between greeklish and case
        layout.addSpacing(3)

        # --- Case transformation ---
        case_layout = QHBoxLayout()
        case_layout.setContentsMargins(0, 0, 0, 0)
        case_layout.setSpacing(8)

        case_label = QLabel("Case:")
        case_label.setFixedWidth(self.LABEL_WIDTH)
        case_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.case_combo = StyledComboBox()
        self.case_combo.addItems(["original", "lower", "UPPER", "Capitalize"])
        self.case_combo.setFixedWidth(200)  # Make combobox larger (~2.5 characters more)
        # Theme styling is handled by StyledComboBox
        self.case_combo.currentIndexChanged.connect(self._on_value_change)

        case_layout.addWidget(case_label)
        case_layout.addWidget(self.case_combo)
        case_layout.addStretch()
        layout.addLayout(case_layout)

        # Space between case and separator
        layout.addSpacing(3)

        # --- Separator transformation ---
        sep_layout = QHBoxLayout()
        sep_layout.setContentsMargins(0, 0, 0, 0)
        sep_layout.setSpacing(8)

        sep_label = QLabel("Separator:")
        sep_label.setFixedWidth(self.LABEL_WIDTH)
        sep_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # type: ignore
        self.sep_combo = StyledComboBox()
        self.sep_combo.addItems(["as-is", "snake_case", "kebab-case", "space"])
        self.sep_combo.setFixedWidth(200)  # Make combobox larger (~2.5 characters more)
        # Theme styling is handled by StyledComboBox
        self.sep_combo.currentIndexChanged.connect(self._on_value_change)

        sep_layout.addWidget(sep_label)
        sep_layout.addWidget(self.sep_combo)
        sep_layout.addStretch()
        layout.addLayout(sep_layout)

    def _on_value_change(self) -> None:
        """Triggered when any control changes.
        Emits update only if the new configuration differs from the last.
        """
        current_data = str(self.get_data())
        self.emit_if_changed(current_data)

    def get_data(self) -> dict:
        """Returns the current name transformation configuration.
        """
        return {
            "greeklish": self.greeklish_checkbox.isChecked(),
            "case": self.case_combo.currentText(),
            "separator": self.sep_combo.currentText(),
        }

    def set_data(self, data: dict) -> None:
        """Sets the current state of the controls from saved configuration.

        Args:
            data (dict): Should include keys 'greeklish', 'case' and 'separator'.

        """
        self.greeklish_checkbox.setChecked(data.get("greeklish", False))
        self.case_combo.setCurrentText(data.get("case", "original"))
        self.sep_combo.setCurrentText(data.get("separator", "as-is"))
        self._last_value = str(self.get_data())  # Update internal cache
