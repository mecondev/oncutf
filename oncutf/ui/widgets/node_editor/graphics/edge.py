"""Graphics representation of edges connecting sockets.

This module defines QDMGraphicsEdge, the Qt graphics item that renders
edge connections between nodes. It supports multiple path styles
(direct, bezier, square) and handles visual states including selection
and hover effects.

The graphics edge:
    - Renders paths between source and destination points
    - Supports pluggable path calculation classes
    - Shows selection and hover visual feedback
    - Integrates with theme system for colors

Author:
    Michael Economou

Date:
    2025-12-11
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QPainterPath, QPen
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsPathItem, QWidget

from oncutf.ui.widgets.node_editor.graphics.edge_path import (
    GraphicsEdgePathBezier,
    GraphicsEdgePathDirect,
    GraphicsEdgePathImprovedBezier,
    GraphicsEdgePathImprovedSharp,
    GraphicsEdgePathSquare,
)
from oncutf.ui.widgets.node_editor.themes.theme_engine import ThemeEngine

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QGraphicsSceneHoverEvent, QStyleOptionGraphicsItem

    from oncutf.ui.widgets.node_editor.core.edge import Edge
    from oncutf.ui.widgets.node_editor.graphics.edge_path import GraphicsEdgePathBase


class QDMGraphicsEdge(QGraphicsPathItem):
    """Qt graphics item rendering edge connections.

    Displays visual connection between two sockets using a configurable
    path style. Handles mouse interaction for selection and provides
    hover highlighting.

    Attributes:
        edge: Reference to logical Edge model.
        path_calculator: Instance computing the connection path.
        pos_source: [x, y] source position in scene coordinates.
        pos_destination: [x, y] destination position in scene coordinates.
        hovered: True while mouse hovers over this edge.
    """

    def __init__(self, edge: Edge, parent: QWidget | None = None):
        """Initialize graphics edge for a logical edge.

        Args:
            edge: Logical Edge this graphics item represents.
            parent: Optional parent widget.
        """
        super().__init__(parent)

        self.edge = edge

        self.path_calculator = self.determine_edge_path_class()(self)

        self._last_selected_state = False
        self.hovered = False

        self.pos_source = [0, 0]
        self.pos_destination = [200, 100]

        self.init_assets()
        self.init_ui()

    def init_ui(self) -> None:
        """Configure item flags for selection and interaction."""
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setZValue(-1)

    def init_assets(self) -> None:
        """Initialize pens for various visual states from theme."""
        theme = ThemeEngine.current_theme()

        self._color = self._default_color = theme.edge_color
        self._color_selected = theme.edge_selected_color
        self._color_hovered = theme.edge_hovered_color

        self._pen = QPen(self._color)
        self._pen_selected = QPen(self._color_selected)
        self._pen_dragging = QPen(self._color)
        self._pen_hovered = QPen(self._color_hovered)

        self._pen_dragging.setStyle(Qt.PenStyle.DashLine)
        self._pen.setWidthF(theme.edge_width)
        self._pen_selected.setWidthF(theme.edge_width)
        self._pen_dragging.setWidthF(theme.edge_width)
        self._pen_hovered.setWidthF(theme.edge_width + 2.0)

    def create_edge_path_calculator(self) -> GraphicsEdgePathBase:
        """Instantiate new path calculator based on edge type.

        Returns:
            GraphicsEdgePathBase subclass instance.
        """
        self.path_calculator = self.determine_edge_path_class()(self)
        return self.path_calculator

    def determine_edge_path_class(self) -> type[GraphicsEdgePathBase]:
        """Select path calculator class based on edge_type constant.

        Returns:
            Class type for computing edge path.
        """
        from oncutf.ui.widgets.node_editor.core.edge import (
            EDGE_TYPE_BEZIER,
            EDGE_TYPE_DIRECT,
            EDGE_TYPE_IMPROVED_BEZIER,
            EDGE_TYPE_IMPROVED_SHARP,
            EDGE_TYPE_SQUARE,
        )

        if self.edge.edge_type == EDGE_TYPE_BEZIER:
            return GraphicsEdgePathBezier
        if self.edge.edge_type == EDGE_TYPE_DIRECT:
            return GraphicsEdgePathDirect
        if self.edge.edge_type == EDGE_TYPE_SQUARE:
            return GraphicsEdgePathSquare
        if self.edge.edge_type == EDGE_TYPE_IMPROVED_SHARP:
            return GraphicsEdgePathImprovedSharp
        if self.edge.edge_type == EDGE_TYPE_IMPROVED_BEZIER:
            return GraphicsEdgePathImprovedBezier

        return GraphicsEdgePathImprovedBezier

    def make_unselectable(self) -> None:
        """Disable selection and hover events.

        Used for temporary drag edges that should not be interactive.
        """
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setAcceptHoverEvents(False)

    def change_color(self, color) -> None:
        """Update edge color.

        Args:
            color: QColor instance or hex string like '#00ff00'.
        """
        from PyQt5.QtGui import QColor

        self._color = QColor(color) if isinstance(color, str) else color
        self._pen = QPen(self._color)
        self._pen.setWidthF(ThemeEngine.current_theme().edge_width)

    def set_color_from_sockets(self) -> bool:
        """Set edge color based on connected socket types.

        Uses socket color if both endpoints have matching types.

        Returns:
            True if color was set, False if socket types differ.
        """
        socket_type_start = self.edge.start_socket.socket_type
        socket_type_end = self.edge.end_socket.socket_type
        if socket_type_start != socket_type_end:
            return False
        self.change_color(self.edge.start_socket.graphics_socket.get_socket_color(socket_type_start))
        return True

    def on_selected(self) -> None:
        """Emit selection signal to scene when selected."""
        self.edge.scene.graphics_scene.item_selected.emit()

    def do_select(self, new_state: bool = True) -> None:
        """Programmatically select or deselect this edge.

        Args:
            new_state: True to select, False to deselect.
        """
        self.setSelected(new_state)
        self._last_selected_state = new_state
        if new_state:
            self.on_selected()

    def mouseReleaseEvent(self, event) -> None:
        """Handle selection changes on mouse release.

        Args:
            event: Qt mouse release event.
        """
        super().mouseReleaseEvent(event)
        if self._last_selected_state != self.isSelected():
            self.edge.scene.graphics_scene.reset_last_selected_states()
            self._last_selected_state = self.isSelected()
            self.on_selected()

    def hoverEnterEvent(self, _event: QGraphicsSceneHoverEvent) -> None:
        """Enable hover highlight when mouse enters.

        Args:
            _event: Qt hover event (unused).
        """
        self.hovered = True
        self.update()

    def hoverLeaveEvent(self, _event: QGraphicsSceneHoverEvent) -> None:
        """Disable hover highlight when mouse leaves.

        Args:
            _event: Qt hover event (unused).
        """
        self.hovered = False
        self.update()

    def set_source(self, x: float, y: float) -> None:
        """Set source endpoint position.

        Args:
            x: Horizontal position in scene coordinates.
            y: Vertical position in scene coordinates.
        """
        self.pos_source = [x, y]

    def set_destination(self, x: float, y: float) -> None:
        """Set destination endpoint position.

        Args:
            x: Horizontal position in scene coordinates.
            y: Vertical position in scene coordinates.
        """
        self.pos_destination = [x, y]

    def boundingRect(self) -> QRectF:
        """Calculate bounding rectangle from endpoints.

        Returns:
            QRectF enclosing the edge path.
        """
        return self.shape().boundingRect()

    def shape(self) -> QPainterPath:
        """Return selectable shape area.

        Returns:
            QPainterPath used for hit detection.
        """
        return self.calc_path()

    def paint(
        self,
        painter,
        _option: QStyleOptionGraphicsItem,
        _widget=None,
    ) -> None:
        """Render the edge path with appropriate pen.

        Selects pen based on selection and hover state.

        Args:
            painter: QPainter for rendering.
            _option: Style options (unused).
            _widget: Target widget (unused).
        """
        self.setPath(self.calc_path())

        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Draw hover highlight
        if self.hovered and self.edge.end_socket is not None:
            painter.setPen(self._pen_hovered)
            painter.drawPath(self.path())

        # Draw edge
        if self.edge.end_socket is None:
            painter.setPen(self._pen_dragging)
        else:
            painter.setPen(self._pen if not self.isSelected() else self._pen_selected)

        painter.drawPath(self.path())

    def intersects_with(self, p1: QPointF, p2: QPointF) -> bool:
        """Test if edge path intersects a line segment.

        Used by cutline to determine if edge should be deleted.

        Args:
            p1: First endpoint of line segment.
            p2: Second endpoint of line segment.

        Returns:
            True if intersection exists, False otherwise.
        """
        cutpath = QPainterPath(p1)
        cutpath.lineTo(p2)
        path = self.calc_path()
        return cutpath.intersects(path)

    def calc_path(self) -> QPainterPath:
        """Compute edge path using current path calculator.

        Returns:
            QPainterPath from source to destination.
        """
        return self.path_calculator.calc_path()
