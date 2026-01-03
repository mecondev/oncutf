"""Light theme for the node editor.

This module provides LightTheme, a theme with light backgrounds and
dark foreground colors suitable for well-lit environments.

Classes:
    LightTheme: Light color scheme theme inheriting from BaseTheme.

Author:
    Michael Economou

Date:
    2025-12-11
"""

from PyQt5.QtGui import QColor, QFont

from oncutf.ui.widgets.node_editor.themes.base_theme import BaseTheme


class LightTheme(BaseTheme):
    """Light theme with light backgrounds and dark text.

    Provides a light color palette optimized for well-lit
    environments. Uses bright backgrounds with saturated
    accent colors for good contrast.

    Attributes:
        name: Theme identifier ("light").
        display_name: Human-readable name ("Light Theme").
    """

    # Theme metadata
    name = "light"
    display_name = "Light Theme"

    # Scene colors
    scene_background = QColor("#e8e8e8")
    scene_grid_light = QColor("#d0d0d0")
    scene_grid_dark = QColor("#b8b8b8")

    # Node colors
    node_background = QColor("#F5FFFFFF")
    node_title_background = QColor("#FFd0d0d0")
    node_title_color = QColor("#FF222222")
    node_border_default = QColor("#7F000000")
    node_border_selected = QColor("#FFFF8C00")
    node_border_hovered = QColor("#FF2196F3")
    node_border_error = QColor("#FFCC0000")

    # Edge colors
    edge_color_default = QColor("#FF404040")
    edge_color_selected = QColor("#FF00aa00")
    edge_color_dragging = QColor("#FF666666")

    # Socket colors
    socket_colors = [
        QColor("#FFFF8C00"),  # Type 0 - Orange
        QColor("#FF4CAF50"),  # Type 1 - Green
        QColor("#FF2196F3"),  # Type 2 - Blue
        QColor("#FF9C27B0"),  # Type 3 - Purple
        QColor("#FFF44336"),  # Type 4 - Red
        QColor("#FFFFEB3B"),  # Type 5 - Yellow
        QColor("#FF9E9E9E"),  # Type 6 - Gray
    ]

    # Fonts
    node_title_font = QFont("Ubuntu", 10)

    # Icon colors (for SVG icons in palette/listbox)
    icon_color = QColor("#FF555555")  # Dark gray for light theme
