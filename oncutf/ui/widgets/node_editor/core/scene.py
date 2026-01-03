"""Scene container for nodes, edges, and graph state.

This module defines the Scene class, the central manager for all elements
in a node graph. The scene maintains collections of nodes and edges,
handles selection, provides undo/redo through history, and manages
serialization for save/load operations.

Key Responsibilities:
    - Node and edge lifecycle management (add, remove, clear)
    - Selection state tracking with event callbacks
    - History system for undo/redo operations
    - Clipboard operations for copy/paste
    - File I/O with JSON serialization
    - Modified state tracking

The scene coordinates between the logical graph model and the graphics
scene (QDMGraphicsScene) that handles visual representation.

Author:
    Michael Economou

Date:
    2025-12-11
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from oncutf.ui.widgets.node_editor.core.host_bridge import NodeHostBridge, NullNodeHostBridge
from oncutf.ui.widgets.node_editor.core.serializable import Serializable
from oncutf.ui.widgets.node_editor.utils.helpers import dump_exception

if TYPE_CHECKING:
    from oncutf.ui.widgets.node_editor.core.edge import Edge
    from oncutf.ui.widgets.node_editor.core.node import Node
    from oncutf.ui.widgets.node_editor.graphics.scene import QDMGraphicsScene


logger = logging.getLogger(__name__)


class Scene(Serializable):
    """Central container managing nodes, edges, and graph state.

    The Scene is the top-level manager for the node graph. It owns all nodes
    and edges, tracks selection state, maintains modification history for
    undo/redo, and handles serialization for persistence.

    The scene uses an event callback system to notify interested parties
    about selection changes and modifications. Register callbacks via the
    add*Listener methods.

    Attributes:
        nodes: List of all Node instances in the graph.
        edges: List of all Edge instances connecting nodes.
        history: SceneHistory instance managing undo/redo stack.
        clipboard: SceneClipboard instance for copy/paste operations.
        scene_width: Horizontal extent of scene in pixels.
        scene_height: Vertical extent of scene in pixels.
        filename: Path to associated file, or None if unsaved.
        graphics_scene: QDMGraphicsScene for visual representation.

    Class Attributes:
        history_class: Factory class for history (set at runtime).
        clipboard_class: Factory class for clipboard (set at runtime).
    """

    history_class = None
    clipboard_class = None

    SNAPSHOT_VERSION = "2.0.0"

    def __init__(self, host_bridge: NodeHostBridge | None = None) -> None:
        """Initialize empty scene with default dimensions.

        Creates graphics scene, history system, and clipboard. Connects
        selection signals for event handling.
        """
        super().__init__()

        self.host_bridge: NodeHostBridge = (
            host_bridge if host_bridge is not None else NullNodeHostBridge()
        )

        self.nodes: list[Node] = []
        self.edges: list[Edge] = []

        self.filename: str | None = None

        self.scene_width: int = 64000
        self.scene_height: int = 64000

        self._silent_selection_events: bool = False
        self._has_been_modified: bool = False
        self._last_selected_items: list | None = None

        self._has_been_modified_listeners: list[Callable] = []
        self._item_selected_listeners: list[Callable] = []
        self._items_deselected_listeners: list[Callable] = []

        self.node_class_selector: Callable[[dict], type[Node]] | None = None

        self.init_ui()

        from oncutf.ui.widgets.node_editor.core.clipboard import SceneClipboard
        from oncutf.ui.widgets.node_editor.core.history import SceneHistory

        self.history = SceneHistory(self)
        self.clipboard = SceneClipboard(self)

        self.graphics_scene.item_selected.connect(self.on_item_selected)
        self.graphics_scene.items_deselected.connect(self.on_items_deselected)

    @property
    def has_been_modified(self) -> bool:
        """Check if scene has unsaved changes.

        Returns:
            True if modified since last save.
        """
        return self._has_been_modified

    @has_been_modified.setter
    def has_been_modified(self, value: bool) -> None:
        """Update modification state and notify listeners.

        Triggers callbacks only on transition from unmodified to modified.

        Args:
            value: New modification state.
        """
        if not self._has_been_modified and value:
            self._has_been_modified = value

            for callback in self._has_been_modified_listeners:
                callback()

        self._has_been_modified = value

    def is_modified(self) -> bool:
        """Compatibility alias for ``has_been_modified``.

        Returns:
            True if modified since last save.
        """

        return self.has_been_modified

    def init_ui(self) -> None:
        """Create and configure the graphics scene.

        Instantiates QDMGraphicsScene and sets its dimensions.
        """
        from oncutf.ui.widgets.node_editor.graphics.scene import QDMGraphicsScene

        self.graphics_scene: QDMGraphicsScene = QDMGraphicsScene(self)
        self.graphics_scene.set_graphics_scene_rect(self.scene_width, self.scene_height)

    # Node and edge management

    def add_node(self, node: Node) -> None:
        """Register a node with this scene.

        Called automatically by Node.__init__. Manual calls are rarely needed.

        Args:
            node: Node instance to add.
        """
        self.nodes.append(node)

    def add_edge(self, edge: Edge) -> None:
        """Register an edge with this scene.

        Called automatically by Edge.__init__. Manual calls are rarely needed.

        Args:
            edge: Edge instance to add.
        """
        self.edges.append(edge)

    def remove_node(self, node: Node) -> None:
        """Unregister a node from this scene.

        Does not delete the node object or its edges. Use node.remove()
        for complete cleanup.

        Args:
            node: Node instance to remove from registry.
        """
        if node in self.nodes:
            self.nodes.remove(node)

    def remove_edge(self, edge: Edge) -> None:
        """Unregister an edge from this scene.

        Does not delete the edge object. Use edge.remove() for complete cleanup.

        Args:
            edge: Edge instance to remove from registry.
        """
        if edge in self.edges:
            self.edges.remove(edge)

    def clear(self) -> None:
        """Remove all nodes and edges from the scene.

        Properly cleans up each node which cascades to remove all edges.
        Resets modification state to unmodified.
        """
        while len(self.nodes) > 0:
            self.nodes[0].remove()

        self.has_been_modified = False

    def get_node_by_id(self, node_id: str) -> Node | None:
        """Find a node by its unique identifier.

        Args:
            node_id: Unique ID assigned during node creation.

        Returns:
            Matching Node instance or None if not found.
        """
        for node in self.nodes:
            if node.sid == node_id:
                return node
        return None

    # Selection management

    def set_silent_selection_events(self, value: bool = True) -> None:
        """Enable or disable selection event callbacks.

        Useful during batch operations like clipboard paste to avoid
        triggering unwanted selection events.

        Args:
            value: True to suppress events, False to enable.
        """
        self._silent_selection_events = value

    def get_selected_nodes(self) -> list[Node]:
        """Get all currently selected nodes.

        Returns:
            List of selected Node instances.
        """
        return [node for node in self.nodes if node.is_selected()]

    def get_selected_edges(self) -> list[Edge]:
        """Get all currently selected edges.

        Returns:
            List of selected Edge instances.
        """
        return [edge for edge in self.edges if edge.is_selected()]

    def get_selected_items(self) -> list:
        """Get all currently selected graphics items.

        Returns:
            List of selected QGraphicsItem instances (nodes and edges).
        """
        return self.graphics_scene.selectedItems()

    def deselect_all(self, silent: bool = False) -> None:
        """Clear selection from all nodes and edges.

        Args:
            silent: If True, skip onItemsDeselected callback.
        """
        for node in self.nodes:
            node.do_select(False)
        for edge in self.edges:
            edge.do_select(False)
        if not silent:
            self.on_items_deselected()

    def on_item_selected(self, silent: bool = False) -> None:
        """Handle selection change events.

        Compares current selection with previous state and triggers
        registered callbacks if changed. Stores history entry.

        Args:
            silent: If True, skip callbacks and history storage.
        """
        if self._silent_selection_events:
            return

        current_selected_items = self.get_selected_items()
        if current_selected_items != self._last_selected_items:
            self._last_selected_items = current_selected_items
            if not silent:
                for callback in self._item_selected_listeners:
                    callback()
                self.history.store_history("Selection Changed")

    def on_items_deselected(self, silent: bool = False) -> None:
        """Handle complete deselection events.

        Called when selection becomes empty. Triggers registered callbacks
        and stores history entry.

        Args:
            silent: If True, skip callbacks and history storage.
        """
        current_selected_items = self.get_selected_items()
        if current_selected_items == self._last_selected_items:
            return

        self.graphics_scene.reset_last_selected_states()
        if current_selected_items == []:
            self._last_selected_items = []
            if not silent:
                self.history.store_history("Deselected Everything")
                for callback in self._items_deselected_listeners:
                    callback()

    # Modification state

    # Event listener management

    def add_has_been_modified_listener(self, callback: Callable) -> None:
        """Register callback for modification state changes.

        Callback receives no arguments, triggered on first modification.

        Args:
            callback: Function to call when scene becomes modified.
        """
        self._has_been_modified_listeners.append(callback)

    def add_item_selected_listener(self, callback: Callable) -> None:
        """Register callback for selection events.

        Callback receives no arguments, triggered when selection changes.

        Args:
            callback: Function to call on item selection.
        """
        self._item_selected_listeners.append(callback)

    def add_items_deselected_listener(self, callback: Callable) -> None:
        """Register callback for deselection events.

        Callback receives no arguments, triggered when selection clears.

        Args:
            callback: Function to call on complete deselection.
        """
        self._items_deselected_listeners.append(callback)

    def _get_graphics_view(self):
        """Internal helper to access graphics view through graphics_scene.

        Returns:
            First QDMGraphicsView attached to graphics_scene.

        Note:
            This is a transitional helper for components that need view access.
            Prefer using scene-level APIs where possible.
        """
        return self.graphics_scene.views()[0]

    # Node/Edge class selection

    def get_edge_class(self) -> type[Edge]:
        """Get factory class for creating edges.

        Override to use custom Edge subclass for this scene.

        Returns:
            Edge class type to instantiate.
        """
        from oncutf.ui.widgets.node_editor.core.edge import Edge

        return Edge

    def set_node_class_selector(
        self, class_selecting_function: Callable[[dict], type[Node]]
    ) -> None:
        """Set callback for dynamic node class selection.

        During deserialization, the callback receives serialized node data
        and returns the appropriate Node subclass to instantiate. Enables
        polymorphic node restoration.

        Args:
            class_selecting_function: Receives dict, returns Node class type.
        """
        self.node_class_selector = class_selecting_function

    def get_node_class_from_data(self, data: dict) -> type[Node]:
        """Determine Node class from serialized data.

        Uses registered selector callback if available, otherwise
        returns base Node class.

        Args:
            data: Serialized node data dictionary.

        Returns:
            Node class type to instantiate.
        """
        from oncutf.ui.widgets.node_editor.core.node import Node

        if self.node_class_selector is None:
            return Node
        return self.node_class_selector(data)

    # Snapshot serialization (IO-free)

    def serialize_snapshot(self) -> dict:
        """Convert scene state to an IO-free snapshot dictionary.

        Returns:
            Dictionary containing complete scene state.
        """
        nodes: list[dict] = []
        edges: list[dict] = []

        for node in self.nodes:
            newnode = node.serialize()
            if not any(newnode["sid"] == a["sid"] for a in nodes):
                nodes.append(newnode)

        for edge in self.edges:
            newedge = edge.serialize()
            if not any(newedge["sid"] == a["sid"] for a in edges):
                edges.append(newedge)

        return {
            "version": self.SNAPSHOT_VERSION,
            "sid": self.sid,
            "scene_width": self.scene_width,
            "scene_height": self.scene_height,
            "nodes": nodes,
            "edges": edges,
        }

    def serialize(self) -> dict:
        """Backward-compatible alias for :meth:`serialize_snapshot`."""

        return self.serialize_snapshot()

    def deserialize_snapshot(
        self, data: dict, hashmap: dict | None = None, restore_id: bool = True, *args, **kwargs
    ) -> bool:
        """Restore scene state from serialized dictionary.

        Intelligently reuses existing nodes and edges when IDs match,
        creating new instances only as needed. Removes items not present
        in the data.

        Args:
            data: Dictionary containing serialized scene data.
            hashmap: Maps original IDs to restored objects for references.
            restore_id: If True, restore original scene ID.
            *args: Additional arguments passed to item deserialize methods.
            **kwargs: Additional keyword arguments.

        Returns:
            True on successful deserialization.
        """
        if hashmap is None:
            hashmap = {}

        # Handle versioning and migrations
        version = data.get("version", "0.9.0")  # Legacy files have no version
        if version not in ("1.0.0", self.SNAPSHOT_VERSION):
            data = self._migrate_to_current_version(data, version)

        if restore_id and "sid" in data:
            self.sid = data["sid"]

        if "sid" in data:
            hashmap[data["sid"]] = self
        if "id" in data:
            hashmap[data["id"]] = self

        all_nodes = self.nodes.copy()

        for node_data in data["nodes"]:
            found = None
            for node in all_nodes:
                if "sid" in node_data and node.sid == node_data["sid"]:
                    found = node
                    break

            if not found:
                try:
                    node_class = self.get_node_class_from_data(node_data)
                    new_node = node_class(self)
                    new_node.deserialize(node_data, hashmap, restore_id, *args, **kwargs)
                    new_node.on_deserialized(node_data)
                except Exception as e:
                    dump_exception(e)
            else:
                try:
                    found.deserialize(node_data, hashmap, restore_id, *args, **kwargs)
                    found.on_deserialized(node_data)
                    all_nodes.remove(found)
                except Exception as e:
                    dump_exception(e)

        while all_nodes:
            node = all_nodes.pop()
            node.remove()

        all_edges = self.edges.copy()

        for edge_data in data["edges"]:
            found = None
            for edge in all_edges:
                if "sid" in edge_data and edge.sid == edge_data["sid"]:
                    found = edge
                    break

            if not found:
                edge_class = self.get_edge_class()
                new_edge = edge_class(self)
                new_edge.deserialize(edge_data, hashmap, restore_id, *args, **kwargs)
            else:
                found.deserialize(edge_data, hashmap, restore_id, *args, **kwargs)
                all_edges.remove(found)

        while all_edges:
            edge = all_edges.pop()
            edge.remove()

        return True

    def deserialize(
        self, data: dict, hashmap: dict | None = None, restore_id: bool = True, *args, **kwargs
    ) -> bool:
        """Backward-compatible alias for :meth:`deserialize_snapshot`."""

        return self.deserialize_snapshot(
            data, *args, hashmap=hashmap, restore_id=restore_id, **kwargs
        )

    def _migrate_to_current_version(self, data: dict, from_version: str) -> dict:  # noqa: ARG002
        """Migrate serialized data from old version to current format.

        Override this method in subclasses to handle version-specific migrations.

        Args:
            data: Serialized data in old format.
            from_version: Version string of the data (unused placeholder for future migrations).

        Returns:
            Migrated data dictionary.
        """
        # Placeholder for future migrations
        # Example:
        # if from_version < "1.0.0":
        #     data = self._migrate_0_9_to_1_0(data)
        return data
