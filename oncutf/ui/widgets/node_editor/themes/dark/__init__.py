"""Dark theme for the node editor.

This module provides DarkTheme, a theme with dark backgrounds and
light foreground colors suitable for low-light environments.

Classes:
    DarkTheme: Dark color scheme theme inheriting from BaseTheme.

Author:
    Michael Economou

Date:
    2025-12-11
"""

from typing import ClassVar

from PyQt5.QtGui import QColor, QFont

from oncutf.ui.widgets.node_editor.themes.base_theme import BaseTheme


class DarkTheme(BaseTheme):
    """Dark theme with dark backgrounds and light text.

    Provides a dark color palette optimized for extended use
    in low-light conditions. Uses muted backgrounds with
    high-contrast accent colors.

    Attributes:
        name: Theme identifier ("dark").
        display_name: Human-readable name ("Dark Theme").

    """

    # Theme metadata
    name = "dark"
    display_name = "Dark Theme"

    # Scene colors
    scene_background = QColor("#393939")
    scene_grid_light = QColor("#2f2f2f")
    scene_grid_dark = QColor("#292929")

    # Node colors
    node_background = QColor("#E3212121")
    node_title_background = QColor("#FF313131")
    node_title_color = QColor("#FFFFFF")
    node_border_default = QColor("#7F000000")
    node_border_selected = QColor("#FFFFA637")
    node_border_hovered = QColor("#FF37A6FF")
    node_border_error = QColor("#FFFF5555")

    # Edge colors
    edge_color_default = QColor("#001000")
    edge_color_selected = QColor("#00ff00")
    edge_color_dragging = QColor("#FFFFFF")

    # Socket colors
    socket_colors: ClassVar[list[QColor]] = [
        QColor("#FFFF7700"),  # Type 0 - Orange
        QColor("#FF52e220"),  # Type 1 - Green
        QColor("#FF0056a6"),  # Type 2 - Blue
        QColor("#FFa86db1"),  # Type 3 - Purple
        QColor("#FFb54747"),  # Type 4 - Red
        QColor("#FFdbe220"),  # Type 5 - Yellow
        QColor("#FF888888"),  # Type 6 - Gray
    ]

    # Fonts
    node_title_font = QFont("Ubuntu", 10)

    # Icon colors (for SVG icons in palette/listbox)
    icon_color = QColor("#FFCCCCCC")  # Light gray (not pure white)
