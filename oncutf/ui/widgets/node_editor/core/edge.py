"""Edge connections between node sockets.

This module defines the Edge class representing visual connections between
node sockets in the graph. Edges support multiple path styles (direct,
bezier, square) and include a validation system for controlling which
connections are allowed.

Edge Type Constants:
    EDGE_TYPE_DIRECT: Straight line connection.
    EDGE_TYPE_BEZIER: Classic bezier curve.
    EDGE_TYPE_SQUARE: Right-angle stepped path.
    EDGE_TYPE_IMPROVED_SHARP: Improved sharp-corner path.
    EDGE_TYPE_IMPROVED_BEZIER: Smooth bezier with optimized control points.

The validation system allows registering callbacks that approve or reject
connections before they are established, enabling type-checking or custom
connection rules.

Author:
    Michael Economou

Date:
    2025-12-11
"""

import contextlib
from enum import IntEnum
from typing import TYPE_CHECKING

from oncutf.ui.widgets.node_editor.core.serializable import Serializable
from oncutf.ui.widgets.node_editor.utils.helpers import dump_exception

if TYPE_CHECKING:
    from oncutf.ui.widgets.node_editor.core.scene import Scene
    from oncutf.ui.widgets.node_editor.core.socket import Socket
    from oncutf.ui.widgets.node_editor.graphics.edge import QDMGraphicsEdge


class EdgeType(IntEnum):
    """Edge path style constants.

    IntEnum provides type safety while maintaining backward compatibility
    with integer comparisons and serialization.
    """

    DIRECT = 1
    BEZIER = 2
    SQUARE = 3
    IMPROVED_SHARP = 4
    IMPROVED_BEZIER = 5


# Backward compatibility: expose as module-level constants
EDGE_TYPE_DIRECT = EdgeType.DIRECT
EDGE_TYPE_BEZIER = EdgeType.BEZIER
EDGE_TYPE_SQUARE = EdgeType.SQUARE
EDGE_TYPE_IMPROVED_SHARP = EdgeType.IMPROVED_SHARP
EDGE_TYPE_IMPROVED_BEZIER = EdgeType.IMPROVED_BEZIER
EDGE_TYPE_DEFAULT = EDGE_TYPE_IMPROVED_BEZIER


class Edge(Serializable):
    """Visual connection between two sockets in the node graph.

    An edge links an output socket to an input socket, representing data
    flow between nodes. The edge manages its own lifecycle, registering
    with connected sockets and updating its visual path when nodes move.

    Edges support validation through class-level callbacks that can approve
    or reject connections based on socket types, node states, or custom
    logic. This enables features like type-safe connections.

    Attributes:
        scene: Parent Scene containing this edge.
        start_socket: Source socket (typically an output).
        end_socket: Target socket (typically an input), or None while dragging.
        edge_type: Path style constant (EDGE_TYPE_DIRECT, etc.).
        graphics_edge: QDMGraphicsEdge instance for visual representation.

    Class Attributes:
        edge_validators: List of validation callback functions.
        _graphics_edge_class: Graphics class for edge visualization (set at init).
    """

    edge_validators: list = []
    _graphics_edge_class: type["QDMGraphicsEdge"] | None = None

    def __init__(
        self,
        scene: "Scene",
        start_socket: "Socket | None" = None,
        end_socket: "Socket | None" = None,
        edge_type: int = EDGE_TYPE_DEFAULT,
    ):
        """Create an edge between two sockets.

        The edge registers itself with the scene and both sockets. If start
        socket is provided, initial positions are calculated and the graphics
        edge is updated.

        Args:
            scene: Parent scene that will contain this edge.
            start_socket: Source socket to connect from (typically output).
            end_socket: Target socket to connect to (typically input).
            edge_type: Visual path style constant.
        """
        super().__init__()
        self.scene = scene

        self._start_socket: Socket | None = None
        self._end_socket: Socket | None = None

        self.start_socket = start_socket
        self.end_socket = end_socket
        self._edge_type = edge_type

        self.graphics_edge = self.create_edge_class_instance()

        self.scene.add_edge(self)

    def __str__(self) -> str:
        """Return human-readable edge representation.

        Returns:
            Format: <Edge ID -- S:socket E:socket> showing both endpoints.
        """
        return (
            f"<Edge {hex(id(self))[2:5]}..{hex(id(self))[-3:]} -- "
            f"S:{self.start_socket} E:{self.end_socket}>"
        )

    @property
    def start_socket(self) -> "Socket | None":
        """Source socket for this edge.

        Returns:
            Socket instance or None if not connected.
        """
        return self._start_socket

    @start_socket.setter
    def start_socket(self, value: "Socket | None") -> None:
        """Set source socket with automatic registration.

        Removes edge from previous socket edge list and registers
        with new socket.

        Args:
            value: New source socket, or None to disconnect.
        """
        if self._start_socket is not None:
            self._start_socket.remove_edge(self)

        self._start_socket = value
        if self.start_socket is not None:
            self.start_socket.add_edge(self)

    @property
    def end_socket(self) -> "Socket | None":
        """Target socket for this edge.

        Returns:
            Socket instance or None if edge is being dragged.
        """
        return self._end_socket

    @end_socket.setter
    def end_socket(self, value: "Socket | None") -> None:
        """Set target socket with automatic registration.

        Removes edge from previous socket edge list and registers
        with new socket.

        Args:
            value: New target socket, or None to disconnect.
        """
        if self._end_socket is not None:
            self._end_socket.remove_edge(self)

        self._end_socket = value
        if self.end_socket is not None:
            self.end_socket.add_edge(self)

    @property
    def edge_type(self) -> int:
        """Visual path style constant.

        Returns:
            One of EDGE_TYPE_* constants.
        """
        return self._edge_type

    @edge_type.setter
    def edge_type(self, value: int) -> None:
        """Change edge path style and refresh graphics.

        Updates the path calculator and recalculates positions.

        Args:
            value: New path style constant.
        """
        self._edge_type = value

        self.graphics_edge.create_edge_path_calculator()

        if self.start_socket is not None:
            self.update_positions()

    @classmethod
    def get_edge_validators(cls) -> list:
        """Retrieve registered edge validator callbacks.

        Returns:
            List of validator functions.
        """
        return cls.edge_validators

    @classmethod
    def register_edge_validator(cls, validator_callback) -> None:
        """Register a callback to validate edge connections.

        Validators receive (start_socket, end_socket) and return True
        if the connection should be allowed.

        Args:
            validator_callback: Function(start_socket, end_socket) -> bool.
        """
        cls.edge_validators.append(validator_callback)

    @classmethod
    def validate_edge(cls, start_socket: "Socket", end_socket: "Socket") -> bool:
        """Check if connection is allowed by all validators.

        Args:
            start_socket: Proposed source socket.
            end_socket: Proposed target socket.

        Returns:
            True if all validators approve the connection.
        """
        return all(validator(start_socket, end_socket) for validator in cls.get_edge_validators())

    def reconnect(self, from_socket: "Socket", to_socket: "Socket") -> None:
        """Move one endpoint to a different socket.

        Args:
            from_socket: Current socket to disconnect from.
            to_socket: New socket to connect to.
        """
        if self.start_socket == from_socket:
            self.start_socket = to_socket
        elif self.end_socket == from_socket:
            self.end_socket = to_socket

    def get_graphics_edge_class(self) -> type["QDMGraphicsEdge"]:
        """Get graphics class for edge visualization.

        Returns:
            QDMGraphicsEdge class or subclass.
        """
        return self.__class__._graphics_edge_class

    def create_edge_class_instance(self) -> "QDMGraphicsEdge":
        """Instantiate and configure graphics edge.

        Creates the visual representation, adds it to the scene,
        and calculates initial path if start socket exists.

        Returns:
            Configured QDMGraphicsEdge instance.
        """
        self.graphics_edge = self.get_graphics_edge_class()(self)
        self.scene.graphics_scene.addItem(self.graphics_edge)
        if self.start_socket is not None:
            self.update_positions()
        return self.graphics_edge

    def get_other_socket(self, known_socket: "Socket") -> "Socket | None":
        """Get the opposite socket on this edge.

        Given one endpoint, returns the other. Useful for traversing
        the graph through edges.

        Args:
            known_socket: One of the two connected sockets.

        Returns:
            The other socket, or None if known_socket is not connected.
        """
        return self.start_socket if known_socket == self.end_socket else self.end_socket

    def do_select(self, new_state: bool = True) -> None:
        """Programmatically select or deselect this edge.

        Args:
            new_state: True to select, False to deselect.
        """
        self.graphics_edge.do_select(new_state)

    def update_positions(self) -> None:
        """Recalculate edge path based on current socket positions.

        Queries both sockets for their scene positions and updates
        the graphics edge endpoints. Called automatically when nodes move.
        """
        source_pos = list(self.start_socket.get_socket_position())
        source_pos[0] += self.start_socket.node.graphics_node.pos().x()
        source_pos[1] += self.start_socket.node.graphics_node.pos().y()
        self.graphics_edge.set_source(*source_pos)

        if self.end_socket is not None:
            end_pos = list(self.end_socket.get_socket_position())
            end_pos[0] += self.end_socket.node.graphics_node.pos().x()
            end_pos[1] += self.end_socket.node.graphics_node.pos().y()
            self.graphics_edge.set_destination(*end_pos)
        else:
            self.graphics_edge.set_destination(*source_pos)

        self.graphics_edge.update()

    def remove_from_sockets(self) -> None:
        """Unregister edge from both connected sockets.

        Sets both socket references to None, which triggers the property
        setters to remove this edge from socket edge lists.
        """
        self.end_socket = None
        self.start_socket = None

    def remove(self, silent_for_socket: "Socket | None" = None, silent: bool = False) -> None:
        """Delete edge and clean up all references.

        Removes graphics item, unregisters from sockets and scene,
        and notifies connected nodes of the disconnection.

        Args:
            silent_for_socket: Skip notification to this socket node.
            silent: If True, suppress all node notifications.
        """
        old_sockets = [self.start_socket, self.end_socket]

        self.graphics_edge.hide()

        self.scene.graphics_scene.removeItem(self.graphics_edge)

        self.scene.graphics_scene.update()

        self.remove_from_sockets()

        with contextlib.suppress(ValueError):
            self.scene.remove_edge(self)

        try:
            for socket in old_sockets:
                if socket and socket.node:
                    if silent:
                        continue
                    if silent_for_socket is not None and socket == silent_for_socket:
                        continue

                    socket.node.on_edge_connection_changed(self)
                    if socket.is_input:
                        socket.node.on_input_changed(socket)

        except Exception as e:
            dump_exception(e)

    def serialize(self) -> dict:
        """Convert edge state to dictionary for persistence.

        Returns:
            Dictionary with edge ID, type, and socket references.
        """
        return {
            "sid": self.sid,
            "edge_type": self.edge_type,
            "start": self.start_socket.sid if self.start_socket is not None else None,
            "end": self.end_socket.sid if self.end_socket is not None else None,
        }

    def deserialize(
        self,
        data: dict,
        hashmap: dict | None = None,
        restore_id: bool = True,
        *_args,
        **_kwargs,
    ) -> bool:
        """Restore edge state from serialized dictionary.

        Reconnects to sockets using hashmap to resolve IDs to objects.

        Args:
            data: Dictionary containing serialized edge data.
            hashmap: Maps original IDs to restored objects.
            restore_id: If True, restore original ID from data.

        Returns:
            True on successful deserialization.
        """
        if hashmap is None:
            hashmap = {}

        if restore_id and "sid" in data:
            self.sid = data["sid"]

        if "sid" in data:
            hashmap[data["sid"]] = self
        if "id" in data:
            hashmap[data["id"]] = self

        self.start_socket = hashmap[data["start"]] if data.get("start") is not None else None
        self.end_socket = hashmap[data["end"]] if data.get("end") is not None else None
        self.edge_type = data["edge_type"]
        return True
