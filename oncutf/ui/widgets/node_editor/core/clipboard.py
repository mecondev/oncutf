"""Copy/paste clipboard operations for scene elements.

This module implements the SceneClipboard class providing copy, cut, and
paste functionality for nodes and edges. Selected elements are serialized
to a dictionary format that can be pasted back into the scene at a new
position.

The clipboard handles:
    - Serialization of selected nodes and edges
    - Position offset calculation for paste operations
    - Edge filtering (only edges with both endpoints selected are copied)
    - Cut operations (copy then delete)

Author:
    Michael Economou

Date:
    2025-12-11
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oncutf.ui.widgets.node_editor.core.scene import Scene


class SceneClipboard:
    """Clipboard manager for scene copy/paste operations.

    Handles serialization of selected nodes and edges for copy/cut,
    and deserialization for paste operations. Manages position offsets
    to paste elements relative to mouse cursor.

    Attributes:
        scene: Parent Scene for clipboard operations.

    """

    def __init__(self, scene: Scene) -> None:
        """Initialize clipboard for a scene.

        Args:
            scene: Scene instance to operate on.

        """
        self.scene = scene

    def serialize_selected(self, delete: bool = False) -> dict:
        """Serialize currently selected nodes and edges.

        Captures all selected nodes and edges that are fully contained
        within the selection (edges with only one selected endpoint are
        excluded).

        Args:
            delete: If True, delete selection after serializing (cut).

        Returns:
            Dictionary with 'nodes' and 'edges' lists of serialized data.

        """
        sel_nodes = []
        sel_edges = []
        sel_sockets = {}

        for item in self.scene.graphics_scene.selectedItems():
            if hasattr(item, "node"):
                sel_nodes.append(item.node.serialize())
                for socket in item.node.inputs + item.node.outputs:
                    sel_sockets[socket.sid] = socket
            elif hasattr(item, "edge"):
                from oncutf.ui.widgets.node_editor.graphics.edge import QDMGraphicsEdge

                if isinstance(item, QDMGraphicsEdge):
                    sel_edges.append(item.edge)

        edges_to_remove = []
        for edge in sel_edges:
            if edge.start_socket.sid in sel_sockets and edge.end_socket.sid in sel_sockets:
                pass
            else:
                edges_to_remove.append(edge)

        for edge in edges_to_remove:
            sel_edges.remove(edge)

        edges_final = [edge.serialize() for edge in sel_edges]

        data = {
            "nodes": sel_nodes,
            "edges": edges_final,
        }

        if delete:
            self.scene._get_graphics_view().delete_selected()
            self.scene.history.store_history("Cut out elements from scene", set_modified=True)

        return data

    def deserialize_from_clipboard(self, data: dict, *args: object, **kwargs: object) -> None:
        """Paste clipboard data into the scene.

        Creates new nodes and edges from serialized data, positioning
        them relative to current mouse cursor. New IDs are generated
        for all pasted elements.

        Args:
            data: Dictionary with 'nodes' and 'edges' from serialize_selected.
            *args: Additional arguments passed to deserialize methods.
            **kwargs: Additional keyword arguments.

        """
        hashmap = {}

        view = self.scene._get_graphics_view()
        mouse_scene_pos = view.last_scene_mouse_position

        minx = maxx = miny = maxy = None

        for node_data in data["nodes"]:
            if "pos_x" in node_data and "pos_y" in node_data:
                x, y = node_data["pos_x"], node_data["pos_y"]
            else:
                x, y = node_data["pos"]

            if minx is None or x < minx:
                minx = x
            if maxx is None or x > maxx:
                maxx = x
            if miny is None or y < miny:
                miny = y
            if maxy is None or y > maxy:
                maxy = y

        if maxx is not None:
            maxx -= 180
        if maxy is not None:
            maxy += 100

        (minx + maxx) / 2 - minx if minx is not None and maxx is not None else 0

        (miny + maxy) / 2 - miny if miny is not None and maxy is not None else 0

        mousex = mouse_scene_pos.x()
        mousey = mouse_scene_pos.y()

        self.scene.set_silent_selection_events()
        self.scene.deselect_all()

        created_nodes = []

        for node_data in data["nodes"]:
            node_class = self.scene.get_node_class_from_data(node_data)
            new_node = node_class(self.scene)
            new_node.deserialize(node_data, hashmap, *args, restore_id=False, **kwargs)
            created_nodes.append(new_node)

            posx = new_node.pos.x()
            posy = new_node.pos.y()

            if minx is not None and miny is not None:
                newx = mousex + posx - minx
                newy = mousey + posy - miny
            else:
                newx = posx
                newy = posy

            new_node.set_pos(newx, newy)
            new_node.do_select()

        if "edges" in data:
            from oncutf.ui.widgets.node_editor.core.edge import Edge

            for edge_data in data["edges"]:
                new_edge = Edge(self.scene)
                new_edge.deserialize(edge_data, hashmap, *args, restore_id=False, **kwargs)

        self.scene.set_silent_selection_events(False)

        self.scene.history.store_history("Pasted elements in scene", set_modified=True)
