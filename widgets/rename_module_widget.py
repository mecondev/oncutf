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

from config import ICON_SIZES
from core.pyqt_imports import (
    QApplication,
    QColor,
    QComboBox,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    Qt,
    QVBoxLayout,
    QWidget,
    pyqtSignal,
)
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

    def __init__(
        self, parent: Optional[QWidget] = None, parent_window: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)

        self.parent_window = parent_window  # Keep for backward compatibility
        self.setObjectName("RenameModuleWidget")
        self.setProperty("module", True)

        # Set transparent background to avoid white borders around rounded corners
        self.setAttribute(Qt.WA_TranslucentBackground, True)  # type: ignore

        # Lazy import to avoid circular import
        from modules.specified_text_module import SpecifiedTextModule
        from modules.text_removal_module import TextRemovalModule

        self.module_instances = {
            "Counter": CounterModule,
            "Metadata": MetadataWidget,
            "Original Name": OriginalNameWidget,
            "Remove Text from Original Name": TextRemovalModule,
            "Specified Text": SpecifiedTextModule,
        }

        self.module_heights = {
            "Counter": 88,  # Increased: 4px more space to prevent focus border clipping
            "Metadata": 66,  # Reduced: 8px less space due to reduced row spacing
            "Original Name": 34,  # Reduced: just one line with minimal padding
            "Remove Text from Original Name": 64,  # Two rows: text input + options
            "Specified Text": 37,  # Increased: 3px more space to prevent clipping
        }

        self.current_module_widget = None

        # --- Layout setup ---
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)  # 2px margins around the plate
        self.main_layout.setSpacing(0)

        # Get colors from theme engine
        from utils.theme_engine import ThemeEngine

        theme = ThemeEngine()
        app_background = theme.get_color("app_background")
        drag_handle_background = theme.get_color("module_drag_handle")

        # --- Main plate container ---
        self.plate_widget = QWidget()
        self.plate_widget.setObjectName("module_plate")
        # Apply plate styling: app background, rounded corners
        self.plate_widget.setStyleSheet(
            f"""
            QWidget[objectName="module_plate"] {{
                background-color: {app_background};
                border-radius: 8px;
            }}
        """
        )

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
        self.drag_handle.setStyleSheet(
            f"""
            QLabel {{
                background-color: {drag_handle_background};
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
            }}
        """
        )

        # Set drag handle icon
        drag_icon = get_menu_icon("more-vertical")
        self.drag_handle.setPixmap(drag_icon.pixmap(ICON_SIZES["SMALL"], ICON_SIZES["SMALL"]))

        # Enable drag functionality
        self.drag_handle.setAcceptDrops(True)
        self.drag_handle.setAttribute(Qt.WA_Hover, True)  # Enable hover events
        self.drag_handle.mousePressEvent = self.drag_handle_mouse_press
        self.drag_handle.mouseMoveEvent = self.drag_handle_mouse_move
        self.drag_handle.mouseReleaseEvent = self.drag_handle_mouse_release
        self.drag_handle.enterEvent = self.drag_handle_enter
        self.drag_handle.leaveEvent = self.drag_handle_leave

        # Drag state
        self.drag_start_position = None
        self.is_dragging = False

        plate_layout.addWidget(self.drag_handle)

        # --- Content Area ---
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(
            8, 6, 3, 6
        )  # Padding inside content area (reduced right margin for more space)
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
        self.type_combo.setFixedHeight(24)  # Match metadata_widget height
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
        self.type_combo.setCurrentText("Specified Text")

        # Load default module
        schedule_ui_update(lambda: self.update_module_content(self.type_combo.currentText()), 0)

        # CSS styling is now applied via external stylesheet

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
        """Connect the module's updated signal to our updated signal."""
        if hasattr(module_widget, "updated"):
            try:
                # Connect the module's updated signal to emit our updated signal
                module_widget.updated.connect(lambda _: self.updated.emit(self))
            except Exception as e:
                logger.warning(f"[RenameModuleWidget] Signal connection failed: {e}")

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
            # MetadataWidget needs parent_window to get selected files
            if module_name == "Metadata":
                # Always pass parent_window for MetadataWidget
                self.current_module_widget = module_class(parent_window=self.parent_window)
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
        converted_type = module_type.lower().replace(" ", "_")
        data["type"] = converted_type
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

    # Drag & Drop functionality
    def drag_handle_enter(self, event):
        """Handle mouse enter on drag handle - change cursor."""
        from core.pyqt_imports import QCursor

        QApplication.setOverrideCursor(QCursor(Qt.OpenHandCursor))

    def drag_handle_leave(self, event):
        """Handle mouse leave on drag handle - restore cursor."""
        if not self.is_dragging:
            QApplication.restoreOverrideCursor()

    def drag_handle_mouse_press(self, event):
        """Handle mouse press on drag handle - prepare for dragging."""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            from core.pyqt_imports import QCursor

            QApplication.setOverrideCursor(QCursor(Qt.ClosedHandCursor))
            event.accept()

    def drag_handle_mouse_move(self, event):
        """Handle mouse move on drag handle - start dragging if moved enough."""
        if not (event.buttons() & Qt.LeftButton):
            return

        if not self.drag_start_position:
            return

        # Check if we've moved far enough to start dragging
        if (
            event.pos() - self.drag_start_position
        ).manhattanLength() < QApplication.startDragDistance():
            return

        if not self.is_dragging:
            self.start_drag()

        # Update module position to follow mouse during drag
        if self.is_dragging:
            self.update_drag_position(event.globalPos())

        event.accept()

    def drag_handle_mouse_release(self, event):
        """Handle mouse release on drag handle - end dragging."""
        if event.button() == Qt.LeftButton:
            if self.is_dragging:
                self.end_drag()
            else:
                QApplication.restoreOverrideCursor()
            self.drag_start_position = None
            event.accept()

    def start_drag(self):
        """Start the drag operation."""
        self.is_dragging = True

        # Enhanced visual feedback during dragging
        self.setWindowOpacity(0.8)
        self.raise_()

        # Add shadow effect for better visual feedback
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(2, 2)
        self.setGraphicsEffect(shadow)

        # Scale up slightly to show it's being dragged
        self.setStyleSheet(
            """
            QWidget[objectName="RenameModuleWidget"] {
                transform: scale(1.02);
            }
        """
        )

        # Notify parent that dragging started - try different parent levels
        parent = self.parent()
        while parent:
            if hasattr(parent, "module_drag_started"):
                parent.module_drag_started(self)
                break
            parent = parent.parent()

    def end_drag(self):
        """End the drag operation."""
        self.is_dragging = False

        # Restore normal appearance
        self.setWindowOpacity(1.0)
        self.setGraphicsEffect(None)  # Remove shadow
        self.setStyleSheet("")  # Remove scale transform
        QApplication.restoreOverrideCursor()

        # Restore original position (remove horizontal offset)
        if self.parent():
            # Get the correct position from the layout
            from utils.timer_manager import schedule_ui_update

            schedule_ui_update(self.restore_original_position, 10)

        # Notify parent that dragging ended - try different parent levels
        parent = self.parent()
        while parent:
            if hasattr(parent, "module_drag_ended"):
                parent.module_drag_ended(self)
                break
            parent = parent.parent()

    def restore_original_position(self):
        """Restore the module to its proper position in the layout."""
        if self.parent():
            # Force layout update to restore proper positioning
            self.parent().updateGeometry()
            self.parent().update()

    def update_drag_position(self, global_pos):
        """Update module position during drag to follow mouse with horizontal movement."""
        if not self.is_dragging:
            return

        # Get mouse position relative to parent widget
        if self.parent():
            local_pos = self.parent().mapFromGlobal(global_pos)

            # Get current geometry
            current_rect = self.geometry()

            # Calculate horizontal offset (allow some horizontal movement for visual feedback)
            original_x = current_rect.x()
            mouse_offset_x = (local_pos.x() - original_x) * 0.1  # 10% of horizontal movement
            # Clamp horizontal movement to a reasonable range (-20 to +20 pixels)
            mouse_offset_x = max(-20, min(20, mouse_offset_x))

            # Update position with horizontal offset
            new_x = int(original_x + mouse_offset_x)
            self.move(new_x, current_rect.y())

            # Notify parent for auto-scroll handling
            parent = self.parent()
            while parent:
                if hasattr(parent, "handle_drag_auto_scroll"):
                    parent.handle_drag_auto_scroll(global_pos)
                    break
                parent = parent.parent()
