"""UI events package - contains UI-specific event handlers.

Author: Michael Economou
Date: 2026-01-22

This package contains event handlers that are UI concerns:
- Context menus (right-click menus)
- Other UI-specific event handling

Previously located in core/events, moved here as part of Phase A
boundary-first refactoring to eliminate core→ui violations.
"""

from oncutf.ui.events.context_menu import ContextMenuHandlers

__all__ = ["ContextMenuHandlers"]
