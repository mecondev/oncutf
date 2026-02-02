"""Module: rename_module_widget.py.

Author: Michael Economou
Date: 2025-05-06

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

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from oncutf.config import ICON_SIZES
from oncutf.controllers.module_drag_drop_manager import ModuleDragDropManager
from oncutf.controllers.module_orchestrator import ModuleOrchestrator
from oncutf.ui.theme_manager import get_theme_manager

# Lazy import to avoid circular import: from oncutf.modules.specified_text_module import SpecifiedTextModule
# Initialize Logger
from oncutf.ui.widgets.styled_combo_box import StyledComboBox
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import schedule_ui_update

logger = get_cached_logger(__name__)


class RenameModuleWidget(QWidget):
    """Container widget that hosts all rename modules and a fixed post-processing section.
    Provides a structured area for inserting, configuring, and removing rename logic modules.

    Phase 2 Refactoring:
    - Uses ModuleDragDropManager for drag & drop state management
    - Separated drag logic from UI rendering
    - Maintains backward compatible signals and API

    Now supports QtAppContext for optimized access patterns while maintaining
    backward compatibility with parent_window parameter.
    """

    remove_requested = pyqtSignal(QWidget)
    updated = pyqtSignal(QWidget)

    LABEL_WIDTH = 80  # Consistent label width for alignment

    # Shared drag manager for all instances (drag state is per-widget but manager is shared)
    _drag_manager = ModuleDragDropManager()

    # Shared orchestrator for module discovery (Phase 3)
    _orchestrator = ModuleOrchestrator()

    @classmethod
    def _build_module_instances_dict(cls) -> dict[str, type]:
        """Build module instances dict from orchestrator (Phase 3: Dynamic discovery).

        Returns:
            Dict mapping display names to module classes

        """
        # Special UI widgets that wrap logic modules
        from oncutf.ui.widgets.metadata_widget import MetadataWidget
        from oncutf.ui.widgets.original_name_widget import OriginalNameWidget

        # Modules that are post-processing only (not selectable in rename modules)
        # NameTransformModule is used in post_transform area, not as a rename module
        post_processing_modules = {"Name Transform"}

        module_instances: dict[str, type] = {}

        for descriptor in cls._orchestrator.get_available_modules():
            # Skip post-processing modules (they're not selectable rename modules)
            if descriptor.display_name in post_processing_modules:
                continue

            # Special cases: UI widgets that wrap logic modules
            if descriptor.display_name == "Metadata":
                module_instances[descriptor.display_name] = MetadataWidget
            elif descriptor.display_name == "Original Name":
                module_instances[descriptor.display_name] = OriginalNameWidget
            else:
                # Use the module class directly (it's both logic + UI)
                module_instances[descriptor.display_name] = descriptor.module_class

        return module_instances

    @classmethod
    def _build_module_heights_dict(cls) -> dict[str, int]:
        """Build module heights dict from orchestrator metadata (Phase 3).

        Returns:
            Dict mapping display names to UI heights in pixels

        """
        # Height calculation: base_height + (ui_rows * row_height) + padding
        base_height = 28  # Label + combo
        row_height = 24  # Per content row
        padding = 6  # Top + bottom padding

        heights = {}
        for descriptor in cls._orchestrator.get_available_modules():
            calculated_height = base_height + (descriptor.ui_rows * row_height) + padding

            # Apply manual overrides for specific modules (backward compatibility)
            overrides = {
                "Counter": 88,  # Needs extra space for focus border
                "Metadata": 66,  # Reduced row spacing
                "Original Name": 34,  # Minimal padding
                "Remove Text from Original Name": 64,  # Two rows
                "Specified Text": 37,  # Prevent clipping
            }

            heights[descriptor.display_name] = overrides.get(
                descriptor.display_name, calculated_height
            )

        return heights

    def __init__(self, parent: QWidget | None = None, parent_window: QWidget | None = None) -> None:
        """Initialize the rename module widget with dynamic module loading."""
        super().__init__(parent)

        self.parent_window = parent_window  # Keep for backward compatibility
        self.setObjectName("RenameModuleWidget")
        self.setProperty("module", True)

        # Set transparent background to avoid white borders around rounded corners
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Phase 3: Get module instances from orchestrator (replacing hardcoded dict)
        self.module_instances = self._build_module_instances_dict()
        self.module_heights = self._build_module_heights_dict()

        self.current_module_widget = None

        # --- Layout setup ---
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)  # 2px margins around the plate
        self.main_layout.setSpacing(0)

        # Get colors from theme manager
        theme = get_theme_manager()
        app_background = theme.get_color("background")  # Main app background
        drag_handle_background = theme.get_color("module_drag_handle")
        border_color = theme.get_color("border")

        # --- Main plate container ---
        self.plate_widget = QWidget()
        self.plate_widget.setObjectName("module_plate")
        # Apply plate styling: app background, border, rounded corners
        self.plate_widget.setStyleSheet(
            f"""
            QWidget[objectName="module_plate"] {{
                background-color: {app_background};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
        """
        )

        # Plate layout with drag handle + content
        plate_layout = QHBoxLayout(self.plate_widget)
        plate_layout.setContentsMargins(0, 0, 0, 0)
        plate_layout.setSpacing(0)

        # --- Drag Handle Area ---
        from oncutf.ui.helpers.icons_loader import get_menu_icon

        self.drag_handle = QLabel()
        self.drag_handle.setFixedWidth(30)
        self.drag_handle.setAlignment(Qt.AlignCenter)
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
        drag_icon = get_menu_icon("more_vert")
        self.drag_handle.setPixmap(drag_icon.pixmap(ICON_SIZES["SMALL"], ICON_SIZES["SMALL"]))

        # Enable drag functionality
        self.drag_handle.setAcceptDrops(True)
        self.drag_handle.setAttribute(Qt.WA_Hover, True)  # Enable hover events
        self.drag_handle.mousePressEvent = self.drag_handle_mouse_press
        self.drag_handle.mouseMoveEvent = self.drag_handle_mouse_move
        self.drag_handle.mouseReleaseEvent = self.drag_handle_mouse_release
        self.drag_handle.enterEvent = self.drag_handle_enter
        self.drag_handle.leaveEvent = self.drag_handle_leave

        # Drag state now managed by ModuleDragDropManager (Phase 2)
        # No local state needed - all in manager

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
        type_label.setAlignment(Qt.AlignVCenter)
        self.type_combo = StyledComboBox()
        self.type_combo.addItems(self.module_instances.keys())
        self.type_combo.setMaximumWidth(140)
        # Theme styling is handled by StyledComboBox
        self.type_combo.currentTextChanged.connect(self.update_module_content)

        type_row.addWidget(type_label, 0, Qt.AlignVCenter)
        type_row.addWidget(self.type_combo, 0, Qt.AlignVCenter)
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
        """Get QtAppContext with fallback to None."""
        try:
            from oncutf.ui.adapters.qt_app_context import get_qt_app_context

            return get_qt_app_context()
        except (ImportError, RuntimeError):
            # QtAppContext not available or not ready yet
            return None

    def _compute_stable_height(self, rows: int, content_widget: QWidget | None) -> int:
        """Compute a stable visual height for module content based on logical row count.

        The goal is to keep consistent heights across modules:
        - Use a normalized row height and spacing to align visually
        - Respect the content's size hint to avoid clipping
        """
        # Normalized metrics (aligned with common 24px control height + vertical padding)
        base_row_height = 28  # px per visual row (control height + small internal padding)
        row_spacing = 4  # px between visual rows
        vertical_padding = 12  # px total (matches content layout top+bottom ~ 6px each)

        height = vertical_padding + rows * base_row_height + max(0, rows - 1) * row_spacing

        # Ensure we never clip actual content
        try:
            hint = content_widget.sizeHint().height() if content_widget else 0
            if hint and hint > height:
                height = hint
        except Exception:
            pass

        return height

    def connect_signals_for_module(self, module_widget: QWidget) -> None:
        """Connect the module's updated signal to our updated signal."""
        if hasattr(module_widget, "updated"):
            try:
                # Connect the module's updated signal to emit our updated signal
                module_widget.updated.connect(lambda _: self.updated.emit(self))
            except Exception as e:
                logger.warning("[RenameModuleWidget] Signal connection failed: %s", e)

    def update_module_content(self, module_name: str) -> None:
        """Replace module widget and adjust height constraint.
        Now uses QtAppContext-optimized approach for MetadataWidget creation.
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

            # Compute stable height based on visual row counts per module
            rows_map = getattr(self, "_module_rows", None)
            if rows_map is None:
                rows_map = {
                    "Counter": 3,
                    "Metadata": 2,
                    "Original Name": 1,
                    "Remove Text from Original Name": 2,
                    "Specified Text": 1,
                }
                self._module_rows = rows_map

            rows = rows_map.get(module_name, 1)
            stable_height = self._compute_stable_height(rows, self.current_module_widget)
            self.content_container_widget.setFixedHeight(stable_height)

            # Optional signal connection
            self.connect_signals_for_module(self.current_module_widget)

        # Schedule preview update after module initialization completes
        # Small delay ensures MetadataWidget's auto-selection has finished
        from oncutf.utils.shared.timer_manager import schedule_ui_update

        schedule_ui_update(lambda: self.updated.emit(self), 50)

    def get_data(self) -> dict:
        """Return the current module data."""
        if self.current_module_widget and hasattr(self.current_module_widget, "get_data"):
            try:
                data = self.current_module_widget.get_data()
            except RuntimeError:
                # Widget was deleted
                data = {}
        else:
            data = {}

        return data

    def to_dict(self, _preview: bool = False) -> dict:
        """Returns the configuration of this rename module as a dictionary.
        Delegates to the active submodule and adds type.
        """
        module_type = self.type_combo.currentText()
        data = self.get_data()
        converted_type = module_type.lower().replace(" ", "_")
        data["type"] = converted_type
        return data

    def is_effective(self) -> bool:
        """Determines if this module is effectively doing something, by checking its data."""
        if not self.current_module_widget:
            logger.warning("[ModuleWidget] No module loaded for widget!")
            return False  # No module loaded

        data = self.get_data()

        # Try to access the class method `is_effective_data(data)` safely
        module_class = type(self.current_module_widget)
        if hasattr(module_class, "is_effective_data"):
            return module_class.is_effective_data(data)
        return False

    # Drag & Drop functionality (Phase 2: Using ModuleDragDropManager)
    def drag_handle_enter(self, _event):
        """Handle mouse enter on drag handle - change cursor."""
        if not self._drag_manager.is_dragging:
            self._drag_manager.set_hover_cursor()

    def drag_handle_leave(self, _event):
        """Handle mouse leave on drag handle - restore cursor."""
        if not self._drag_manager.is_dragging:
            self._drag_manager.restore_cursor()

    def drag_handle_mouse_press(self, event):
        """Handle mouse press on drag handle - prepare for dragging."""
        if event.button() == Qt.LeftButton:
            global_pos = (event.globalPos().x(), event.globalPos().y())
            self._drag_manager.start_drag(self, global_pos)
            self._drag_manager.set_drag_cursor()
            event.accept()

    def drag_handle_mouse_move(self, event):
        """Handle mouse move on drag handle - start dragging if moved enough."""
        if not (event.buttons() & Qt.LeftButton):
            return

        global_pos = (event.globalPos().x(), event.globalPos().y())

        # Check if drag threshold crossed (manager handles 5px threshold)
        if self._drag_manager.update_drag(global_pos):
            # Drag just started - begin visual feedback
            self.start_drag()

        # Update module position to follow mouse during drag
        if self._drag_manager.is_dragging:
            self.update_drag_position(event.globalPos())

        event.accept()

    def drag_handle_mouse_release(self, event):
        """Handle mouse release on drag handle - end dragging."""
        if event.button() == Qt.LeftButton:
            if self._drag_manager.is_dragging:
                self.end_drag()
            else:
                # Was a click, not a drag - restore cursor
                self._drag_manager.restore_cursor()
            self._drag_manager.end_drag()
            event.accept()

    def start_drag(self):
        """Start the drag operation - visual feedback only (state managed by ModuleDragDropManager)."""
        # Enhanced visual feedback during dragging
        self.setWindowOpacity(0.8)
        self.raise_()

        # Add shadow effect for better visual feedback
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(2, 2)
        self.setGraphicsEffect(shadow)

        # Note: QSS doesn't support CSS transform, using graphical effect only

        # Notify parent that dragging started - try different parent levels
        parent = self.parent()
        while parent:
            if hasattr(parent, "module_drag_started"):
                parent.module_drag_started(self)
                break
            parent = parent.parent()

    def end_drag(self):
        """End the drag operation - visual cleanup only (state managed by ModuleDragDropManager)."""
        # Restore normal appearance
        self.setWindowOpacity(1.0)
        self.setGraphicsEffect(None)  # Remove shadow
        self._drag_manager.restore_cursor()

        # Restore original position (remove horizontal offset)
        if self.parent():
            # Get the correct position from the layout
            from oncutf.utils.shared.timer_manager import schedule_ui_update

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
        if not self._drag_manager.is_dragging:
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
