"""Core module - Contains fundamental classes for the node editor.

Classes:
    - Serializable: Base class for serialization
    - Socket: Connection point on nodes
    - Node: Base node class
    - Edge: Connection between sockets
    - Scene: Container for nodes and edges (to be migrated)

Enums:
    - SocketPosition: Socket position constants
    - EdgeType: Edge path style constants

Author: Michael Economou
Date: 2025-12-11
"""

from oncutf.ui.widgets.node_editor.core.edge import (
    EDGE_TYPE_BEZIER,
    EDGE_TYPE_DEFAULT,
    EDGE_TYPE_DIRECT,
    EDGE_TYPE_IMPROVED_BEZIER,
    EDGE_TYPE_IMPROVED_SHARP,
    EDGE_TYPE_SQUARE,
    Edge,
    EdgeType,
)
from oncutf.ui.widgets.node_editor.core.node import Node
from oncutf.ui.widgets.node_editor.core.serializable import Serializable
from oncutf.ui.widgets.node_editor.core.socket import (
    LEFT_BOTTOM,
    LEFT_CENTER,
    LEFT_TOP,
    RIGHT_BOTTOM,
    RIGHT_CENTER,
    RIGHT_TOP,
    Socket,
    SocketPosition,
)


# Late binding for graphics classes to avoid circular imports
def _init_graphics_classes():
    """Initialize graphics class references."""
    from oncutf.ui.widgets.node_editor.graphics.edge import QDMGraphicsEdge
    from oncutf.ui.widgets.node_editor.graphics.node import QDMGraphicsNode
    from oncutf.ui.widgets.node_editor.graphics.socket import QDMGraphicsSocket
    from oncutf.ui.widgets.node_editor.widgets.content_widget import QDMNodeContentWidget

    Socket._graphics_socket_class = QDMGraphicsSocket
    Node._graphics_node_class = QDMGraphicsNode
    Node._content_widget_class = QDMNodeContentWidget
    Edge._graphics_edge_class = QDMGraphicsEdge


# NOTE: Graphics classes are initialized lazily on first use
# to avoid circular import issues at module initialization time
# _init_graphics_classes()

__all__ = [
    "EDGE_TYPE_BEZIER",
    "EDGE_TYPE_DEFAULT",
    "EDGE_TYPE_DIRECT",
    "EDGE_TYPE_IMPROVED_BEZIER",
    "EDGE_TYPE_IMPROVED_SHARP",
    "EDGE_TYPE_SQUARE",
    "LEFT_BOTTOM",
    "LEFT_CENTER",
    "LEFT_TOP",
    "RIGHT_BOTTOM",
    "RIGHT_CENTER",
    "RIGHT_TOP",
    "Edge",
    "EdgeType",
    "Node",
    "Serializable",
    "Socket",
    "SocketPosition",
]
