"""
Module: rename_module_widget.py

Author: Michael Economou
Date: 2025-06-15

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

from core.pyqt_imports import QComboBox, QHBoxLayout, QLabel, Qt, QVBoxLayout, QWidget, pyqtSignal
from modules.counter_module import CounterModule

# Lazy import to avoid circular import: from modules.specified_text_module import SpecifiedTextModule
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

        # Set transparent background to avoid white borders around rounded corners
        self.setAttribute(Qt.WA_TranslucentBackground, True)  # type: ignore

        # Lazy import to avoid circular import
        from modules.specified_text_module import SpecifiedTextModule

        self.module_instances = {
            "Counter": CounterModule,
            "Metadata": MetadataWidget,
            "Original Name": OriginalNameWidget,
            "Specified Text": SpecifiedTextModule
        }

        self.module_heights = {
            "Counter": 88,  # Increased: 4px more space to prevent focus border clipping
            "Metadata": 74,   # Increased: 12px more space for increased row spacing
            "Original Name": 34,  # Reduced: just one line with minimal padding
            "Specified Text": 37  # Increased: 3px more space to prevent clipping
        }

        self.current_module_widget = None

                # --- Layout setup ---
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)  # 2px margins around the plate
        self.main_layout.setSpacing(0)

                # Get colors from theme engine
        from utils.theme_engine import ThemeEngine
        theme = ThemeEngine()
        app_background = theme.get_color('app_background')
        drag_handle_background = theme.get_color('module_drag_handle')

        # --- Main plate container ---
        self.plate_widget = QWidget()
        self.plate_widget.setObjectName("module_plate")
        # Apply plate styling: app background, rounded corners
        self.plate_widget.setStyleSheet(f"""
            QWidget[objectName="module_plate"] {{
                background-color: {app_background};
                border-radius: 8px;
            }}
        """)

        # Plate layout with drag handle + content
        plate_layout = QHBoxLayout(self.plate_widget)
        plate_layout.setContentsMargins(0, 0, 0, 0)
        plate_layout.setSpacing(0)

        # --- Drag Handle Area ---
        from utils.icons_loader import get_menu_icon
        self.drag_handle = QLabel()
        self.drag_handle.setFixedWidth(30)
        self.drag_handle.setAlignment(Qt.AlignCenter)  # type: ignore
        # Subtle background for handle area
        self.drag_handle.setStyleSheet(f"""
            QLabel {{
                background-color: {drag_handle_background};
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
            }}
        """)

        # Set drag handle icon
        drag_icon = get_menu_icon("more-vertical")
        self.drag_handle.setPixmap(drag_icon.pixmap(16, 16))

        plate_layout.addWidget(self.drag_handle)

        # --- Content Area ---
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(8, 6, 3, 6)  # Padding inside content area (reduced right margin for more space)
        content_layout.setSpacing(4)

        # Row for "Type" label and combo box
        type_row = QHBoxLayout()
        type_row.setContentsMargins(0, 0, 0, 0)
        type_row.setSpacing(8)

        type_label = QLabel("Type:")
        type_label.setFixedWidth(self.LABEL_WIDTH)
        type_label.setAlignment(Qt.AlignVCenter)  # type: ignore
        self.type_combo = QComboBox()
        self.type_combo.addItems(self.module_instances.keys())
        self.type_combo.setMaximumWidth(140)
        self.type_combo.setFixedHeight(20)
        self.type_combo.currentTextChanged.connect(self.update_module_content)

        type_row.addWidget(type_label, 0, Qt.AlignVCenter)  # type: ignore
        type_row.addWidget(self.type_combo, 0, Qt.AlignVCenter)  # type: ignore
        type_row.addStretch()
        content_layout.addLayout(type_row)

        # Module content container
        self.content_container_widget = QWidget()
        self.content_container_layout = QVBoxLayout(self.content_container_widget)
        self.content_container_layout.setContentsMargins(0, 0, 0, 0)
        self.content_container_layout.setSpacing(0)
        content_layout.addWidget(self.content_container_widget)

        plate_layout.addWidget(content_widget)
        self.main_layout.addWidget(self.plate_widget)

        # Set default module AFTER layout initialization
        self.type_combo.setCurrentText('Specified Text')

        # Load default module
        logger.debug(f"[RenameModuleWidget] Before QTimer.singleShot: content_container_layout is {'initialized' if hasattr(self, 'content_container_layout') else 'not initialized'}")
        schedule_ui_update(lambda: self.update_module_content(self.type_combo.currentText()), 0)

        # CSS styling is now applied via external stylesheet

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



