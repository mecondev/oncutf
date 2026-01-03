"""Socket connection points for node inputs and outputs.

This module defines the Socket class representing connection endpoints on nodes.
Sockets serve as anchors for edges, enabling visual connections between nodes
in the graph. Each socket has a type (affecting visual appearance and
connection compatibility) and can be configured for single or multiple
simultaneous connections.

Position Constants:
    LEFT_TOP, LEFT_CENTER, LEFT_BOTTOM: Input socket positions.
    RIGHT_TOP, RIGHT_CENTER, RIGHT_BOTTOM: Output socket positions.

Author:
    Michael Economou

Date:
    2025-12-11
"""

from enum import IntEnum
from typing import TYPE_CHECKING

from oncutf.ui.widgets.node_editor.core.serializable import Serializable

if TYPE_CHECKING:
    from oncutf.ui.widgets.node_editor.core.edge import Edge
    from oncutf.ui.widgets.node_editor.core.node import Node
    from oncutf.ui.widgets.node_editor.graphics.socket import QDMGraphicsSocket


class SocketPosition(IntEnum):
    """Socket position constants for node layout.

    IntEnum provides type safety while maintaining backward compatibility
    with integer comparisons and serialization.
    """

    LEFT_TOP = 1
    LEFT_CENTER = 2
    LEFT_BOTTOM = 3
    RIGHT_TOP = 4
    RIGHT_CENTER = 5
    RIGHT_BOTTOM = 6


# Backward compatibility: expose as module-level constants
LEFT_TOP = SocketPosition.LEFT_TOP
LEFT_CENTER = SocketPosition.LEFT_CENTER
LEFT_BOTTOM = SocketPosition.LEFT_BOTTOM
RIGHT_TOP = SocketPosition.RIGHT_TOP
RIGHT_CENTER = SocketPosition.RIGHT_CENTER
RIGHT_BOTTOM = SocketPosition.RIGHT_BOTTOM


class Socket(Serializable):
    """Connection point on a node for attaching edges.

    Sockets are the interface between nodes and edges. Input sockets receive
    data from connected output sockets, while output sockets send data out.
    Each socket maintains a list of connected edges and manages connection
    lifecycle (add/remove edges).

    The socket type determines visual appearance (color) and can be used for
    type-checking connections. Multi-edge sockets allow multiple simultaneous
    connections; single-edge sockets disconnect existing edges when a new
    connection is made.

    Attributes:
        node: Parent node that owns this socket.
        index: Zero-based index among sockets on the same side.
        position: Position constant (LEFT_TOP, RIGHT_CENTER, etc.).
        socket_type: Integer type identifier affecting visual color.
        is_multi_edges: True if multiple edges can connect simultaneously.
        is_input: True for input sockets (left side).
        is_output: True for output sockets (right side).
        edges: List of currently connected Edge instances.
        graphics_socket: Associated QDMGraphicsSocket for visual representation.
        count_on_this_node_side: Total socket count on this side for layout.

    Class Attributes:
        _graphics_socket_class: Graphics class for socket visualization (set at init).
    """

    _graphics_socket_class: type["QDMGraphicsSocket"] | None = None

    def __init__(
        self,
        node: "Node",
        index: int = 0,
        position: int = LEFT_TOP,
        socket_type: int = 1,
        multi_edges: bool = True,
        count_on_this_node_side: int = 1,
        is_input: bool = False,
    ):
        """Create a socket attached to a node.

        Args:
            node: Parent node that will contain this socket.
            index: Socket index on this side of the node (0-based).
            position: Position constant determining socket placement.
            socket_type: Type identifier for visual styling and compatibility.
            multi_edges: Allow multiple simultaneous edge connections.
            count_on_this_node_side: Total sockets on this side for layout calc.
            is_input: True for input socket, False for output socket.
        """
        super().__init__()

        self.node = node
        self.position = position
        self.index = index
        self.socket_type = socket_type
        self.count_on_this_node_side = count_on_this_node_side
        self.is_multi_edges = multi_edges
        self.is_input = is_input
        self.is_output = not self.is_input

        self.graphics_socket: QDMGraphicsSocket = self.__class__._graphics_socket_class(self)
        self.set_socket_position()

        self.edges: list[Edge] = []

    def __str__(self) -> str:
        """Return human-readable socket representation.

        Returns:
            Format: <Socket #index ME|SE ID> where ME=multi-edge, SE=single-edge.
        """
        edge_type = "ME" if self.is_multi_edges else "SE"
        return f"<Socket #{self.index} {edge_type} {hex(id(self))[2:5]}..{hex(id(self))[-3:]}>"

    def delete(self) -> None:
        """Remove socket from scene and clean up graphics resources.

        Detaches the graphics socket from its parent and removes it from
        the graphics scene. Should be called before discarding the socket.
        """
        self.graphics_socket.setParentItem(None)
        self.node.scene.graphics_scene.removeItem(self.graphics_socket)
        del self.graphics_socket

    def change_socket_type(self, new_socket_type: int) -> bool:
        """Update socket type and refresh visual appearance.

        Args:
            new_socket_type: New type identifier for the socket.

        Returns:
            True if type changed, False if already set to this type.
        """
        if self.socket_type != new_socket_type:
            self.socket_type = new_socket_type
            self.graphics_socket.change_socket_type()
            return True
        return False

    def set_socket_position(self) -> None:
        """Update graphics socket position based on current node layout.

        Queries the parent node for this socket's position and updates
        the graphics socket accordingly.
        """
        pos = self.node.get_socket_position(self.index, self.position, self.count_on_this_node_side)
        self.graphics_socket.setPos(*pos)

    def get_socket_position(self) -> tuple[float, float]:
        """Calculate socket position in node-local coordinates.

        Returns:
            Tuple of (x, y) position relative to parent node.
        """
        result = self.node.get_socket_position(
            self.index, self.position, self.count_on_this_node_side
        )
        return result

    def has_any_edge(self) -> bool:
        """Check if socket has any connected edges.

        Returns:
            True if at least one edge is connected to this socket.
        """
        return len(self.edges) > 0

    def is_connected(self, edge: "Edge") -> bool:
        """Check if a specific edge is connected to this socket.

        Args:
            edge: Edge instance to check for connection.

        Returns:
            True if the edge is in this socket's edge list.
        """
        return edge in self.edges

    def add_edge(self, edge: "Edge") -> None:
        """Register an edge as connected to this socket.

        Args:
            edge: Edge to add to the connection list.
        """
        self.edges.append(edge)

    def remove_edge(self, edge: "Edge") -> None:
        """Unregister an edge from this socket.

        Args:
            edge: Edge to remove from the connection list.

        Note:
            Silently ignores if edge is not connected.
        """
        if edge in self.edges:
            self.edges.remove(edge)

    def remove_all_edges(self, silent: bool = False) -> None:
        """Disconnect and remove all edges from this socket.

        Iterates through all connected edges and removes them. Each edge
        is properly cleaned up through its remove() method.

        Args:
            silent: If True, suppress removal notifications to this socket.
        """
        while self.edges:
            edge = self.edges.pop(0)
            if silent:
                edge.remove(silent_for_socket=self)
            else:
                edge.remove()

    def serialize(self) -> dict:
        """Convert socket state to dictionary for persistence.

        Returns:
            Dictionary containing socket configuration and ID.
        """
        return {
            "sid": self.sid,
            "index": self.index,
            "multi_edges": self.is_multi_edges,
            "position": self.position,
            "socket_type": self.socket_type,
        }

    def deserialize(self, data: dict, hashmap: dict | None = None, restore_id: bool = True) -> bool:
        """Restore socket state from serialized dictionary.

        Args:
            data: Dictionary containing serialized socket data.
            hashmap: Maps original IDs to restored objects for references.
            restore_id: If True, restore original ID from data.

        Returns:
            True on successful deserialization.
        """
        if hashmap is None:
            hashmap = {}

        # New format (v2+): stable string IDs
        if restore_id and "sid" in data:
            self.sid = data["sid"]

        # Register both stable and legacy IDs (legacy used ints under key 'id')
        if "sid" in data:
            hashmap[data["sid"]] = self
        if "id" in data:
            hashmap[data["id"]] = self

        self.is_multi_edges = data["multi_edges"]
        self.change_socket_type(data["socket_type"])
        return True
