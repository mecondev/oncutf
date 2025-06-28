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
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from modules.base_module import BaseRenameModule
from utils.logger_factory import get_cached_logger
from utils.timer_manager import schedule_scroll_adjust
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
        main_layout.setContentsMargins(6, 2, 6, 2)  # Reduced bottom margin from 6 to 2
        main_layout.setSpacing(0)  # Control spacing manually like metadata dialog

        # No spacing at the top for testing - direct alignment with preview labels
        # main_layout.addSpacing(0)  # Commented out for zero spacing

        # Scrollable module container
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(4, 2, 4, 2)  # Reduced bottom padding from 4 to 2
        self.scroll_layout.setSpacing(6)  # Reduced spacing between modules from 8 to 6

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

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

            # If only one module remains, scroll to top
            if len(self.module_widgets) == 1:
                # Schedule scroll to top
                schedule_scroll_adjust(lambda: self.scroll_area.verticalScrollBar().setValue(0), 50)
                logger.debug("[RenameModulesArea] Scrolled to top after removal (single module remains)", extra={"dev_only": True})

            self.updated.emit()

    def remove_last_module(self):
        """Remove the last module if more than one exists."""
        if len(self.module_widgets) > 1:
            self.remove_module(self.module_widgets[-1])
        else:
            logger.debug("[RenameModulesArea] Cannot remove last module - minimum 1 required", extra={"dev_only": True})

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
        Collects data from all modules.
        Note: post_transform data is now handled by FinalTransformContainer.
        """
        return {
            "modules": [m.to_dict() for m in self.module_widgets]
        }

    def get_all_module_instances(self) -> list[BaseRenameModule]:
        """
        Returns all current rename module widget instances.
        Useful for checking is_effective() per module.
        """
        logger.debug("[Preview] Modules: %s", self.module_widgets, extra={"dev_only": True})
        logger.debug("[Preview] Effective check: %s", [m.is_effective() for m in self.module_widgets], extra={"dev_only": True})

        return self.module_widgets
