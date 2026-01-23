"""Module: window_event_handler.py.

Author: Michael Economou
Date: 2026-01-01

Handler for window events and state management in MainWindow.
Handles Qt window events (resize, state change), geometry configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oncutf.ui.main_window import MainWindow

from PyQt5.QtCore import QEvent

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class WindowEventHandler:
    """Handles window events and state management."""

    def __init__(self, main_window: MainWindow) -> None:
        """Initialize handler with MainWindow reference.

        Args:
            main_window: Reference to the main window instance

        """
        self.main_window = main_window
        logger.debug("[WindowEventHandler] Initialized")

    # -------------------------------------------------------------------------
    # Qt Event Handlers
    # -------------------------------------------------------------------------

    def changeEvent(self, event: QEvent) -> None:
        """Handle window state changes (maximize, minimize, restore)."""
        super(self.main_window.__class__, self.main_window).changeEvent(event)

        if event.type() == QEvent.WindowStateChange:
            self._handle_window_state_change()

    def resizeEvent(self, event) -> None:
        """Handle window resize events to update splitter ratios for wide screens."""
        super(self.main_window.__class__, self.main_window).resizeEvent(event)

        # Only update splitters if UI is fully initialized and window is visible
        if (
            hasattr(self.main_window, "splitter_manager")
            and hasattr(self.main_window, "horizontal_splitter")
            and self.main_window.isVisible()
            and not self.main_window.isMinimized()
        ):
            # Get new window width
            new_width = self.main_window.width()

            # Use SplitterManager to update splitter sizes
            from oncutf.utils.shared.timer_manager import schedule_resize_adjust

            def update_splitters():
                """Update splitter proportions for new window width."""
                self.main_window.splitter_manager.update_splitter_sizes_for_window_width(new_width)

            # Schedule the update to avoid conflicts with other resize operations
            schedule_resize_adjust(update_splitters, 50)

            # Also trigger column adjustment when window resizes
            if hasattr(self.main_window, "file_table_view"):

                def trigger_column_adjustment():
                    """Trigger column width adjustment after splitter change."""
                    self.main_window.splitter_manager.trigger_column_adjustment_after_splitter_change()

                # Schedule column adjustment after splitter update
                schedule_resize_adjust(trigger_column_adjustment, 60)

    def _handle_window_state_change(self) -> None:
        """Handle maximize/restore geometry and file table refresh."""
        # Handle maximize: store appropriate geometry for restore
        if self.main_window.isMaximized() and not hasattr(self.main_window, "_restore_geometry"):
            current_geo = self.main_window.geometry()
            initial_size = self.main_window._initial_geometry.size()

            # Use current geometry if manually resized, otherwise use initial
            is_manually_resized = (
                abs(current_geo.width() - initial_size.width()) > 10
                or abs(current_geo.height() - initial_size.height()) > 10
            )

            self.main_window._restore_geometry = (
                current_geo if is_manually_resized else self.main_window._initial_geometry
            )
            geometry_kind = "manual" if is_manually_resized else "initial"
            logger.debug(
                "[MainWindow] Stored %s geometry for restore",
                geometry_kind,
            )

        # Handle restore: restore stored geometry
        elif not self.main_window.isMaximized() and hasattr(self.main_window, "_restore_geometry"):
            self.main_window.setGeometry(self.main_window._restore_geometry)
            delattr(self.main_window, "_restore_geometry")
            logger.debug("[MainWindow] Restored geometry")

        # Refresh file table after state change
        self._refresh_file_table_for_window_change()

    def _refresh_file_table_for_window_change(self) -> None:
        """Refresh file table after window state changes."""
        if (
            not hasattr(self.main_window, "file_table_view")
            or not self.main_window.file_table_view.model()
        ):
            return

        from oncutf.utils.shared.timer_manager import schedule_resize_adjust

        def refresh():
            """Refresh file table column widths after layout change."""
            # Reset manual column preference for auto-sizing
            if not getattr(self.main_window.file_table_view, "_recent_manual_resize", False):
                self.main_window.file_table_view._has_manual_preference = False

            # Use existing splitter logic for column sizing
            if hasattr(self.main_window, "horizontal_splitter"):
                sizes = self.main_window.horizontal_splitter.sizes()
                self.main_window.file_table_view.on_horizontal_splitter_moved(sizes[1], 1)

        schedule_resize_adjust(refresh, 25)

    # -------------------------------------------------------------------------
    # Window Configuration Delegates
    # -------------------------------------------------------------------------

    def _load_window_config(self) -> None:
        """Load and apply window configuration from config manager."""
        # Delegate to WindowConfigManager
        self.main_window.window_config_manager.load_window_config()

    def _set_smart_default_geometry(self) -> None:
        """Set smart default window geometry based on screen size."""
        config_mgr = self.main_window.window_config_manager
        if config_mgr is not None and hasattr(config_mgr, "set_smart_default_geometry"):
            config_mgr.set_smart_default_geometry()

    def _save_window_config(self) -> None:
        """Save current window state to config manager."""
        # Delegate to WindowConfigManager
        self.main_window.window_config_manager.save_window_config()

    def _apply_loaded_config(self) -> None:
        """Apply loaded configuration after UI is fully initialized."""
        # Delegate to WindowConfigManager
        self.main_window.window_config_manager.apply_loaded_config()

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def center_window(self) -> None:
        """Center window via Application Service."""
        self.main_window.app_service.center_window()
