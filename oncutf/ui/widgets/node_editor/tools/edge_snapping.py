"""Socket snapping for easier edge connections.

This module provides EdgeSnapping, which automatically snaps edge endpoints
to nearby sockets during edge creation or rerouting. This improves the user
experience by making it easier to connect to small socket targets.

The snapping behavior:
    1. User drags edge near a socket
    2. If within snapping radius, endpoint jumps to socket center
    3. Socket highlights to show valid snap target
    4. On release, edge connects to snapped socket

Author:
    Michael Economou

Date:
    2025-12-11
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtCore import QPointF, QRectF

if TYPE_CHECKING:
    from PyQt5.QtGui import QMouseEvent

    from oncutf.ui.widgets.node_editor.graphics.socket import QDMGraphicsSocket
    from oncutf.ui.widgets.node_editor.graphics.view import QDMGraphicsView


class EdgeSnapping:
    """Manages socket snapping during edge operations.

    Detects nearby sockets and snaps edge endpoints to their centers,
    making precise connections easier for users.

    Attributes:
        graphics_view: QDMGraphicsView being used.
        graphics_scene: QDMGraphicsScene for item queries.
        edge_snapping_radius: Distance within which to snap to sockets.
    """

    def __init__(self, graphics_view: QDMGraphicsView, snapping_radius: float = 24) -> None:
        """Initialize edge snapping handler.

        Args:
            graphics_view: QDMGraphicsView to operate on.
            snapping_radius: Pixel radius for socket detection.
        """
        self.graphics_view = graphics_view
        self.graphics_scene = self.graphics_view.graphics_scene
        self.edge_snapping_radius = snapping_radius

    def getSnappedSocketItem(self, event: QMouseEvent) -> QDMGraphicsSocket | None:
        """Find socket to snap to from mouse event.

        Args:
            event: Mouse event containing cursor position.

        Returns:
            QDMGraphicsSocket to snap to, or None if no socket nearby.
        """
        scenepos = self.graphics_view.mapToScene(event.pos())
        graphics_socket, pos = self.getSnappedToSocketPosition(scenepos)
        return graphics_socket

    def getSnappedToSocketPosition(
        self, scenepos: QPointF
    ) -> tuple[QDMGraphicsSocket | None, QPointF]:
        """Find nearest socket and its center position.

        Searches within snapping radius for sockets and returns the
        nearest one with its scene position for snapping.

        Args:
            scenepos: Current position in scene coordinates.

        Returns:
            Tuple of (socket to snap to or None, snapped position).
        """
        from oncutf.ui.widgets.node_editor.graphics.socket import QDMGraphicsSocket

        scanrect = QRectF(
            scenepos.x() - self.edge_snapping_radius,
            scenepos.y() - self.edge_snapping_radius,
            self.edge_snapping_radius * 2,
            self.edge_snapping_radius * 2
        )
        items = self.graphics_scene.items(scanrect)
        items = list(filter(lambda socket_item: isinstance(socket_item, QDMGraphicsSocket), items))

        if len(items) == 0:
            return None, scenepos

        selected_item = items[0]
        if len(items) > 1:
            nearest = float('inf')
            for graphics_socket_item in items:
                socket_scene_position = graphics_socket_item.socket.node.get_socket_scene_position(graphics_socket_item.socket)
                qpdist = QPointF(*socket_scene_position) - scenepos
                dist = qpdist.x() * qpdist.x() + qpdist.y() * qpdist.y()
                if dist < nearest:
                    nearest = dist
                    selected_item = graphics_socket_item

        selected_item.isHighlighted = True

        calcpos = selected_item.socket.node.get_socket_scene_position(selected_item.socket)

        return selected_item, QPointF(*calcpos)
