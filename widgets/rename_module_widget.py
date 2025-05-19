"""
Module: rename_module_widget.py

Author: Michael Economou
Date: 2025-05-01

This module defines a custom widget for managing rename modules within
the oncutf application. It allows users to add, configure, remove, and
reorder individual rename modules that collectively define the batch
renaming logic.

The widget provides a visual, modular interface for customizing the
renaming workflow interactively.

Features:
- Dynamic UI creation for each module type
- Dropdown-based module type selection
- Add/Remove buttons and layout management
"""

from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFrame
)
from PyQt5.QtCore import pyqtSignal, QTimer

from modules.specified_text_module import SpecifiedTextModule
from modules.counter_module import CounterModule
from modules.metadata_module import MetadataModule
from widgets.original_name_widget import OriginalNameWidget

from widgets.custom_msgdialog import CustomMessageDialog

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)

class RenameModuleWidget(QWidget):
    """
    A wrapper widget that hosts a dynamically loaded rename module,
    with a combo box for selecting module type and add/remove buttons.
    """
    remove_requested = pyqtSignal(QWidget)
    updated = pyqtSignal(QWidget)

    def __init__(self, parent: QWidget = None, parent_window: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.parent_window = parent_window  # MainWindow
        self.setObjectName("RenameModuleWidget")
        self.setProperty("module", True)
        self.style().unpolish(self)
        self.style().polish(self)

        self.module_instances = {
            "Specified Text": SpecifiedTextModule,
            "Counter": CounterModule,
            "Metadata": MetadataModule,
            "Original Name": OriginalNameWidget
        }

        self.module_heights = {
            "Specified Text": 90,
            "Counter": 130,
            "Metadata": 100,
            "Original Name": 120
        }

        self.current_module_widget = None

        # --- Layout setup ---
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(0)

        # Optional divider
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.HLine)
        self.divider.setFixedHeight(2)
        self.divider.setStyleSheet("background-color: #aaa; border: none; margin: 4px 0px;")
        self.divider.setVisible(False)
        self.main_layout.addWidget(self.divider)

        # Row for "Type" label and combo box
        type_row = QHBoxLayout()
        type_label = QLabel("Type:")
        self.type_combo = QComboBox()
        self.type_combo.addItems(self.module_instances.keys())
        self.type_combo.setMaximumWidth(140)
        self.type_combo.setFixedHeight(24)
        self.type_combo.currentTextChanged.connect(self.update_module_content)

        type_row.addWidget(type_label)
        type_row.addWidget(self.type_combo)
        type_row.addStretch()
        self.main_layout.addLayout(type_row)

        # Fixed height container layout for modules
        self.content_container_widget = QWidget()
        self.content_container_layout = QVBoxLayout(self.content_container_widget)
        self.content_container_layout.setContentsMargins(4, 4, 4, 4)
        self.content_container_layout.setSpacing(2)
        self.main_layout.addWidget(self.content_container_widget)

        # Add/remove buttons
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("+")
        self.add_button.setFixedSize(24, 24)
        self.remove_button = QPushButton("-")
        self.remove_button.setFixedSize(24, 24)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))
        button_layout.addStretch()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        self.main_layout.addLayout(button_layout)

        # Load default module
        QTimer.singleShot(0, lambda: self.update_module_content(self.type_combo.currentText()))

    def connect_signals_for_module(self, module_widget: QWidget) -> None:
        if self.parent_window and hasattr(module_widget, "updated"):
            try:
                self.updated.connect(self.parent_window.generate_preview_names)
                module_widget.updated.connect(self.updated.emit)
                logger.info("[RenameModuleWidget] Connected updated -> generate_preview_names (with module ref)")

            except Exception as e:
                logger.warning(f"[RenameModuleWidget] Signal connection failed: {e}")

        else:
            logger.warning("[RenameModuleWidget] Could not connect signal. parent_window: %s, has updated: %s",
                        self.parent_window, hasattr(module_widget, "updated"))

    def update_module_content(self, module_name: str) -> None:
        """
        Replace module widget and adjust height constraint.
        """
        if self.current_module_widget:
            self.content_container_layout.removeWidget(self.current_module_widget)
            self.current_module_widget.setParent(None)
            self.current_module_widget.deleteLater()

        module_class = self.module_instances.get(module_name)
        if module_class:
            self.current_module_widget = module_class()
            self.content_container_layout.addWidget(self.current_module_widget)

            # Force fixed height for container depending on module type
            height = self.module_heights.get(module_name, 90)
            self.content_container_widget.setFixedHeight(height)

            # Optional signal connection
            self.connect_signals_for_module(self.current_module_widget)

    def get_data(self) -> dict:
        """
        Return the current module data.
        """
        if self.current_module_widget and hasattr(self.current_module_widget, "get_data"):
            return self.current_module_widget.get_data()
        return {}

    def to_dict(self, preview: bool = False) -> dict:
        """
        Returns the configuration of this rename module as a dictionary.
        Delegates to the active submodule and adds type.
        """
        module_type = self.type_combo.currentText()
        data = self.get_data()
        data["type"] = module_type.lower().replace(" ", "_")
        return data
