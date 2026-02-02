"""Viewport button specifications for the FileTable header.

Author: Michael Economou
Date: 2026-01-10
"""

from typing import NamedTuple


class ViewportSpec(NamedTuple):
    """Specification for a viewport button."""

    id: str  # Unique identifier
    tooltip: str  # Tooltip text
    icon_name: str  # Icon name for get_menu_icon()
    shortcut: str  # Keyboard shortcut (e.g., "F1")


# Viewport button specifications - single source of truth
VIEWPORT_SPECS: list[ViewportSpec] = [
    ViewportSpec("details", "Details view", "list", "F1"),
    ViewportSpec("thumbs", "Thumbnail view", "grid_view", "F2"),
]

# Layout constants (logical pixels - Qt scales for high-DPI)
VIEWPORT_BUTTON_SIZE = 20
VIEWPORT_BUTTON_SPACING = 4
FILES_HEADER_HEIGHT = 24
