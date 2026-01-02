"""Module: ui_manager.py

Author: Michael Economou
Date: 2025-05-31
Updated: 2026-01-02

LEGACY: Thin delegator to new UI controllers.
Maintains backward compatibility while delegating to specialized controllers.

See oncutf/controllers/ui/ for the new architecture:
- WindowSetupController: Window properties, sizing
- LayoutController: Panels, splitters, layout
- SignalController: Signal connections
- ShortcutController: Keyboard shortcuts
"""

from typing import Any

from oncutf.controllers.ui import (
    LayoutController,
    ShortcutController,
    SignalController,
    WindowSetupController,
)
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class UIManager:
    """LEGACY: Thin delegator to new UI controllers.

    This class maintains backward compatibility by delegating to the new
    specialized controllers. New code should use the controllers directly.

    Controllers:
    - WindowSetupController: Window sizing, title, icon
    - LayoutController: Panel and splitter setup
    - SignalController: Signal connections
    - ShortcutController: Keyboard shortcuts
    """

    def __init__(self, parent_window: Any):
        """Initialize UIManager with parent window reference.

        Args:
            parent_window: The main application window
        """
        self.parent_window = parent_window

        # Initialize controllers
        self._window_controller = WindowSetupController(parent_window)
        self._layout_controller = LayoutController(parent_window)
        self._signal_controller = SignalController(parent_window)
        self._shortcut_controller = ShortcutController(parent_window)

        logger.debug("UIManager initialized (delegating to controllers)", extra={"dev_only": True})

    def setup_all_ui(self) -> None:
        """Setup all UI components in the correct order.

        Delegates to specialized controllers in sequence.
        """
        # Disable updates during setup to prevent flickering
        self.parent_window.setUpdatesEnabled(False)

        # Delegate to controllers in order
        self._window_controller.setup()
        self._layout_controller.setup()
        self._signal_controller.setup()
        self._shortcut_controller.setup()

        # Re-enable updates after UI is fully constructed
        self.parent_window.setUpdatesEnabled(True)
        logger.debug("All UI components setup completed", extra={"dev_only": True})

    # === Backward compatibility methods ===
    # These delegate to controllers for any code that calls UIManager directly

    def setup_main_window(self) -> None:
        """Backward compatibility: Delegate to WindowSetupController."""
        self._window_controller.setup()

    def setup_main_layout(self) -> None:
        """Backward compatibility: Delegate to LayoutController._setup_main_layout."""
        self._layout_controller._setup_main_layout()

    def setup_splitters(self) -> None:
        """Backward compatibility: Delegate to LayoutController._setup_splitters."""
        self._layout_controller._setup_splitters()

    def setup_left_panel(self) -> None:
        """Backward compatibility: Delegate to LayoutController._setup_left_panel."""
        self._layout_controller._setup_left_panel()

    def setup_center_panel(self) -> None:
        """Backward compatibility: Delegate to LayoutController._setup_center_panel."""
        self._layout_controller._setup_center_panel()

    def setup_right_panel(self) -> None:
        """Backward compatibility: Delegate to LayoutController._setup_right_panel."""
        self._layout_controller._setup_right_panel()

    def setup_bottom_layout(self) -> None:
        """Backward compatibility: Delegate to LayoutController._setup_bottom_layout."""
        self._layout_controller._setup_bottom_layout()

    def setup_footer(self) -> None:
        """Backward compatibility: Delegate to LayoutController._setup_footer."""
        self._layout_controller._setup_footer()

    def setup_signals(self) -> None:
        """Backward compatibility: Delegate to SignalController."""
        self._signal_controller.setup()

    def setup_shortcuts(self) -> None:
        """Backward compatibility: Delegate to ShortcutController."""
        self._shortcut_controller.setup()

    def restore_metadata_search_text(self) -> None:
        """Backward compatibility: Delegate to SignalController."""
        self._signal_controller.restore_metadata_search_text()

    def _calculate_optimal_window_size(self):
        """Backward compatibility: Delegate to WindowSetupController."""
        return self._window_controller._calculate_optimal_window_size()

    def _calculate_optimal_splitter_sizes(self, window_width: int):
        """Backward compatibility: Delegate to LayoutController."""
        return self._layout_controller._calculate_optimal_splitter_sizes(window_width)
