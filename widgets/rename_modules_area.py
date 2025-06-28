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
from utils.icons_loader import get_menu_icon
from utils.logger_factory import get_cached_logger
from utils.timer_manager import schedule_scroll_adjust
from widgets.name_transform_widget import NameTransformWidget
from widgets.rename_module_widget import RenameModuleWidget

# ApplicationContext integration
try:
    from core.application_context import get_app_context
except ImportError:
    get_app_context = None

logger = get_cached_logger(__name__)


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
        main_layout.setSpacing(0)  # Control spacing manually like metadata dialog

        # Small spacing at the top to align with preview labels
        # This aligns the modules with the preview tables labels
        main_layout.addSpacing(4)

        # Scrollable module container
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll_layout.setSpacing(8)  # Reduce spacing between modules

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        # Small space between scroll area and footer
        main_layout.addSpacing(4)

        # Final transformation + controls
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(2, 2, 2, 2)
        footer_layout.setSpacing(10)

        # Left side: name transform
        self.name_transform_label = QLabel("Final Transform:")
        self.name_transform_widget = NameTransformWidget()
        self.name_transform_widget.updated.connect(self.updated.emit)

        name_transform_layout = QVBoxLayout()
        name_transform_layout.setContentsMargins(0, 0, 0, 0)
        name_transform_layout.setSpacing(2)  # Small space between label and widget
        name_transform_layout.addWidget(self.name_transform_label)
        name_transform_layout.addWidget(self.name_transform_widget)

        # Middle spacer
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Right side: buttons positioned to align with specific transform rows
        # Create a layout that matches the structure of name_transform_widget
        buttons_container = QWidget()
        buttons_container_layout = QVBoxLayout(buttons_container)
        buttons_container_layout.setContentsMargins(0, 0, 0, 0)
        buttons_container_layout.setSpacing(0)

        # Space to align with "Final Transform:" label (22px label height + 2px spacing)
        buttons_container_layout.addSpacing(24)

        # Space to align with Greeklish row (20px row height + 6px spacing)
        buttons_container_layout.addSpacing(26)

        # Add button - aligns with Case row (2nd row)
        case_button_layout = QHBoxLayout()
        case_button_layout.setContentsMargins(0, 0, 0, 0)
        case_button_layout.addStretch()

        self.add_button = QPushButton()
        self.add_button.setIcon(get_menu_icon("plus"))
        self.add_button.setFixedSize(28, 28)
        self.add_button.setToolTip("Add new module")
        self.add_button.clicked.connect(self.add_module)

        case_button_layout.addWidget(self.add_button)
        buttons_container_layout.addLayout(case_button_layout)

        # Space between Case and Separator rows (6px spacing)
        buttons_container_layout.addSpacing(6)

        # Remove button - aligns with Separator row (3rd row)
        separator_button_layout = QHBoxLayout()
        separator_button_layout.setContentsMargins(0, 0, 0, 0)
        separator_button_layout.addStretch()

        self.remove_button = QPushButton()
        self.remove_button.setIcon(get_menu_icon("minus"))
        self.remove_button.setFixedSize(28, 28)
        self.remove_button.setToolTip("Remove last module")
        self.remove_button.clicked.connect(self.remove_last_module)

        separator_button_layout.addWidget(self.remove_button)
        buttons_container_layout.addLayout(separator_button_layout)

        # Add remaining stretch
        buttons_container_layout.addStretch()

        footer_layout.addLayout(name_transform_layout)
        footer_layout.addItem(spacer)
        footer_layout.addWidget(buttons_container)

        main_layout.addLayout(footer_layout)

        self.add_module()  # Start with one by default
        self._update_remove_button_state()  # Set initial button state

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
        logger.debug("[RenameModulesArea] Module updated, restarting timer", extra={"dev_only": True})
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
            logger.debug("[RenameModulesArea] Created RenameModuleWidget via ApplicationContext", extra={"dev_only": True})
        else:
            # Fallback to legacy approach with parent_window
            module = RenameModuleWidget(parent=self, parent_window=self.parent_window)
            logger.debug("[RenameModulesArea] Created RenameModuleWidget via parent_window fallback", extra={"dev_only": True})

        module.remove_requested.connect(lambda m=module: self.remove_module(m))
        module.updated.connect(lambda: self._on_module_updated())
        self.module_widgets.append(module)

        # Add separator if this is not the first module
        if len(self.module_widgets) > 1:
            separator = self._create_separator()
            self.scroll_layout.addWidget(separator)

        self.scroll_layout.addWidget(module)
        self._update_remove_button_state()

        # Schedule scroll to new module
        schedule_scroll_adjust(lambda: self._scroll_to_show_new_module(module), 50)

        self.updated.emit()

    def remove_module(self, module: RenameModuleWidget):
        # Ensure at least one module always remains
        if len(self.module_widgets) <= 1:
            logger.debug("[RenameModulesArea] Cannot remove module - minimum 1 required", extra={"dev_only": True})
            return

        if module in self.module_widgets:
            # Find and remove any separator associated with this module
            module_index = self.scroll_layout.indexOf(module)
            if module_index > 0:  # Check if there's a separator before this module
                previous_widget = self.scroll_layout.itemAt(module_index - 1)
                if previous_widget and hasattr(previous_widget.widget(), 'accessibleName'):
                    if previous_widget.widget().accessibleName() == "module_separator":
                        separator = previous_widget.widget()
                        self.scroll_layout.removeWidget(separator)
                        separator.setParent(None)
                        separator.deleteLater()

            self.module_widgets.remove(module)
            self.scroll_layout.removeWidget(module)
            module.setParent(None)
            module.deleteLater()
            self._update_remove_button_state()

            # If only one module remains, scroll to top
            if len(self.module_widgets) == 1:
                # Schedule scroll to top
                schedule_scroll_adjust(lambda: self.scroll_area.verticalScrollBar().setValue(0), 50)
                logger.debug("[RenameModulesArea] Scrolled to top after removal (single module remains)", extra={"dev_only": True})

            self.updated.emit()

    def remove_last_module(self):
        # Ensure at least one module always remains
        if len(self.module_widgets) > 1:
            self.remove_module(self.module_widgets[-1])
        else:
            logger.debug("[RenameModulesArea] Cannot remove last module - minimum 1 required", extra={"dev_only": True})

    def _update_remove_button_state(self):
        """Enable/disable remove button based on number of modules."""
        self.remove_button.setEnabled(len(self.module_widgets) > 1)
        logger.debug(f"[RenameModulesArea] Remove button {'enabled' if len(self.module_widgets) > 1 else 'disabled'} - {len(self.module_widgets)} modules", extra={"dev_only": True})

    def _scroll_to_show_new_module(self, new_module):
        """Scroll to ensure the newly added module is visible."""
        if len(self.module_widgets) == 1:
            # If only one module, scroll to top
            self.scroll_area.verticalScrollBar().setValue(0)
            logger.debug("[RenameModulesArea] Scrolled to top (single module)", extra={"dev_only": True})
        else:
            # If multiple modules, scroll to show the new module
            self.scroll_area.ensureWidgetVisible(new_module, 50, 50)
            logger.debug(f"[RenameModulesArea] Scrolled to show new module ({len(self.module_widgets)} total)", extra={"dev_only": True})

    def _create_separator(self):
        """Create a visual separator between modules."""
        from PyQt5.QtWidgets import QFrame
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setAccessibleName("module_separator")  # For QSS targeting
        separator.setFixedHeight(2)  # Make separator 2px tall
        separator.setContentsMargins(10, 0, 10, 0)  # Add some horizontal margin
        return separator

    def set_current_file_for_modules(self, file_item) -> None:
        """
        Set the current file for all SpecifiedText modules.

        Args:
            file_item: The FileItem object representing the currently selected file
        """
        for module_widget in self.module_widgets:
            if hasattr(module_widget, 'current_module_widget') and module_widget.current_module_widget:
                # Check if this is a SpecifiedTextModule
                module_instance = module_widget.current_module_widget
                if hasattr(module_instance, 'set_current_file'):
                    module_instance.set_current_file(file_item)

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
        logger.debug("[Preview] Modules: %s", self.module_widgets, extra={"dev_only": True})
        logger.debug("[Preview] Effective check: %s", [m.is_effective() for m in self.module_widgets], extra={"dev_only": True})

        return self.module_widgets
