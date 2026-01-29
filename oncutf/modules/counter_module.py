"""Module: counter_module.py.

Author: Michael Economou
Date: 2025-05-06

This module defines a rename module that inserts an incrementing counter
into filenames. It is used within the oncutf application to generate
sequential file names based on configurable start value, step, and padding.
"""

from typing import Any

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from oncutf.config import ICON_SIZES
from oncutf.models.counter_scope import CounterScope
from oncutf.modules.base_module import BaseRenameModule
from oncutf.ui.helpers.icons_loader import get_menu_icon
from oncutf.ui.helpers.tooltip_helper import TooltipHelper, TooltipType
from oncutf.ui.theme_manager import get_theme_manager
from oncutf.ui.widgets.styled_combo_box import StyledComboBox

# initialize logger
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class CounterModule(BaseRenameModule):
    """A widget for inserting an incrementing counter in filenames.
    Displays each row as: [Label (fixed width, right-aligned)] [input field] [btn_minus] [btn_plus].
    """

    # Phase 3.1: Module metadata for auto-discovery
    DISPLAY_NAME = "Counter"
    UI_ROWS = 3
    DESCRIPTION = "Sequential numbering with custom start, step, and padding"
    CATEGORY = "Numbering"

    updated = pyqtSignal(object)

    LABEL_WIDTH = 110  # pixels - increased by 10px for better text fit

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize counter module with start number, padding, increment, and scope controls.

        Args:
            parent: Optional parent widget

        """
        super().__init__(parent)
        self.setProperty("module", True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        # Row 1: Start Number
        self.start_input, row1 = self._create_row("Start Number", initial_value=1, min_val=0)
        layout.addLayout(row1)

        # Row 2: Number of Digits
        self.padding_input, row2 = self._create_row("Number of Digits", initial_value=4, min_val=1)
        layout.addLayout(row2)

        # Row 3: Increment By
        self.increment_input, row3 = self._create_row("Increment By", initial_value=1, min_val=1)
        layout.addLayout(row3)

        # Row 4: Counter Scope (NEW)
        scope_row = self._create_scope_row()
        layout.addLayout(scope_row)

        # Connect inputs to update signal (debounced)
        self.start_input.textChanged.connect(self._on_value_change)
        self.padding_input.textChanged.connect(self._on_value_change)
        self.increment_input.textChanged.connect(self._on_value_change)
        self.scope_combo.currentIndexChanged.connect(self._on_value_change)

        # Initialize _last_value to prevent duplicate signals
        self._last_value = str(self.get_data())

    def _on_value_change(self) -> None:
        """Triggered when any of the spinboxes change.
        Emits update only if data has truly changed.
        """
        self.emit_if_changed(str(self.get_data()))

    def _create_row(
        self, label_text: str, initial_value: int = 1, min_val: int = 0, max_val: int = 999999
    ) -> tuple[QLineEdit, QHBoxLayout]:
        """Create a row layout with:
        [QLabel(label_text)] [QLineEdit] [btn_minus] [btn_plus]
        Returns the input field and the layout.
        """
        # Label with fixed width and right alignment
        label = QLabel(label_text)
        label.setFixedWidth(self.LABEL_WIDTH)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Input field with integer validator
        input_field = QLineEdit(str(initial_value))
        input_field.setFixedWidth(60)
        input_field.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # Right align for numbers
        validator = QIntValidator(min_val, max_val, self)
        input_field.setValidator(validator)

        # Buttons with icons
        theme = get_theme_manager()
        button_size = theme.get_constant("button_height")

        btn_minus = QPushButton()
        btn_plus = QPushButton()
        btn_minus.setIcon(get_menu_icon("minus"))
        btn_plus.setIcon(get_menu_icon("plus"))
        btn_minus.setFixedSize(button_size, button_size)
        btn_plus.setFixedSize(button_size, button_size)
        btn_minus.setIconSize(
            QSize(ICON_SIZES["SMALL"], ICON_SIZES["SMALL"])
        )  # Small icons for buttons
        btn_plus.setIconSize(
            QSize(ICON_SIZES["SMALL"], ICON_SIZES["SMALL"])
        )  # Small icons for buttons

        # Setup custom tooltips for plus/minus buttons
        TooltipHelper.setup_tooltip(btn_minus, "Decrease value", TooltipType.INFO)
        TooltipHelper.setup_tooltip(btn_plus, "Increase value", TooltipType.INFO)

        # Adjust helper
        def adjust(delta: int) -> None:
            """Adjusts the value in the input field by the specified delta,
            ensuring it remains within the specified minimum and maximum bounds.

            Emits the 'updated' signal after updating the value.

            :param delta: The amount to adjust the current value by.
            """
            try:
                val = int(input_field.text())
            except ValueError:
                val = min_val
            val = max(min_val, min(val + delta, max_val))
            input_field.setText(str(val))
            self.updated.emit(self)

        # Connect signals
        btn_minus.clicked.connect(lambda: adjust(-1))
        btn_plus.clicked.connect(lambda: adjust(1))
        input_field.textChanged.connect(lambda _: self.updated.emit(self))

        # Build row layout
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(2, 2, 2, 2)
        row_layout.setSpacing(6)
        row_layout.addWidget(label, 0, Qt.AlignVCenter)
        row_layout.addWidget(input_field, 0, Qt.AlignVCenter)
        row_layout.addSpacing(4)  # Extra space before buttons
        row_layout.addWidget(btn_minus, 0, Qt.AlignVCenter)
        row_layout.addWidget(btn_plus, 0, Qt.AlignVCenter)
        row_layout.addStretch()

        return input_field, row_layout

    def _create_scope_row(self) -> QHBoxLayout:
        """Create a row for counter scope selection.
        Returns the layout containing label and combobox.
        """
        # Label with fixed width and right alignment
        label = QLabel("Counter Scope")
        label.setFixedWidth(self.LABEL_WIDTH)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # ComboBox for scope selection
        self.scope_combo = StyledComboBox()

        # Add scope options
        for scope in CounterScope:
            self.scope_combo.addItem(scope.display_name, scope.value)

        # Set default to PER_FOLDER (fixes multi-folder issue)
        self.scope_combo.setCurrentIndex(1)  # PER_FOLDER is index 1

        # Setup tooltip
        TooltipHelper.setup_tooltip(
            self.scope_combo,
            "Control when the counter resets:\n"
            "• Global: Single counter across all files\n"
            "• Per Folder: Reset at folder boundaries\n"
            "• Per Extension: Reset for each file type\n"
            "• Per File Group: Reset for each group (future)",
            TooltipType.INFO,
        )

        # Build row layout
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(2, 2, 2, 2)
        row_layout.setSpacing(6)
        row_layout.addWidget(label, 0, Qt.AlignVCenter)
        row_layout.addWidget(self.scope_combo, 0, Qt.AlignVCenter)
        row_layout.addStretch()

        return row_layout

    def get_data(self) -> dict[str, Any]:
        """Returns the current configuration of the counter module.

        :return: dict with counter info including scope
        """
        return {
            "type": "counter",
            "start": int(self.start_input.text() or "0"),
            "padding": int(self.padding_input.text() or "0"),
            "step": int(self.increment_input.text() or "0"),
            "scope": self.scope_combo.currentData() or CounterScope.PER_FOLDER.value,
        }

    def apply(self, file_item: Any, index: int = 0, metadata_cache: Any = None) -> str:
        """Apply counter module using current widget configuration.

        Args:
            file_item: FileItem being renamed
            index: Index in the file list
            metadata_cache: Optional metadata cache

        Returns:
            Formatted counter string (zero-padded)

        """
        return self.apply_from_data(self.get_data(), file_item, index, metadata_cache)

    @staticmethod
    def apply_from_data(
        data: dict[str, Any],
        _file_item: Any,
        index: int = 0,
        _metadata_cache: dict[str, Any] | None = None,
    ) -> str:
        """Applies counter-based formatting using the given config and index.

        Parameters
        ----------
        data : dict
            Configuration dictionary with keys:
                - 'type': 'counter'
                - 'start': int, the starting number
                - 'padding': int, number of digits (e.g. 4 -> 0001)
                - 'step': int, increment step
                - 'scope': str, counter scope ('global', 'per_folder', 'per_selection')
        file_item : FileItem
            The file to rename (not used by counter).
        index : int, optional
            The position of the file in the list (used for offsetting).
            NOTE: For PER_FOLDER scope, this should be the index within the folder group,
                  not the global index. The preview engine is responsible for providing
                  the correct index based on the scope.
        metadata_cache : dict, optional
            Not used in this module but accepted for API compatibility.

        Returns
        -------
        str
            The stringified counter value with proper padding.

        """
        try:
            start = int(data.get("start", 1))
            step = int(data.get("step", 1))
            padding = int(data.get("padding", 4))
            scope = data.get("scope", CounterScope.PER_FOLDER.value)

            value = start + index * step
            result = f"{value:0{padding}d}"
            logger.debug(
                "[CounterModule] index: %d, value: %d, padded: %s, scope: %s",
                index,
                value,
                result,
                scope,
                extra={"dev_only": True},
            )
            return result
        except Exception as e:
            logger.exception("[CounterModule] Failed to apply counter logic: %s", e)
            return "####"

    @staticmethod
    def is_effective_data(_data: dict[str, Any]) -> bool:
        """Check if counter module data is effective (always True).

        Counter module is always active regardless of configuration.

        Args:
            _data: Module configuration dictionary (unused)

        Returns:
            Always True

        """
        return True
