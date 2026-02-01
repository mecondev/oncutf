"""Node representation in the visual graph editor.

This module defines the Node class, the fundamental building block of node
graphs. Nodes contain sockets for connections, content widgets for UI
interaction, and graphics representations for visualization. The module
supports an evaluation system with dirty/invalid state tracking for
efficient graph computation.

Node Features:
    - Configurable input and output sockets
    - Customizable content widget
    - Dirty/invalid state propagation for evaluation
    - Serialization/deserialization support
    - Graph traversal methods

Author:
    Michael Economou

Date:
    2025-12-11
"""

from typing import TYPE_CHECKING

from oncutf.ui.widgets.node_editor.core.serializable import Serializable
from oncutf.ui.widgets.node_editor.core.socket import (
    LEFT_BOTTOM,
    LEFT_CENTER,
    LEFT_TOP,
    RIGHT_BOTTOM,
    RIGHT_CENTER,
    RIGHT_TOP,
    Socket,
)
from oncutf.ui.widgets.node_editor.utils.helpers import dump_exception

if TYPE_CHECKING:
    from PyQt5.QtCore import QPointF

    from oncutf.ui.widgets.node_editor.core.edge import Edge
    from oncutf.ui.widgets.node_editor.core.scene import Scene
    from oncutf.ui.widgets.node_editor.graphics.node import QDMGraphicsNode
    from oncutf.ui.widgets.node_editor.widgets.content_widget import (
        QDMNodeContentWidget,
    )


class Node(Serializable):
    """Fundamental graph element containing sockets and content.

    A node represents a single processing unit in the graph. It manages
    input and output sockets for connections, a content widget for user
    interaction, and maintains evaluation state (dirty/invalid) for
    efficient graph computation.

    Subclass this to create custom node types with specific behavior,
    socket configurations, and content widgets.

    Attributes:
        scene: Parent Scene containing this node.
        title: Display title shown in the graphics node.
        graphics_node: QDMGraphicsNode instance for visualization.
        content: QDMNodeContentWidget instance for UI content.
        inputs: List of input Socket instances.
        outputs: List of output Socket instances.

    Class Attributes:
        _graphics_node_class: Graphics class injected via node_editor.core._init_graphics_classes;
            override in subclasses for custom visuals.
        _content_widget_class: Content widget class injected via node_editor.core._init_graphics_classes;
            override in subclasses for custom UI widgets.
        Socket_class: Socket class for creating connections.

    """

    _graphics_node_class: type["QDMGraphicsNode"] | None = None
    _content_widget_class: type["QDMNodeContentWidget"] | None = None
    Socket_class = Socket

    def __init__(
        self,
        scene: "Scene",
        title: str = "Undefined Node",
        inputs: list[int] | None = None,
        outputs: list[int] | None = None,
    ):
        """Create a node and add it to the scene.

        Initializes graphics, content widget, and sockets based on
        provided configurations. The node is automatically registered
        with the scene.

        Args:
            scene: Parent scene that will contain this node.
            title: Display text shown in the node header.
            inputs: Socket type identifiers for input sockets.
            outputs: Socket type identifiers for output sockets.

        """
        super().__init__()
        self._title = title
        self.scene = scene

        self.content: QDMNodeContentWidget | None = None
        self.graphics_node: QDMGraphicsNode | None = None

        self.init_inner_classes()
        self.init_settings()

        self.title = title

        self.scene.add_node(self)
        self.scene.graphics_scene.addItem(self.graphics_node)

        self.inputs: list[Socket] = []
        self.outputs: list[Socket] = []
        self.init_sockets(inputs or [], outputs or [])

        self._is_dirty = False
        self._is_invalid = False

    def __str__(self) -> str:
        """Return human-readable node representation.

        Returns:
            Format: <title:ClassName ID> showing title and class.

        """
        return (
            f"<{self.title}:{self.__class__.__name__} {hex(id(self))[2:5]}..{hex(id(self))[-3:]}>"
        )

    @property
    def title(self) -> str:
        """Display title shown in the graphics node header.

        Returns:
            Current title string.

        """
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        """Update node title and refresh display.

        Args:
            value: New title to display.

        """
        self._title = value
        self.graphics_node.title = self._title

    @property
    def pos(self) -> "QPointF":
        """Current position in scene coordinates.

        Returns:
            QPointF with x, y position.

        """
        return self.graphics_node.pos()

    def set_pos(self, x: float, y: float) -> None:
        """Move node to specified scene position.

        Updates graphics position and recalculates all connected
        edge paths.

        Args:
            x: Horizontal scene coordinate.
            y: Vertical scene coordinate.

        """
        self.graphics_node.setPos(x, y)
        for socket in self.inputs:
            for edge in socket.edges:
                edge.graphics_edge.calc_path()
                edge.update_positions()
        for socket in self.outputs:
            for edge in socket.edges:
                edge.graphics_edge.calc_path()
                edge.update_positions()

    def init_inner_classes(self) -> None:
        """Instantiate graphics node and content widget.

        Creates instances using class-level factory classes. Override
        get_node_content_class() and get_graphics_node_class() to customize.
        """
        node_content_class = self.get_node_content_class()
        graphics_node_class = self.get_graphics_node_class()
        if node_content_class is not None:
            self.content = node_content_class(self)
        if graphics_node_class is not None:
            self.graphics_node = graphics_node_class(self)

    def get_node_content_class(self) -> type["QDMNodeContentWidget"] | None:
        """Get factory class for content widget.

        Override in subclasses to provide custom content widgets.

        Returns:
            Content widget class or None for no content.

        """
        return self.__class__._content_widget_class

    def get_graphics_node_class(self) -> type["QDMGraphicsNode"] | None:
        """Get factory class for graphics node.

        Override in subclasses to provide custom graphics.

        Returns:
            Graphics node class or None.

        """
        return self.__class__._graphics_node_class

    def init_settings(self) -> None:
        """Configure socket layout properties.

        Sets socket spacing, positions, and multi-edge defaults.
        Override to customize socket arrangement.
        """
        self.socket_spacing = 22

        self.input_socket_position = LEFT_BOTTOM
        self.output_socket_position = RIGHT_TOP
        self.input_multi_edged = False
        self.output_multi_edged = True
        self.socket_offsets = {
            LEFT_BOTTOM: -1,
            LEFT_CENTER: -1,
            LEFT_TOP: -1,
            RIGHT_BOTTOM: 1,
            RIGHT_CENTER: 1,
            RIGHT_TOP: 1,
        }

    def init_sockets(self, inputs: list[int], outputs: list[int], reset: bool = True) -> None:
        """Create input and output sockets from type lists.

        Optionally removes existing sockets first. Each element in
        the lists represents a socket type identifier.

        Args:
            inputs: Socket type IDs for inputs.
            outputs: Socket type IDs for outputs.
            reset: If True, remove existing sockets before creating new.

        """
        if reset and hasattr(self, "inputs") and hasattr(self, "outputs"):
            # Clear old sockets
            # Remove graphics sockets from scene
            for socket in self.inputs + self.outputs:
                self.scene.graphics_scene.removeItem(socket.graphics_socket)
            self.inputs = []
            self.outputs = []

        # Create new input sockets
        for counter, item in enumerate(inputs):
            socket = self.__class__.Socket_class(
                node=self,
                index=counter,
                position=self.input_socket_position,
                socket_type=item,
                multi_edges=self.input_multi_edged,
                count_on_this_node_side=len(inputs),
                is_input=True,
            )
            self.inputs.append(socket)

        # Create new output sockets
        for counter, item in enumerate(outputs):
            socket = self.__class__.Socket_class(
                node=self,
                index=counter,
                position=self.output_socket_position,
                socket_type=item,
                multi_edges=self.output_multi_edged,
                count_on_this_node_side=len(outputs),
                is_input=False,
            )
            self.outputs.append(socket)

    def on_edge_connection_changed(self, new_edge: "Edge") -> None:
        """Handle edge connection or disconnection events.

        Called when any edge connected to this node changes state.
        Override to implement custom connection handling logic.

        Args:
            new_edge: Edge that was connected or disconnected.

        """

    def on_input_changed(self, _socket: Socket) -> None:
        """Handle input socket value changes.

        Called when data arrives on an input socket. Default behavior
        marks this node and all descendants as dirty for re-evaluation.

        Args:
            _socket: Input socket that received new data.

        """
        self.mark_dirty()
        self.mark_descendants_dirty()

    def on_deserialized(self, data: dict) -> None:
        """Handle post-deserialization initialization.

        Called after node state is restored from saved data. Override
        to perform any required setup after loading.

        Args:
            data: Dictionary containing the deserialized data.

        """

    def on_double_clicked(self, event) -> None:
        """Handle double-click on graphics node.

        Override to implement custom double-click behavior such as
        opening configuration dialogs.

        Args:
            event: Qt mouse event with click details.

        """

    def do_select(self, new_state: bool = True) -> None:
        """Programmatically select or deselect this node.

        Args:
            new_state: True to select, False to deselect.

        """
        self.graphics_node.do_select(new_state)

    def is_selected(self) -> bool:
        """Check if node is currently selected.

        Returns:
            True if node is in selected state.

        """
        return self.graphics_node.isSelected()

    def has_connected_edge(self, edge: "Edge") -> bool:
        """Check if specified edge connects to this node.

        Args:
            edge: Edge to check for connection.

        Returns:
            True if edge is connected to any socket on this node.

        """
        return any(socket.is_connected(edge) for socket in self.inputs + self.outputs)

    def get_socket_position(
        self, index: int, position: int, num_out_of: int = 1
    ) -> tuple[float, float]:
        """Calculate socket position in node-local coordinates.

        Determines placement based on socket index, position constant,
        and total socket count for proper spacing.

        Args:
            index: Zero-based socket index on this side.
            position: Position constant (LEFT_TOP, RIGHT_CENTER, etc.).
            num_out_of: Total sockets on this position for spacing calc.

        Returns:
            Tuple of (x, y) in node-local coordinates.

        """
        x = (
            self.socket_offsets[position]
            if (position in (LEFT_TOP, LEFT_CENTER, LEFT_BOTTOM))
            else self.graphics_node.width + self.socket_offsets[position]
        )

        if position in (LEFT_BOTTOM, RIGHT_BOTTOM):
            y = (
                self.graphics_node.height
                - self.graphics_node.edge_roundness
                - self.graphics_node.title_vertical_padding
                - index * self.socket_spacing
            )
        elif position in (LEFT_CENTER, RIGHT_CENTER):
            node_height = self.graphics_node.height
            top_offset = (
                self.graphics_node.title_height
                + 2 * self.graphics_node.title_vertical_padding
                + self.graphics_node.edge_padding
            )
            available_height = node_height - top_offset

            y = top_offset + available_height / 2.0 + (index - 0.5) * self.socket_spacing
            if num_out_of > 1:
                y -= self.socket_spacing * (num_out_of - 1) / 2

        elif position in (LEFT_TOP, RIGHT_TOP):
            y = (
                self.graphics_node.title_height
                + self.graphics_node.title_vertical_padding
                + self.graphics_node.edge_roundness
                + index * self.socket_spacing
            )
        else:
            y = 0

        return (x, y)

    def get_socket_scene_position(self, socket: Socket) -> tuple[float, float]:
        """Calculate socket position in scene coordinates.

        Combines node position with socket offset for absolute placement.

        Args:
            socket: Socket to get position for.

        Returns:
            Tuple of (x, y) in scene coordinates.

        """
        nodepos = self.graphics_node.pos()
        socketpos = self.get_socket_position(
            socket.index, socket.position, socket.count_on_this_node_side
        )
        return (nodepos.x() + socketpos[0], nodepos.y() + socketpos[1])

    def update_connected_edges(self) -> None:
        """Refresh positions of all edges connected to this node.

        Call after moving node to update edge path calculations.
        """
        for socket in self.inputs + self.outputs:
            for edge in socket.edges:
                edge.update_positions()

    def remove(self) -> None:
        """Delete node and clean up all references.

        Removes all connected edges, graphics item, and unregisters
        from the scene.
        """
        for socket in self.inputs + self.outputs:
            for edge in socket.edges.copy():
                edge.remove()

        self.scene.graphics_scene.removeItem(self.graphics_node)
        self.graphics_node = None
        self.scene.remove_node(self)

    # Node evaluation methods

    def is_dirty(self) -> bool:
        """Check if node requires re-evaluation.

        Returns:
            True if node data is stale and needs recalculation.

        """
        return self._is_dirty

    def mark_dirty(self, new_value: bool = True) -> None:
        """Set dirty state indicating need for re-evaluation.

        Triggers on_marked_dirty() callback when transitioning to dirty.

        Args:
            new_value: True to mark dirty, False to clear dirty state.

        """
        self._is_dirty = new_value
        if self._is_dirty:
            self.on_marked_dirty()

    def on_marked_dirty(self) -> None:
        """Handle transition to dirty state.

        Override to implement custom dirty-state handling such as
        visual indicators or logging.
        """

    def mark_children_dirty(self, new_value: bool = True) -> None:
        """Mark immediate downstream nodes as dirty.

        Only affects first-level children connected to outputs.

        Args:
            new_value: True to mark dirty, False to clear.

        """
        for other_node in self.get_children_nodes():
            other_node.mark_dirty(new_value)

    def mark_descendants_dirty(self, new_value: bool = True) -> None:
        """Mark all downstream nodes as needing re-evaluation.

        Uses iterative BFS to avoid stack overflow on deep graphs
        and prevent duplicate processing on diamond patterns.

        Args:
            new_value: True to mark dirty, False to clear.

        """
        from collections import deque

        visited: set[str] = {self.sid}
        queue: deque[Node] = deque(self.get_children_nodes())

        while queue:
            node = queue.popleft()
            if node.sid in visited:
                continue
            visited.add(node.sid)
            node.mark_dirty(new_value)
            queue.extend(node.get_children_nodes())

    def is_invalid(self) -> bool:
        """Check if node is in an error state.

        Returns:
            True if node has invalid configuration or data.

        """
        return self._is_invalid

    def mark_invalid(self, new_value: bool = True) -> None:
        """Set invalid state indicating configuration error.

        Triggers on_marked_invalid() callback when transitioning to invalid.

        Args:
            new_value: True to mark invalid, False to clear.

        """
        self._is_invalid = new_value
        if self._is_invalid:
            self.on_marked_invalid()
        # Update visual representation
        if self.graphics_node:
            self.graphics_node.update()

    def on_marked_invalid(self) -> None:
        """Handle transition to invalid state.

        Override to implement error indicators or recovery logic.
        """

    def mark_children_invalid(self, new_value: bool = True) -> None:
        """Mark immediate downstream nodes as invalid.

        Args:
            new_value: True to mark invalid, False to clear.

        """
        for other_node in self.get_children_nodes():
            other_node.mark_invalid(new_value)

    def mark_descendants_invalid(self, new_value: bool = True) -> None:
        """Mark all downstream nodes as invalid.

        Uses iterative BFS to avoid stack overflow on deep graphs
        and prevent duplicate processing on diamond patterns.

        Args:
            new_value: True to mark invalid, False to clear.

        """
        from collections import deque

        visited: set[str] = {self.sid}
        queue: deque[Node] = deque(self.get_children_nodes())

        while queue:
            node = queue.popleft()
            if node.sid in visited:
                continue
            visited.add(node.sid)
            node.mark_invalid(new_value)
            queue.extend(node.get_children_nodes())

    def eval(self, _index: int = 0) -> int | float | str | bool | list | dict | None:
        """Evaluate node and compute output value.

        Override this method to implement node-specific computation.
        Default implementation clears dirty/invalid state and returns 0.

        Args:
            _index: Output socket index to evaluate.

        Returns:
            Computed value (type depends on node implementation).

        """
        self.mark_dirty(False)
        self.mark_invalid(False)
        return 0

    def eval_children(self) -> None:
        """Evaluate all immediate downstream nodes.

        Calls eval() on each node connected to this node's outputs.
        """
        for node in self.get_children_nodes():
            node.eval()

    # Node traversal methods

    def get_children_nodes(self) -> list["Node"]:
        """Get nodes connected to this node's outputs.

        Returns:
            List of downstream nodes (immediate children only).

        """
        if not self.outputs:
            return []
        other_nodes = []
        for output_socket in self.outputs:
            for edge in output_socket.edges:
                other_node = edge.get_other_socket(output_socket).node
                other_nodes.append(other_node)
        return other_nodes

    def get_input(self, index: int = 0) -> "Node | None":
        """Get node connected to specified input socket.

        Returns only the first connected node if multiple exist.

        Args:
            index: Input socket index (0-based).

        Returns:
            Connected node or None if unconnected.

        """
        try:
            input_socket = self.inputs[index]
            if len(input_socket.edges) == 0:
                return None
            connecting_edge = input_socket.edges[0]
            other_socket = connecting_edge.get_other_socket(self.inputs[index])
            return other_socket.node
        except Exception as e:
            dump_exception(e)
            return None

    def get_input_with_socket(self, index: int = 0) -> tuple["Node | None", "Socket | None"]:
        """Get node and socket connected to specified input.

        Returns first connection if multiple exist.

        Args:
            index: Input socket index (0-based).

        Returns:
            Tuple of (node, socket) or (None, None) if unconnected.

        """
        try:
            input_socket = self.inputs[index]
            if len(input_socket.edges) == 0:
                return None, None
            connecting_edge = input_socket.edges[0]
            other_socket = connecting_edge.get_other_socket(self.inputs[index])
            return other_socket.node, other_socket
        except Exception as e:
            dump_exception(e)
            return None, None

    def get_input_with_socket_index(self, index: int = 0) -> tuple["Node | None", int | None]:
        """Get node and output socket index connected to specified input.

        Args:
            index: Input socket index (0-based).

        Returns:
            Tuple of (node, socket_index) or (None, None) if unconnected.

        """
        try:
            edge = self.inputs[index].edges[0]
            socket = edge.get_other_socket(self.inputs[index])
            return socket.node, socket.index
        except IndexError:
            return None, None
        except Exception as e:
            dump_exception(e)
            return None, None

    def get_inputs(self, index: int = 0) -> list["Node"]:
        """Get all nodes connected to specified input socket.

        Useful for multi-edge input sockets.

        Args:
            index: Input socket index (0-based).

        Returns:
            List of all connected upstream nodes.

        """
        ins = []
        for edge in self.inputs[index].edges:
            other_socket = edge.get_other_socket(self.inputs[index])
            ins.append(other_socket.node)
        return ins

    def get_outputs(self, index: int = 0) -> list["Node"]:
        """Get all nodes connected to specified output socket.

        Args:
            index: Output socket index (0-based).

        Returns:
            List of all connected downstream nodes.

        """
        outs = []
        for edge in self.outputs[index].edges:
            other_socket = edge.get_other_socket(self.outputs[index])
            outs.append(other_socket.node)
        return outs

    # Serialization methods

    def serialize(self) -> dict:
        """Convert node state to dictionary for persistence.

        Includes position, sockets, and content widget state.

        Returns:
            Dictionary containing complete node configuration.

        """
        inputs, outputs = [], []
        for socket in self.inputs:
            inputs.append(socket.serialize())
        for socket in self.outputs:
            outputs.append(socket.serialize())
        ser_content = self.content.serialize() if isinstance(self.content, Serializable) else {}
        return {
            "sid": self.sid,
            "title": self.title,
            "pos_x": self.graphics_node.scenePos().x(),
            "pos_y": self.graphics_node.scenePos().y(),
            "inputs": inputs,
            "outputs": outputs,
            "content": ser_content,
        }

    def deserialize(
        self,
        data: dict,
        hashmap: dict | None = None,
        restore_id: bool = True,
        *_args,
        **_kwargs,
    ) -> bool:
        """Restore node state from serialized dictionary.

        Restores position, sockets, and content. Uses hashmap to
        resolve ID references for edge connections.

        Args:
            data: Dictionary containing serialized node data.
            hashmap: Maps original IDs to restored objects.
            restore_id: If True, restore original ID from data.

        Returns:
            True on successful deserialization.

        """
        if hashmap is None:
            hashmap = {}

        try:
            # New format (v2+): stable string IDs
            if restore_id and "sid" in data:
                self.sid = data["sid"]

            # Register both stable and legacy IDs (legacy used ints under key 'id')
            if "sid" in data:
                hashmap[data["sid"]] = self
            if "id" in data:
                hashmap[data["id"]] = self

            self.set_pos(data["pos_x"], data["pos_y"])
            self.title = data["title"]

            data["inputs"].sort(key=lambda socket: socket["index"] + socket["position"] * 10000)
            data["outputs"].sort(key=lambda socket: socket["index"] + socket["position"] * 10000)
            num_inputs = len(data["inputs"])
            num_outputs = len(data["outputs"])

            for socket_data in data["inputs"]:
                found = None
                for socket in self.inputs:
                    if socket.index == socket_data["index"]:
                        found = socket
                        break
                if found is None:
                    found = self.__class__.Socket_class(
                        node=self,
                        index=socket_data["index"],
                        position=socket_data["position"],
                        socket_type=socket_data["socket_type"],
                        count_on_this_node_side=num_inputs,
                        is_input=True,
                    )
                    self.inputs.append(found)
                found.deserialize(socket_data, hashmap, restore_id)

            for socket_data in data["outputs"]:
                found = None
                for socket in self.outputs:
                    if socket.index == socket_data["index"]:
                        found = socket
                        break
                if found is None:
                    found = self.__class__.Socket_class(
                        node=self,
                        index=socket_data["index"],
                        position=socket_data["position"],
                        socket_type=socket_data["socket_type"],
                        count_on_this_node_side=num_outputs,
                        is_input=False,
                    )
                    self.outputs.append(found)
                found.deserialize(socket_data, hashmap, restore_id)

        except Exception as e:
            dump_exception(e)

        if isinstance(self.content, Serializable):
            return self.content.deserialize(data["content"], hashmap)

        return True
