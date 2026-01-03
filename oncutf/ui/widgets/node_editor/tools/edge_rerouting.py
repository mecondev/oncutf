"""Edge rerouting for reconnecting existing edges.

This module provides EdgeRerouting, which allows users to reconnect
existing edges by Ctrl+clicking on a socket and dragging to a new
destination socket.

The rerouting workflow:
    1. User Ctrl+clicks on a socket with existing connections
    2. Original edges are hidden and dashed preview edges appear
    3. User drags to target socket
    4. On release, edges reconnect to new socket or revert if invalid

Author:
    Michael Economou

Date:
    2025-12-11
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oncutf.ui.widgets.node_editor.core.edge import Edge
    from oncutf.ui.widgets.node_editor.core.socket import Socket
    from oncutf.ui.widgets.node_editor.graphics.view import QDMGraphicsView

logger = logging.getLogger(__name__)


class EdgeRerouting:
    """Manages rerouting of existing edge connections.

    Allows users to reroute edges by Ctrl+clicking on a connected socket
    and dragging to a new target socket. Preview edges show the potential
    new connections during drag.

    Attributes:
        graphics_view: QDMGraphicsView being used.
        start_socket: Socket where rerouting started.
        rerouting_edges: Temporary preview edges during rerouting.
        is_rerouting: Whether rerouting operation is active.
        first_mb_release: Flag for first mouse button release detection.
    """

    def __init__(self, graphics_view: QDMGraphicsView) -> None:
        """Initialize edge rerouting handler.

        Args:
            graphics_view: QDMGraphicsView to operate on.
        """
        self.graphics_view = graphics_view
        self.start_socket: Socket | None = None
        self.rerouting_edges: list[Edge] = []
        self.is_rerouting: bool = False
        self.first_mb_release: bool = False

    def get_edge_class(self) -> type[Edge]:
        """Get the Edge class for creating preview edges.

        Returns:
            Edge class from the scene.
        """
        return self.graphics_view.graphics_scene.scene.get_edge_class()

    def get_affected_edges(self) -> list[Edge]:
        """Get all edges connected to the start socket.

        Returns:
            List of edges that will be affected by rerouting.
        """
        if self.start_socket is None:
            return []
        return self.start_socket.edges.copy()

    def set_affected_edges_visible(self, visibility: bool = True) -> None:
        """Control visibility of affected edges during rerouting.

        Args:
            visibility: True to show edges, False to hide them.
        """
        for edge in self.get_affected_edges():
            if visibility:
                edge.graphics_edge.show()
            else:
                edge.graphics_edge.hide()

    def reset_rerouting(self) -> None:
        """Reset rerouting state to default values."""
        self.is_rerouting = False
        self.start_socket = None
        self.first_mb_release = False

    def clear_rerouting_edges(self) -> None:
        """Remove temporary preview edges from the scene."""
        while self.rerouting_edges:
            edge = self.rerouting_edges.pop()
            edge.remove()

    def update_scene_pos(self, x: float, y: float) -> None:
        """Update preview edge endpoints during drag.

        Called from mouse move event to track cursor position.

        Args:
            x: Current X position in scene coordinates.
            y: Current Y position in scene coordinates.
        """
        if self.is_rerouting:
            for edge in self.rerouting_edges:
                if edge and edge.graphics_edge:
                    edge.graphics_edge.set_destination(x, y)
                    edge.graphics_edge.update()

    def start_rerouting(self, socket: Socket) -> None:
        """Begin rerouting operation from a socket.

        Hides original edges and creates preview edges for visual feedback.

        Args:
            socket: Socket to start rerouting from.
        """
        self.is_rerouting = True
        self.start_socket = socket

        self.set_affected_edges_visible(visibility=False)

        start_position = self.start_socket.node.get_socket_scene_position(self.start_socket)

        edge_class = self.get_edge_class()
        for edge in self.get_affected_edges():
            other_socket = edge.get_other_socket(self.start_socket)

            new_edge = edge_class(self.start_socket.node.scene, edge_type=edge.edge_type)
            new_edge.start_socket = other_socket
            new_edge.graphics_edge.set_source(*other_socket.node.get_socket_scene_position(other_socket))
            new_edge.graphics_edge.set_destination(*start_position)
            new_edge.graphics_edge.update()
            self.rerouting_edges.append(new_edge)

    def stop_rerouting(self, target: Socket | None = None) -> None:
        """Complete or cancel the rerouting operation.

        Validates potential connections and reconnects edges to the target
        socket. Invalid edges remain connected to their original sockets.

        Args:
            target: Socket to connect to, or None to cancel rerouting.
        """
        if self.start_socket is not None:
            # Reset start socket highlight
            self.start_socket.graphics_socket.isHighlighted = False

        # Collect all affected (node, edge) tuples
        affected_nodes = []

        if target is None or target == self.start_socket:
            # Canceling - no change
            self.set_affected_edges_visible(visibility=True)
        else:
            # Validate edges before doing anything
            valid_edges = self.get_affected_edges()
            invalid_edges = []

            for edge in self.get_affected_edges():
                start_sock = edge.get_other_socket(self.start_socket)
                if not edge.validate_edge(start_sock, target):
                    # Not valid edge
                    invalid_edges.append(edge)

            # Remove the invalidated edges from the list
            for invalid_edge in invalid_edges:
                valid_edges.remove(invalid_edge)

            # Reconnect to new socket
            self.set_affected_edges_visible(visibility=True)

            for edge in valid_edges:
                for node in [edge.start_socket.node, edge.end_socket.node]:
                    if node not in [n for n, e in affected_nodes]:
                        affected_nodes.append((node, edge))

                if target.is_input:
                    target.remove_all_edges(silent=True)

                if edge.end_socket == self.start_socket:
                    edge.end_socket = target
                else:
                    edge.start_socket = target

                edge.update_positions()

        # Hide rerouting edges
        self.clear_rerouting_edges()

        # Send notifications for all affected nodes
        for affected_node, edge in affected_nodes:
            affected_node.on_edge_connection_changed(edge)
            if edge.start_socket in affected_node.inputs:
                affected_node.on_input_changed(edge.start_socket)
            if edge.end_socket in affected_node.inputs:
                affected_node.on_input_changed(edge.end_socket)

        # Store history stamp
        if self.start_socket:
            self.start_socket.node.scene.history.store_history("Rerouted edges", set_modified=True)

        # Reset variables
        self.reset_rerouting()
