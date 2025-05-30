"""
rename_modules_area.py

Author: Michael Economou
Date: 2025-05-25

Container widget that holds multiple RenameModuleWidget instances inside
scrollable area and provides fixed post-processing section and global
add/remove controls.

Designed to scale and support future drag & drop reordering.
"""

from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton,
    QSpacerItem, QSizePolicy, QLabel, QFrame
)
from PyQt5.QtCore import pyqtSignal

from widgets.rename_module_widget import RenameModuleWidget
from widgets.name_transform_widget import NameTransformWidget


class RenameModulesArea(QWidget):
    """
    Main area that contains all rename modules and final transformation widget.
    Supports scrolling for large numbers of modules.
    """
    updated = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None, parent_window: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.parent_window = parent_window
        self.module_widgets: list[RenameModuleWidget] = []

        self.setObjectName("RenameModulesArea")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(8)

        # Scrollable module container
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(False)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll_layout.setSpacing(10)

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        # Final transformation + controls
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(2, 10, 2, 2)
        footer_layout.setSpacing(12)

        # Left side: name transform
        self.name_transform_label = QLabel("Final Transform:")
        self.name_transform_widget = NameTransformWidget()
        self.name_transform_widget.updated.connect(self.updated.emit)

        name_transform_layout = QVBoxLayout()
        name_transform_layout.addWidget(self.name_transform_label)
        name_transform_layout.addWidget(self.name_transform_widget)

        # Middle spacer
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Right side: buttons
        self.add_button = QPushButton("+")
        self.remove_button = QPushButton("-")
        self.add_button.setFixedSize(28, 28)
        self.remove_button.setFixedSize(28, 28)

        self.add_button.clicked.connect(self.add_module)
        self.remove_button.clicked.connect(self.remove_last_module)

        buttons_layout = QVBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.remove_button)
        buttons_layout.addStretch()

        footer_layout.addLayout(name_transform_layout)
        footer_layout.addItem(spacer)
        footer_layout.addLayout(buttons_layout)

        main_layout.addLayout(footer_layout)

        self.add_module()  # Start with one by default

    def add_module(self):
        module = RenameModuleWidget(parent=self, parent_window=self.parent_window)
        module.remove_requested.connect(lambda m=module: self.remove_module(m))
        module.updated.connect(self.updated.emit)
        self.module_widgets.append(module)
        self.scroll_layout.addWidget(module)
        self.updated.emit()

    def remove_module(self, module: RenameModuleWidget):
        if module in self.module_widgets:
            self.module_widgets.remove(module)
            self.scroll_layout.removeWidget(module)
            module.setParent(None)
            module.deleteLater()
            self.updated.emit()

    def remove_last_module(self):
        if self.module_widgets:
            self.remove_module(self.module_widgets[-1])

    def get_all_data(self) -> dict:
        """
        Collects data from all modules and final transform.
        """
        return {
            "modules": [m.to_dict() for m in self.module_widgets],
            "post_transform": self.name_transform_widget.get_data()
        }
