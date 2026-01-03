"""Cut line graphics item for slicing through edges.

This module defines QDMCutLine, a graphics item that renders a dashed
line following the mouse cursor. When the cut line intersects edges,
those edges are removed from the scene.

Usage:
    The cut line is activated by Ctrl+Left-Click and follows mouse
    movement until button release. All intersected edges are deleted.

Author:
    Michael Economou

Date:
    2025-12-11
"""

from __future__ import annotations

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QPainter, QPainterPath, QPen, QPolygonF
from PyQt5.QtWidgets import QGraphicsItem, QWidget


class QDMCutLine(QGraphicsItem):
    """Cutting line for removing edges by intersection.

    Renders as a white dashed line and tracks mouse movement.
    After release, edges intersecting any segment are deleted.

    Attributes:
        line_points: Sequential QPointF positions forming the line.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize cut line graphics item.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)

        self.line_points: list[QPointF] = []

        self._pen = QPen(Qt.white)
        self._pen.setWidthF(2.0)
        self._pen.setDashPattern([3, 3])

        self.setZValue(2)

    def boundingRect(self) -> QRectF:
        """Calculate bounding rectangle enclosing all points.

        Returns:
            QRectF containing all line points.
        """
        return self.shape().boundingRect()

    def shape(self) -> QPainterPath:
        """Build painter path from line points.

        Returns:
            QPainterPath connecting all points in sequence.
        """
        QPolygonF(self.line_points)

        if len(self.line_points) > 1:
            path = QPainterPath(self.line_points[0])
            for pt in self.line_points[1:]:
                path.lineTo(pt)
        else:
            path = QPainterPath(QPointF(0, 0))
            path.lineTo(QPointF(1, 1))

        return path

    def paint(self, painter: QPainter, _option, _widget=None) -> None:
        """Render the dashed cut line.

        Args:
            painter: QPainter for rendering.
            _option: Style options (unused).
            _widget: Target widget (unused).
        """
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(self._pen)

        poly = QPolygonF(self.line_points)
        painter.drawPolyline(poly)
