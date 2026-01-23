"""Graphics scene for Qt rendering of the node graph.

This module defines QDMGraphicsScene, the Qt graphics scene that renders
the visual representation of the node graph. It draws the grid background
and emits signals for selection changes.

The scene supports:
    - Configurable grid with light and dark lines
    - Background color theming
    - Selection change signaling

Author:
    Michael Economou

Date:
    2025-12-11
"""

import math
from typing import TYPE_CHECKING

from PyQt5.QtCore import QLine, QRect, pyqtSignal as Signal
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtWidgets import QGraphicsScene, QWidget

from oncutf.ui.widgets.node_editor.themes.theme_engine import ThemeEngine

if TYPE_CHECKING:
    from oncutf.ui.widgets.node_editor.core.scene import Scene

class QDMGraphicsScene(QGraphicsScene):
    """Qt graphics scene rendering the node graph background.

    Draws a configurable grid pattern as the scene background and emits
    signals when item selection changes. Connects to the logical Scene
    for coordination between model and view.

    Signals:
        item_selected: Emitted when any item is selected.
        items_deselected: Emitted when selection is cleared.

    Attributes:
        scene: Reference to logical Scene model.
        gridSize: Pixel size of grid cells.
        gridSquares: Number of cells between major (dark) grid lines.

    """

    item_selected = Signal()
    items_deselected = Signal()

    def __init__(self, scene: "Scene", parent: QWidget | None = None):
        """Initialize graphics scene with grid.

        Args:
            scene: Logical Scene this graphics scene represents.
            parent: Optional parent widget.

        """
        super().__init__(parent)

        self.scene = scene

        self.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)

        self.gridSize = 20
        self.gridSquares = 5

        self.init_assets()
        self.setBackgroundBrush(self._color_background)

    def init_assets(self) -> None:
        """Initialize pens and colors from current theme."""
        theme = ThemeEngine.current_theme()

        self._color_background = theme.scene_background
        self._color_light = theme.scene_grid_light
        self._color_dark = theme.scene_grid_dark

        self._pen_light = QPen(self._color_light)
        self._pen_light.setWidth(1)
        self._pen_dark = QPen(self._color_dark)
        self._pen_dark.setWidth(2)

    def dragMoveEvent(self, event) -> None:
        """Accept drag move events for drop support.

        Args:
            event: Qt drag move event.

        """

    def set_graphics_scene_rect(self, width: int, height: int) -> None:
        """Configure scene dimensions centered at origin.

        Args:
            width: Total scene width in pixels.
            height: Total scene height in pixels.

        """
        self.setSceneRect(-width // 2, -height // 2, width, height)

    def drawBackground(self, painter: QPainter, rect: QRect) -> None:
        """Render grid background pattern.

        Draws light grid lines at gridSize intervals and dark lines
        at gridSize * gridSquares intervals.

        Args:
            painter: QPainter for drawing operations.
            rect: Visible rectangle area to draw.

        """
        super().drawBackground(painter, rect)

        left = math.floor(rect.left())
        right = math.ceil(rect.right())
        top = math.floor(rect.top())
        bottom = math.ceil(rect.bottom())

        first_left = left - (left % self.gridSize)
        first_top = top - (top % self.gridSize)

        lines_light, lines_dark = [], []
        for x in range(first_left, right, self.gridSize):
            if (x % (self.gridSize * self.gridSquares) != 0):
                lines_light.append(QLine(x, top, x, bottom))
            else:
                lines_dark.append(QLine(x, top, x, bottom))

        for y in range(first_top, bottom, self.gridSize):
            if (y % (self.gridSize * self.gridSquares) != 0):
                lines_light.append(QLine(left, y, right, y))
            else:
                lines_dark.append(QLine(left, y, right, y))

        painter.setPen(self._pen_light)
        try:
            painter.drawLines(*lines_light)
        except TypeError:
            painter.drawLines(lines_light)

        painter.setPen(self._pen_dark)
        try:
            painter.drawLines(*lines_dark)
        except TypeError:
            painter.drawLines(lines_dark)

    def reset_last_selected_states(self) -> None:
        """Clear internal selection state flags on all graphics items.

        Ensures proper detection of selection changes on next interaction.
        """
        for node in self.scene.nodes:
            node.graphics_node._last_selected_state = False
        for edge in self.scene.edges:
            edge.graphics_edge._last_selected_state = False
