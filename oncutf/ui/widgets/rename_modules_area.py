"""Module: rename_modules_area.py.

Author: Michael Economou
Date: 2025-05-27

rename_modules_area.py
Container widget that holds multiple RenameModuleWidget instances inside
scrollable area and provides fixed post-processing section and global
add/remove controls.
Designed to scale and support future drag & drop reordering.
Now supports ApplicationContext for optimized access patterns.
"""

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import (
    QFrame,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import oncutf.config
from oncutf.controllers.module_orchestrator import ModuleOrchestrator
from oncutf.modules.base_module import BaseRenameModule
from oncutf.ui.theme_manager import get_theme_manager
from oncutf.ui.widgets.rename_module_widget import RenameModuleWidget
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import schedule_scroll_adjust

logger = get_cached_logger(__name__)


class RenameModulesArea(QWidget):
    """Main area that contains all rename modules and final transformation widget.
    Supports scrolling for large numbers of modules.

    Phase 2 Refactoring:
    - Uses ModuleOrchestrator for module pipeline management
    - Maintains backward compatible API (get_all_data returns same structure)
    - Prepares for node editor by separating logic from UI

    Still supports ApplicationContext for optimized access patterns while maintaining
    backward compatibility with parent_window parameter.
    """

    updated = pyqtSignal()

    def __init__(self, parent: QWidget | None = None, parent_window: QWidget | None = None) -> None:
        """Initialize rename modules area with orchestrator and scroll container."""
        super().__init__(parent)
        self.parent_window = parent_window  # Keep for backward compatibility
        self.module_widgets: list[RenameModuleWidget] = []

        self.setObjectName("RenameModulesArea")

        # Initialize module orchestrator (Phase 2 refactoring)
        self.orchestrator = ModuleOrchestrator()
        logger.debug("[RenameModulesArea] ModuleOrchestrator initialized")

        # Initialize UnifiedRenameEngine
        self.rename_engine = None
        self._setup_rename_engine()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 2, 6, 2)  # Reduced bottom margin from 6 to 2
        main_layout.setSpacing(0)  # Control spacing manually like metadata dialog

        # No spacing at the top for testing - direct alignment with preview labels
        # main_layout.addSpacing(0)  # Commented out for zero spacing

        # Scrollable module container
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("rename_modules_scroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Add border to scroll area
        theme = get_theme_manager()
        border_color = theme.get_color("border")
        self.scroll_area.setStyleSheet(f"""
            QScrollArea#rename_modules_scroll {{
                border: 1px solid {border_color};
                border-radius: 4px;
                background-color: transparent;
            }}
        """)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("scroll_content_widget")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(2, 2, 2, 2)  # Further reduced for compactness
        self.scroll_layout.setSpacing(0)  # No spacing between modules - using margins instead

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        # Current theme (set before add_module)
        self.current_theme = oncutf.config.THEME_NAME

        self.add_module()  # Start with one by default

        # Use centralized timer manager for debouncing
        # This replaces the local QTimer with a managed timer that handles cleanup
        from oncutf.utils.shared.timer_manager import schedule_preview_update

        self._schedule_preview_update = schedule_preview_update
        self._preview_timer_id = f"preview_debounce_{id(self)}"

        # Drag & Drop state
        self.dragged_module = None
        self._drag_placeholder = None
        self.drop_indicators = []
        self.auto_scroll_timer = QTimer()
        self.auto_scroll_timer.setSingleShot(False)
        self.auto_scroll_timer.timeout.connect(self.handle_auto_scroll)
        self.scroll_direction = 0  # -1 for up, 1 for down, 0 for none

    def _get_app_context(self):
        """Get ApplicationContext with fallback to None."""
        try:
            from oncutf.core.application_context import get_app_context
            return get_app_context()
        except (ImportError, RuntimeError):
            # ApplicationContext not available or not ready yet
            return None

    def _on_module_updated(self):
        """Handle module updates with debouncing to prevent duplicates."""
        self._preview_timer_id = self._schedule_preview_update(
            self._emit_updated_signal, timer_id=self._preview_timer_id
        )

    def add_module(self):
        """Add a new RenameModuleWidget to the area.
        Now uses ApplicationContext-optimized approach when available.
        """
        # Always pass parent_window for stability
        module = RenameModuleWidget(parent=self, parent_window=self.parent_window)

        module.remove_requested.connect(lambda m=module: self.remove_module(m))
        module.updated.connect(lambda *_: self._on_module_updated())
        self.module_widgets.append(module)

        # Theme styling is now handled by the global theme engine

        # Remove separator creation - using margins instead
        self.scroll_layout.addWidget(module)

        # Update layout stretch to prevent modules from expanding
        self._update_layout_stretch()

        # Schedule scroll to bottom for new module
        schedule_scroll_adjust(lambda: self._scroll_to_bottom(), 50)

        self.updated.emit()

    def remove_module(self, module: RenameModuleWidget):
        """Remove specific module widget (keeps at least one module)."""
        # Prevent removal of the last module (keep at least one)
        if len(self.module_widgets) > 1 and module in self.module_widgets:
            # Remove separator handling since we're using margins now
            self.module_widgets.remove(module)
            self.scroll_layout.removeWidget(module)
            module.setParent(None)
            module.deleteLater()

            # Update layout stretch to maintain proper layout
            self._update_layout_stretch()

            # After removal, scroll to bottom to show remaining modules
            # Schedule scroll to bottom
            schedule_scroll_adjust(lambda: self._scroll_to_bottom(), 50)

            self.updated.emit()

    def remove_last_module(self):
        """Remove the last module (allows removal of all modules)."""
        if len(self.module_widgets) > 0:
            self.remove_module(self.module_widgets[-1])

    def _scroll_to_bottom(self):
        """Scroll to the bottom of the modules area."""
        scroll_bar = self.scroll_area.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

    def _update_layout_stretch(self):
        """Update stretch to prevent modules from expanding to fill container."""
        # Remove any existing stretch items first
        for i in reversed(range(self.scroll_layout.count())):
            item = self.scroll_layout.itemAt(i)
            if item and item.spacerItem():
                self.scroll_layout.removeItem(item)

        # Add stretch at the end to push modules to top
        self.scroll_layout.addStretch()

    def set_current_file_for_modules(self, file_item) -> None:
        """Set the current file for all SpecifiedText modules.

        Args:
            file_item: The FileItem object representing the currently selected file

        """
        for module_widget in self.module_widgets:
            if (
                hasattr(module_widget, "current_module_widget")
                and module_widget.current_module_widget
            ):
                # Check if this is a SpecifiedTextModule
                module_instance = module_widget.current_module_widget
                if hasattr(module_instance, "set_current_file"):
                    module_instance.set_current_file(file_item)

    def get_all_data(self) -> dict:
        """Collects data from all modules.
        Note: post_transform data is now handled by FinalTransformContainer.

        Phase 2: Uses orchestrator for better architecture but maintains
        backward compatible API.
        """
        # Sync orchestrator with current widget data
        self._sync_orchestrator_from_widgets()

        # Use orchestrator to collect data (new approach)
        return self.orchestrator.collect_all_data()

    def _sync_orchestrator_from_widgets(self) -> None:
        """Sync orchestrator state with current widgets.

        This bridge method maintains backward compatibility during Phase 2
        transition. Eventually widgets will be driven by orchestrator.
        """
        # Clear orchestrator and rebuild from widgets
        self.orchestrator.clear_all_modules()

        for widget in self.module_widgets:
            # Get widget data
            data = widget.to_dict()
            module_type = data.get("type", "")

            # Remove type from config (it's stored separately in orchestrator)
            config = data.copy()
            if "type" in config:
                del config["type"]

            # Add to orchestrator
            self.orchestrator.add_module(module_type, config)

    def get_all_module_instances(self) -> list[BaseRenameModule]:
        """Returns all current rename module widget instances.
        Useful for checking is_effective() per module.
        """
        logger.debug("[Preview] Modules: %s", self.module_widgets, extra={"dev_only": True})
        logger.debug(
            "[Preview] Effective check: %s",
            [m.is_effective() for m in self.module_widgets],
            extra={"dev_only": True},
        )

        return [
            m.current_module_widget
            for m in self.module_widgets
            if hasattr(m, "current_module_widget")
            and isinstance(m.current_module_widget, BaseRenameModule)
        ]

    def set_theme(self, theme: str):
        """Change the theme for the rename modules area.

        Args:
            theme: 'dark' or 'light'

        """
        self.current_theme = theme
        # Theme styling is now handled by the global theme engine
        logger.debug("[RenameModulesArea] Theme changed to: %s", theme, extra={"dev_only": True})

    def _setup_rename_engine(self):
        """Setup QtRenameEngine with signal support."""
        try:
            from oncutf.ui.adapters.qt_rename_engine import QtRenameEngine

            self.rename_engine = QtRenameEngine()
            logger.debug("[RenameModulesArea] QtRenameEngine initialized")
        except Exception as e:
            logger.error("[RenameModulesArea] Error initializing QtRenameEngine: %s", e)

    def _emit_updated_signal(self):
        """Emit the updated signal after debouncing."""
        logger.debug(
            "[RenameModulesArea] Timer timeout - emitting updated signal", extra={"dev_only": True}
        )
        self.updated.emit()
        # Trigger central preview update
        self._trigger_central_preview_update()

    def _trigger_central_preview_update(self):
        """Trigger central preview update."""
        try:
            if self.rename_engine:
                # Clear cache to force fresh preview
                self.rename_engine.clear_cache()
                logger.debug("[RenameModulesArea] Central preview update triggered")
        except Exception as e:
            logger.error("[RenameModulesArea] Error in central preview update: %s", e)

    def trigger_preview_update(self):
        """Public method to trigger preview update."""
        self._trigger_central_preview_update()

    # Drag & Drop functionality
    def module_drag_started(self, module):
        """Handle when a module starts being dragged."""
        self.dragged_module = module
        logger.debug(
            "[RenameModulesArea] Module drag started: %s", module, extra={"dev_only": True}
        )
        # Create a visual placeholder to reserve space while dragging
        self._create_drag_placeholder(module)
        # Optional: keep thin indicators for clarity
        self.create_drop_indicators()
        for indicator in self.drop_indicators:
            indicator.show()

    def module_drag_ended(self, module):
        """Handle when a module drag ends."""
        logger.debug("[RenameModulesArea] Module drag ended: %s", module, extra={"dev_only": True})

        # Stop auto-scrolling
        self.auto_scroll_timer.stop()
        self.scroll_direction = 0

        # Find drop position based on mouse position
        drop_index = self.find_drop_position()
        if drop_index is not None:
            self.reorder_module(module, drop_index)

        self.cleanup_drop_indicators()
        self._remove_drag_placeholder()
        self.dragged_module = None

    def create_drop_indicators(self):
        """Create visual indicators showing where the module can be dropped."""
        self.cleanup_drop_indicators()

        # Don't show indicator at the start if dragging the first module
        # Don't show indicator at the end if dragging the last module
        dragged_index = (
            self.module_widgets.index(self.dragged_module) if self.dragged_module else -1
        )

        # Create drop indicators between each module and at the ends
        for i in range(len(self.module_widgets) + 1):
            # Skip indicator at start if dragging first module
            if i == 0 and dragged_index == 0:
                continue
            # Skip indicator at end if dragging last module
            if i == len(self.module_widgets) and dragged_index == len(self.module_widgets) - 1:
                continue

            indicator = self.create_drop_indicator()
            self.drop_indicators.append(indicator)

            # Insert at the correct position in the layout
            insert_position = i * 2  # Account for modules taking odd positions
            if i < len(self.module_widgets):
                # Insert before the module at position i
                self.scroll_layout.insertWidget(insert_position, indicator)
            else:
                # Insert at the end
                self.scroll_layout.addWidget(indicator)

        # Ensure placeholder is at current module position initially
        self._position_drag_placeholder()

    def create_drop_indicator(self):
        """Create a single drop indicator widget."""
        indicator = QFrame()
        indicator.setObjectName("drop_indicator")
        indicator.setFixedHeight(4)  # Slightly thinner

        # Get hover color from theme and convert to rgba for alpha channel
        theme = get_theme_manager()
        hover_color = theme.colors.get("button_background_hover", "#3e5c76")

        indicator.setStyleSheet(
            f"""
            QFrame#drop_indicator {{
                background-color: {hover_color}CC;
                border: 1px solid {hover_color};
                border-radius: 2px;
                margin: 1px 8px;
            }}
            QFrame#drop_indicator:hover {{
                background-color: {hover_color};
            }}
        """
        )
        indicator.hide()  # Initially hidden
        return indicator

    def cleanup_drop_indicators(self):
        """Remove all drop indicators."""
        for indicator in self.drop_indicators:
            self.scroll_layout.removeWidget(indicator)
            indicator.setParent(None)
            indicator.deleteLater()
        self.drop_indicators.clear()

    def find_drop_position(self):
        """Find the drop position based on current mouse position."""
        if not self.dragged_module:
            return None

        # Get mouse position relative to scroll content
        mouse_pos = self.scroll_content.mapFromGlobal(QCursor.pos())

        # Find which module the mouse is over
        for i, module in enumerate(self.module_widgets):
            if module == self.dragged_module:
                continue

            module_rect = module.geometry()
            if mouse_pos.y() < module_rect.center().y():
                return i

        # If not over any module, drop at the end
        return len(self.module_widgets)

    def reorder_module(self, module, new_index):
        """Reorder a module to a new position."""
        if module not in self.module_widgets:
            return

        old_index = self.module_widgets.index(module)
        if old_index == new_index:
            return

        logger.debug(
            "[RenameModulesArea] Reordering module from %d to %d",
            old_index,
            new_index,
            extra={"dev_only": True},
        )

        # Remove module from old position
        self.module_widgets.pop(old_index)
        self.scroll_layout.removeWidget(module)

        # Insert module at new position
        self.module_widgets.insert(new_index, module)
        self.scroll_layout.insertWidget(new_index, module)

        # Update layout stretch
        self._update_layout_stretch()

        # Emit updated signal
        self.updated.emit()

        # Re-anchor placeholder below the moved module for a smooth visual
        self._position_drag_placeholder()

    def handle_drag_auto_scroll(self, global_pos):
        """Handle auto-scrolling during drag operations."""
        # Convert global position to scroll area coordinates
        scroll_local_pos = self.scroll_area.mapFromGlobal(global_pos)

        # Get scroll area geometry
        scroll_rect = self.scroll_area.rect()

        # Define scroll zones (top and bottom 30 pixels)
        scroll_zone = 30

        if scroll_local_pos.y() < scroll_zone:
            # Mouse near top - scroll up
            self.scroll_direction = -1
            if not self.auto_scroll_timer.isActive():
                self.auto_scroll_timer.start(50)  # Scroll every 50ms
        elif scroll_local_pos.y() > scroll_rect.height() - scroll_zone:
            # Mouse near bottom - scroll down
            self.scroll_direction = 1
            if not self.auto_scroll_timer.isActive():
                self.auto_scroll_timer.start(50)  # Scroll every 50ms
        else:
            # Mouse in middle area - stop scrolling
            self.scroll_direction = 0
            self.auto_scroll_timer.stop()

    def handle_auto_scroll(self):
        """Perform the actual auto-scrolling."""
        if self.scroll_direction == 0:
            self.auto_scroll_timer.stop()
            return

        scroll_bar = self.scroll_area.verticalScrollBar()
        current_value = scroll_bar.value()

        # Scroll speed (pixels per timer tick)
        # Adapt speed for smoother visual
        scroll_speed = 8 if self.scroll_direction != 0 else 0

        if self.scroll_direction == -1:  # Scroll up
            new_value = max(0, current_value - scroll_speed)
        else:  # Scroll down
            new_value = min(scroll_bar.maximum(), current_value + scroll_speed)

        scroll_bar.setValue(new_value)

        # Stop scrolling if we've reached the limits
        if new_value == scroll_bar.minimum() or new_value == scroll_bar.maximum():
            self.auto_scroll_timer.stop()

    # --- Drag placeholder helpers ---
    def _create_drag_placeholder(self, module: QWidget) -> None:
        """Create a placeholder widget with the same height as the module to preserve layout."""
        if self._drag_placeholder is not None:
            self._remove_drag_placeholder()
        placeholder = QFrame()
        placeholder.setObjectName("drag_placeholder")
        placeholder.setFixedHeight(module.height())

        # Get pressed color from theme for placeholder (lighter appearance)
        theme = get_theme_manager()
        pressed_color = theme.colors.get("button_background_pressed", "#748cab")

        placeholder.setStyleSheet(
            f"""
            QFrame#drag_placeholder {{
                background-color: {pressed_color}1F;
                border: 1px dashed {pressed_color}99;
                border-radius: 8px;
                margin: 2px 2px;
            }}
            """
        )
        self._drag_placeholder = placeholder
        # Insert right after the dragged module to start
        try:
            idx = self.module_widgets.index(module)
            self.scroll_layout.insertWidget(idx + 1, placeholder)
        except ValueError:
            self.scroll_layout.addWidget(placeholder)

    def _remove_drag_placeholder(self) -> None:
        """Remove drag placeholder widget from layout."""
        if self._drag_placeholder is not None:
            self.scroll_layout.removeWidget(self._drag_placeholder)
            self._drag_placeholder.setParent(None)
            self._drag_placeholder.deleteLater()
            self._drag_placeholder = None

    def _position_drag_placeholder(self) -> None:
        """Reposition placeholder near the dragged module for clearer drop target feeling."""
        if self._drag_placeholder is None or self.dragged_module is None:
            return
        # Place placeholder just after the dragged module for stability
        try:
            idx = self.module_widgets.index(self.dragged_module)
            # Ensure it's right after the dragged module in layout
            self.scroll_layout.removeWidget(self._drag_placeholder)
            self.scroll_layout.insertWidget(idx + 1, self._drag_placeholder)
        except ValueError:
            pass
