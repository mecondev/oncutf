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
- Unified add/remove buttons at bottom right
- Fixed post-processing area (e.g., NameTransform)
- Responsive layout with visual separation between module logic and final formatting
"""

from typing import Optional

from core.qt_imports import pyqtSignal, QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from modules.counter_module import CounterModule
from modules.specified_text_module import SpecifiedTextModule

# Initialize Logger
from utils.logger_factory import get_cached_logger
from utils.timer_manager import schedule_ui_update
from widgets.metadata_widget import MetadataWidget
from widgets.original_name_widget import OriginalNameWidget

# ApplicationContext integration
try:
    from core.application_context import get_app_context
except ImportError:
    get_app_context = None

logger = get_cached_logger(__name__)

class RenameModuleWidget(QWidget):
    """
    Container widget that hosts all rename modules and a fixed post-processing section.
    Provides a structured area for inserting, configuring, and removing rename logic modules.

    Now supports ApplicationContext for optimized access patterns while maintaining
    backward compatibility with parent_window parameter.
    """
    remove_requested = pyqtSignal(QWidget)
    updated = pyqtSignal(QWidget)

    LABEL_WIDTH = 80  # Consistent label width for alignment

    def __init__(self, parent: Optional[QWidget] = None, parent_window: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.parent_window = parent_window  # Keep for backward compatibility
        self.setObjectName("RenameModuleWidget")
        self.setProperty("module", True)

        self.module_instances = {
            "Original Name": OriginalNameWidget,
            "Specified Text": SpecifiedTextModule,
            "Counter": CounterModule,
            "Metadata": MetadataWidget
        }

        self.module_heights = {
            "Original Name": 34,  # Reduced: just one line with minimal padding
            "Specified Text": 34,  # Reduced: just input field with minimal padding
            "Counter": 78,  # Reduced: 3 rows with minimal spacing
            "Metadata": 56   # Reduced: 2 rows with minimal spacing, matching final transformer
        }

        self.current_module_widget = None

        # --- Layout setup ---
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)  # Reduced margins for compactness
        self.main_layout.setSpacing(0)  # Control spacing manually like metadata dialog

        # --- Top layout (type selection + module area) ---

        # Row for "Type" label and combo box
        type_row = QHBoxLayout()
        type_row.setContentsMargins(0, 0, 0, 0)
        type_row.setSpacing(8)

        type_label = QLabel("Type:")
        type_label.setFixedWidth(self.LABEL_WIDTH)
        self.type_combo = QComboBox()
        self.type_combo.addItems(self.module_instances.keys())
        self.type_combo.setMaximumWidth(140)
        self.type_combo.setFixedHeight(20)
        self.type_combo.currentTextChanged.connect(self.update_module_content)

        type_row.addWidget(type_label)
        type_row.addWidget(self.type_combo)
        type_row.addStretch()
        self.main_layout.addLayout(type_row)

        # Small space between type selection and module content
        self.main_layout.addSpacing(2)

        # Module content container
        self.content_container_widget = QWidget()
        self.content_container_layout = QVBoxLayout(self.content_container_widget)
        self.content_container_layout.setContentsMargins(2, 2, 2, 2)
        self.content_container_layout.setSpacing(2)
        self.main_layout.addWidget(self.content_container_widget)

        # Set default module AFTER layout initialization
        self.type_combo.setCurrentText('Specified Text')

        # Load default module
        logger.debug(f"[RenameModuleWidget] Before QTimer.singleShot: content_container_layout is {'initialized' if hasattr(self, 'content_container_layout') else 'not initialized'}")
        schedule_ui_update(lambda: self.update_module_content(self.type_combo.currentText()), 0)

        # Apply styling after a delay to ensure it's not overridden by main app stylesheet
        schedule_ui_update(lambda: self._apply_module_styling(), 100)

        logger.debug(f"[RenameModuleWidget] Before update_module_content: content_container_layout is {'initialized' if hasattr(self, 'content_container_layout') else 'not initialized'}")

    def _get_app_context(self):
        """Get ApplicationContext with fallback to None."""
        if get_app_context is None:
            return None
        try:
            return get_app_context()
        except RuntimeError:
            # ApplicationContext not ready yet
            return None

    def _apply_module_styling(self):
        """Apply module styling after main app stylesheet is loaded."""
        # Apply styling only to this specific widget using its objectName
        style = """
            QWidget[objectName="RenameModuleWidget"] {
                background-color: #232323;
                border: 3px solid #ff0000;
                border-radius: 6px;
                margin: 8px;
            }
            /* Preserve original styling for children widgets */
            QWidget[objectName="RenameModuleWidget"] QComboBox {
                background-color: #181818;
                border: 1px solid #3a3b40;
                border-radius: 4px;
                color: #f0ebd8;
                padding: 2px 8px;
            }
            QWidget[objectName="RenameModuleWidget"] QLineEdit {
                background-color: #181818;
                border: 1px solid #3a3b40;
                border-radius: 4px;
                color: #f0ebd8;
                padding: 2px 6px;
            }
            QWidget[objectName="RenameModuleWidget"] QLabel {
                background-color: transparent;
                color: #f0ebd8;
                border: none;
            }
        """
        self.setStyleSheet(style)

    def connect_signals_for_module(self, module_widget: QWidget) -> None:
        if hasattr(module_widget, "updated"):
            try:
                # Connect the module's updated signal to emit our updated signal
                module_widget.updated.connect(lambda _: self.updated.emit(self))
                logger.info("[RenameModuleWidget] Connected module.updated -> self.updated", extra={"dev_only": True})

            except Exception as e:
                logger.warning(f"[RenameModuleWidget] Signal connection failed: {e}")

        else:
            logger.warning("[RenameModuleWidget] Could not connect signal. Has updated: %s",
                        hasattr(module_widget, "updated"))

    def update_module_content(self, module_name: str) -> None:
        """
        Replace module widget and adjust height constraint.
        Now uses ApplicationContext-optimized approach for MetadataWidget creation.
        """
        if self.current_module_widget:
            self.content_container_layout.removeWidget(self.current_module_widget)
            self.current_module_widget.setParent(None)
            self.current_module_widget.deleteLater()

        module_class = self.module_instances.get(module_name)
        if module_class:
            # MetadataWidget now supports ApplicationContext, no need for parent_window
            if module_name == "Metadata":
                # Try ApplicationContext approach first, fallback to parent_window
                context = self._get_app_context()
                if context:
                    # ApplicationContext available - MetadataWidget can find what it needs
                    self.current_module_widget = module_class()
                    logger.debug("[RenameModuleWidget] Created MetadataWidget via ApplicationContext")
                else:
                    # Fallback to legacy approach with parent_window
                    self.current_module_widget = module_class(parent_window=self.parent_window)
                    logger.debug("[RenameModuleWidget] Created MetadataWidget via parent_window fallback")
            else:
                self.current_module_widget = module_class()

            self.module = self.current_module_widget  # Define the module
            self.content_container_layout.addWidget(self.current_module_widget)

            # Force fixed height for container depending on module type
            height = self.module_heights.get(module_name, 90)
            self.content_container_widget.setFixedHeight(height)

            # Optional signal connection
            self.connect_signals_for_module(self.current_module_widget)

        # Emit updated signal to refresh preview
        self.updated.emit(self)

    def get_data(self) -> dict:
        """
        Return the current module data.
        """
        if self.current_module_widget and hasattr(self.current_module_widget, "get_data"):
            data = self.current_module_widget.get_data()
        else:
            data = {}

        return data

    def to_dict(self, preview: bool = False) -> dict:
        """
        Returns the configuration of this rename module as a dictionary.
        Delegates to the active submodule and adds type.
        """
        module_type = self.type_combo.currentText()
        data = self.get_data()
        data["type"] = module_type.lower().replace(" ", "_")
        return data

    def is_effective(self) -> bool:
        """
        Determines if this module is effectively doing something, by checking its data.
        """
        if not self.current_module_widget:
            logger.warning("[ModuleWidget] No module loaded for widget!")
            return False  # No module loaded

        data = self.get_data()

        # Try to access the class method `is_effective(data)` safely
        module_class = type(self.current_module_widget)
        if hasattr(module_class, "is_effective"):
            return module_class.is_effective(data)  # type: ignore[attr-defined]
            # return self.module.is_effective(self.get_data())
        return False



