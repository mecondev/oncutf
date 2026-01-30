"""Node insertion into edges by dropping.

This module provides EdgeIntersect, which handles automatic edge splitting
when a node is dropped onto an existing edge. The dropped node is inserted
between the previously connected nodes.

The insertion workflow:
    1. User drags a node over an existing edge
    2. Edge highlights to show valid drop target
    3. User releases node on edge
    4. Original edge is split into two edges through the new node

Author:
    Michael Economou

Date:
    2025-12-11
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtCore import QRectF

if TYPE_CHECKING:
    from oncutf.ui.widgets.node_editor.core.edge import Edge
    from oncutf.ui.widgets.node_editor.core.node import Node
    from oncutf.ui.widgets.node_editor.graphics.view import QDMGraphicsView


class EdgeIntersect:
    """Manages node insertion into edges by drag-and-drop.

    Detects when a dragged node overlaps an edge and handles the
    automatic reconnection when dropped.

    Attributes:
        graphics_scene: QDMGraphicsScene for item queries.
        graphics_view: QDMGraphicsView for coordinate mapping.
        draggedNode: Node currently being dragged.
        hoveredList: Graphics items under the dragged node.

    """

    def __init__(self, graphics_view: QDMGraphicsView) -> None:
        """Initialize edge intersection handler.

        Args:
            graphics_view: QDMGraphicsView to operate on.

        """
        self.graphics_scene = graphics_view.graphics_scene
        self.graphics_view = graphics_view
        self.draggedNode: Node | None = None
        self.hoveredList: list = []

    def enter_state(self, node: Node) -> None:
        """Begin tracking node drag for edge intersection.

        Args:
            node: Node being dragged.

        """
        self.hoveredList = []
        self.draggedNode = node

    def leave_state(self, scene_pos_x: float, scene_pos_y: float) -> None:
        """End drag tracking and process any intersection.

        Args:
            scene_pos_x: Final X position in scene coordinates.
            scene_pos_y: Final Y position in scene coordinates.

        """
        self.drop_node(self.draggedNode, scene_pos_x, scene_pos_y)
        self.draggedNode = None
        self.hoveredList = []

    def drop_node(self, node: Node, _scene_pos_x: float, _scene_pos_y: float) -> None:
        """Handle node drop and create edge split if intersecting.

        If node overlaps an edge, removes that edge and creates
        two new edges connecting through the dropped node.

        Args:
            node: Node being dropped.
            _scene_pos_x: Drop X position (unused).
            _scene_pos_y: Drop Y position (unused).

        """
        from oncutf.ui.widgets.node_editor.core.edge import Edge

        node_box = self.hot_zone_rect(node)

        edge = self.intersect(node_box)
        if edge is None:
            return

        if self.is_connected(node):
            return

        if edge.start_socket.is_output:
            socket_start = edge.start_socket
            socket_end = edge.end_socket
        else:
            socket_start = edge.end_socket
            socket_end = edge.start_socket

        edge_type = edge.edge_type
        edge.remove()
        self.graphics_view.graphics_scene.scene.history.store_history(
            "Delete existing edge", set_modified=True
        )

        new_node_socket_in = node.inputs[0]
        Edge(
            self.graphics_scene.scene,
            socket_start,
            new_node_socket_in,
            edge_type=edge_type,
        )

        new_node_socket_out = node.outputs[0]
        Edge(
            self.graphics_scene.scene,
            new_node_socket_out,
            socket_end,
            edge_type=edge_type,
        )

        self.graphics_view.graphics_scene.scene.history.store_history(
            "Created new edges by dropping node", set_modified=True
        )

    def hot_zone_rect(self, node: Node) -> QRectF:
        """Calculate bounding rectangle for node intersection testing.

        Args:
            node: Node to get bounds for.

        Returns:
            QRectF covering the node's area.

        """
        node_pos = node.graphics_node.scenePos()
        x = node_pos.x()
        y = node_pos.y()
        w = node.graphics_node.width
        h = node.graphics_node.height
        return QRectF(x, y, w, h)

    def update(self, _scene_pos_x: float, _scene_pos_y: float) -> None:
        """Update edge hover highlighting during drag.

        Args:
            _scene_pos_x: Current X position (unused).
            _scene_pos_y: Current Y position (unused).

        """
        rect = self.hot_zone_rect(self.draggedNode)
        graphics_items = self.graphics_scene.items(rect)

        for graphics_edge in self.hoveredList:
            graphics_edge.hovered = False
        self.hoveredList = []

        for graphics_item in graphics_items:
            if hasattr(graphics_item, "edge") and not self.draggedNode.has_connected_edge(
                graphics_item.edge
            ):
                self.hoveredList.append(graphics_item)
                graphics_item.hovered = True

    def intersect(self, node_box: QRectF) -> Edge | None:
        """Find first edge intersecting with node bounds.

        Args:
            node_box: Rectangle to test for intersection.

        Returns:
            First intersecting Edge, or None.

        """
        graphics_items = self.graphics_scene.items(node_box)
        for graphics_item in graphics_items:
            if hasattr(graphics_item, "edge") and not self.draggedNode.has_connected_edge(
                graphics_item.edge
            ):
                return graphics_item.edge
        return None

    def is_connected(self, node: Node) -> bool:
        """Check if node already has edge connections.

        Nodes without both inputs and outputs, or nodes with existing
        connections, are excluded from edge insertion.

        Args:
            node: Node to check.

        Returns:
            True if node has connections or lacks input/output.

        """
        if node.inputs == [] or node.outputs == []:
            return True

        return node.get_input() or node.get_outputs()
