"""
Module: icons.py

Author: Michael Economou
Date: 2025-07-06

This utility module provides functions for creating and preparing icons,
typically using QIcon or related PyQt components. It may also include
logic for assigning icons based on file status or other contextual rules.
Used by oncutf to generate or modify visual indicators in the user interface.
Supports:
- Dynamic icon generation based on input conditions
- Theming or state-aware icon selection
- Compatibility with oncutf UI components
"""
from core.qt_imports import Qt, QColor, QPainter, QPen, QPixmap

# Initialize Logger
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

def create_colored_icon(
    fill_color: str,
    shape: str = "circle",
    size_x: int = 10,
    size_y: int = 10,
    border_color: str = None,
    border_thickness: int = 0
) -> QPixmap:
    """
    Creates a small colored shape (circle or rectangle) as a QPixmap icon.

    Args:
        fill_color (str): Fill color in hex (e.g. "#ff0000").
        shape (str): "circle" or "square". Default is "circle".
        size_x (int): Width of the shape. Default is 10.
        size_y (int): Height of the shape. Default is 10.
        border_color (str): Optional border color in hex (e.g. "#ffffff").
        border_thickness (int): Optional border thickness in pixels.

    Returns:
        QPixmap: A QPixmap with the desired shape and color.
    """
    pixmap = QPixmap(size_x, size_y)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    if border_color and border_thickness > 0:
        pen = QPen(QColor(border_color))
        pen.setWidth(border_thickness)
        painter.setPen(pen)
    else:
        painter.setPen(Qt.NoPen)

    painter.setBrush(QColor(fill_color))

    if shape == "square":
        painter.drawRect(0, 0, size_x, size_y)
    else:
        painter.drawEllipse(0, 0, size_x, size_y)

    painter.end()
    return pixmap

