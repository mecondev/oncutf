"""
rename_modules_area.py

Author: Michael Economou
Date: 2025-05-25

Container widget that holds multiple RenameModuleWidget instances inside
scrollable area and provides fixed post-processing section and global
add/remove controls.

Designed to scale and support future drag & drop reordering.
Now supports ApplicationContext for optimized access patterns.
"""

from typing import Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from modules.base_module import BaseRenameModule
from utils.logger_helper import get_logger
from widgets.name_transform_widget import NameTransformWidget
from widgets.rename_module_widget import RenameModuleWidget

# ApplicationContext integration
try:
    from core.application_context import get_app_context
except ImportError:
    get_app_context = None

logger = get_logger(__name__)


class RenameModulesArea(QWidget):
    """
    Main area that contains all rename modules and final transformation widget.
    Supports scrolling for large numbers of modules.

    Now supports ApplicationContext for optimized access patterns while maintaining
    backward compatibility with parent_window parameter.
    """
    updated = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None, parent_window: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.parent_window = parent_window  # Keep for backward compatibility
        self.module_widgets: list[RenameModuleWidget] = []

        self.setObjectName("RenameModulesArea")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(8)

        # Scrollable module container
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

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

        # Update timer for debouncing
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(100)  # 100ms debounce
        self._update_timer.timeout.connect(lambda: self.updated.emit())

    def _get_app_context(self):
        """Get ApplicationContext with fallback to None."""
        if get_app_context is None:
            return None
        try:
            return get_app_context()
        except RuntimeError:
            # ApplicationContext not ready yet
            return None

    def _on_module_updated(self):
        """Handle module updates with debouncing to prevent duplicates."""
        logger.debug("[RenameModulesArea] Module updated, restarting timer")
        self._update_timer.stop()
        self._update_timer.start()

    def add_module(self):
        """
        Add a new RenameModuleWidget to the area.
        Now uses ApplicationContext-optimized approach when available.
        """
        context = self._get_app_context()
        if context:
            # ApplicationContext available - create module without parent_window
            module = RenameModuleWidget(parent=self)
            logger.debug("[RenameModulesArea] Created RenameModuleWidget via ApplicationContext")
        else:
            # Fallback to legacy approach with parent_window
            module = RenameModuleWidget(parent=self, parent_window=self.parent_window)
            logger.debug("[RenameModulesArea] Created RenameModuleWidget via parent_window fallback")

        module.remove_requested.connect(lambda m=module: self.remove_module(m))
        module.updated.connect(lambda: self._on_module_updated())
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

    def get_all_module_instances(self) -> list[BaseRenameModule]:
        """
        Returns all current rename module widget instances.
        Useful for checking is_effective() per module.
        """
        logger.debug("[Preview] Modules: %s", self.module_widgets)
        logger.debug("[Preview] Effective check: %s", [m.is_effective() for m in self.module_widgets])

        return self.module_widgets
