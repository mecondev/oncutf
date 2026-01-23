"""Path calculators for different edge rendering styles.

This module defines classes that compute QPainterPath objects for drawing
edge connections between nodes. Multiple path styles are supported:

- Direct: Straight line connection
- Bezier: Smooth cubic Bezier curve
- Square: Right-angle stepped connection
- ImprovedSharp: Horizontal segments with corners
- ImprovedBezier: Adaptive Bezier with horizontal ends

Each path calculator takes source and destination positions and produces
a QPainterPath suitable for rendering by QDMGraphicsEdge.

Author:
    Michael Economou

Date:
    2025-12-11
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QPainterPath

if TYPE_CHECKING:
    from oncutf.ui.widgets.node_editor.graphics.edge import QDMGraphicsEdge

# Edge path constants
EDGE_CP_ROUNDNESS = 100  # Bezier control point distance on the line
WEIGHT_SOURCE = 0.2  # Factor for square edge midpoint between start and end
EDGE_IBCP_ROUNDNESS = 75  # Scale curvature with distance
NODE_DISTANCE = 12
EDGE_CURVATURE = 2


class GraphicsEdgePathBase:
    """Base class for edge path calculation.

    Subclasses implement calcPath() to produce specific path styles.

    Attributes:
        owner: QDMGraphicsEdge this calculator belongs to.

    """

    def __init__(self, owner: QDMGraphicsEdge):
        """Initialize path calculator with owner edge.

        Args:
            owner: QDMGraphicsEdge that owns this calculator.

        """
        self.owner = owner

    def calc_path(self) -> QPainterPath | None:
        """Calculate path from source to destination.

        Override in subclasses to implement specific path styles.

        Returns:
            QPainterPath for rendering, or None if not implemented.

        """
        return None


class GraphicsEdgePathDirect(GraphicsEdgePathBase):
    """Straight line path between source and destination."""

    def calc_path(self) -> QPainterPath:
        """Calculate direct line connection.

        Returns:
            QPainterPath with single line segment.

        """
        path = QPainterPath(
            QPointF(self.owner.pos_source[0], self.owner.pos_source[1])
        )
        path.lineTo(self.owner.pos_destination[0], self.owner.pos_destination[1])
        return path


class GraphicsEdgePathBezier(GraphicsEdgePathBase):
    """Cubic Bezier curve path with adaptive control points."""

    def calc_path(self) -> QPainterPath:
        """Calculate cubic Bezier curve with two control points.

        Adjusts control points based on socket positions and
        relative locations of start and end points.

        Returns:
            QPainterPath with smooth Bezier curve.

        """
        s = self.owner.pos_source
        d = self.owner.pos_destination
        dist = (d[0] - s[0]) * 0.5

        cpx_s = +dist
        cpx_d = -dist
        cpy_s = 0
        cpy_d = 0

        if self.owner.edge.start_socket is not None:
            ssin = self.owner.edge.start_socket.is_input
            ssout = self.owner.edge.start_socket.is_output

            if (s[0] > d[0] and ssout) or (s[0] < d[0] and ssin):
                cpx_d *= -1
                cpx_s *= -1

                cpy_d = (
                    (s[1] - d[1])
                    / math.fabs((s[1] - d[1]) if (s[1] - d[1]) != 0 else 0.00001)
                ) * EDGE_CP_ROUNDNESS
                cpy_s = (
                    (d[1] - s[1])
                    / math.fabs((d[1] - s[1]) if (d[1] - s[1]) != 0 else 0.00001)
                ) * EDGE_CP_ROUNDNESS

        path = QPainterPath(
            QPointF(self.owner.pos_source[0], self.owner.pos_source[1])
        )
        path.cubicTo(
            s[0] + cpx_s,
            s[1] + cpy_s,
            d[0] + cpx_d,
            d[1] + cpy_d,
            self.owner.pos_destination[0],
            self.owner.pos_destination[1],
        )

        return path


class GraphicsEdgePathSquare(GraphicsEdgePathBase):
    """Square-cornered path with three line segments."""

    def __init__(self, *args, handle_weight: float = 0.5, **kwargs):
        """Initialize square path calculator.

        Args:
            *args: Passed to base class.
            handle_weight: Position of vertical segment (0.0 to 1.0).
            **kwargs: Passed to base class.

        """
        super().__init__(*args, **kwargs)
        self.rand = None
        self.handle_weight = handle_weight

    def calc_path(self) -> QPainterPath:
        """Calculate right-angle stepped path.

        Creates path with horizontal-vertical-horizontal segments.

        Returns:
            QPainterPath with three connected line segments.

        """
        s = self.owner.pos_source
        d = self.owner.pos_destination

        mid_x = s[0] + ((d[0] - s[0]) * self.handle_weight)

        path = QPainterPath(QPointF(s[0], s[1]))
        path.lineTo(mid_x, s[1])
        path.lineTo(mid_x, d[1])
        path.lineTo(d[0], d[1])

        return path


class GraphicsEdgePathImprovedSharp(GraphicsEdgePathBase):
    """Sharp-cornered path with horizontal exit segments."""

    def calc_path(self) -> QPainterPath:
        """Calculate sharp path with horizontal ends.

        Creates path that exits horizontally from both sockets
        before connecting with straight line.

        Returns:
            QPainterPath with horizontal segments and diagonal.

        """
        sx, sy = self.owner.pos_source
        dx, dy = self.owner.pos_destination
        distx, disty = dx - sx, dy - sy
        dist = math.sqrt(distx * distx + disty * disty)

        # Is start/end socket on left side?
        sleft = self.owner.edge.start_socket.position <= 3

        # If drag edge started from input socket, connect to output socket
        eleft = self.owner.edge.start_socket.position > 3

        if self.owner.edge.end_socket is not None:
            eleft = self.owner.edge.end_socket.position <= 3

        node_sdist = (-NODE_DISTANCE) if sleft else NODE_DISTANCE
        node_edist = (-NODE_DISTANCE) if eleft else NODE_DISTANCE

        path = QPainterPath(QPointF(sx, sy))

        if abs(dist) > NODE_DISTANCE:
            path.lineTo(sx + node_sdist, sy)
            path.lineTo(dx + node_edist, dy)

        path.lineTo(dx, dy)

        return path


class GraphicsEdgePathImprovedBezier(GraphicsEdgePathBase):
    """Bezier curve path with horizontal exit segments."""

    def calc_path(self) -> QPainterPath:
        """Calculate Bezier path with adaptive curvature.

        Creates path with horizontal segments near sockets and
        smooth Bezier curve in between. Curvature adapts to distance.

        Returns:
            QPainterPath with horizontal ends and curved middle.

        """
        sx, sy = self.owner.pos_source
        dx, dy = self.owner.pos_destination
        distx, disty = dx - sx, dy - sy
        dist = math.sqrt(distx * distx + disty * disty)

        # Is start/end socket on left side?
        sleft = self.owner.edge.start_socket.position <= 3

        # If drag edge started from input socket, connect to output socket
        eleft = self.owner.edge.start_socket.position > 3

        if self.owner.edge.end_socket is not None:
            eleft = self.owner.edge.end_socket.position <= 3

        path = QPainterPath(QPointF(sx, sy))

        if abs(dist) > NODE_DISTANCE:
            curvature = max(
                EDGE_CURVATURE, (EDGE_CURVATURE * abs(dist)) / EDGE_IBCP_ROUNDNESS
            )

            node_sdist = (-NODE_DISTANCE) if sleft else NODE_DISTANCE
            node_edist = (-NODE_DISTANCE) if eleft else NODE_DISTANCE

            path.lineTo(sx + node_sdist, sy)

            path.cubicTo(
                QPointF(sx + node_sdist * curvature, sy),
                QPointF(dx + node_edist * curvature, dy),
                QPointF(dx + node_edist, dy),
            )

            path.lineTo(dx + node_edist, dy)

        path.lineTo(dx, dy)

        return path
