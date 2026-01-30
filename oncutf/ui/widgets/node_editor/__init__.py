"""Node Editor - A PyQt5 framework for building node-based visual editors.

This package provides a complete, extensible node editor framework for creating
visual programming interfaces, data flow graphs, and node-based tools.

Core Components:
    Node: Base class for graph nodes with input/output sockets.
    Edge: Connections between node sockets.
    Socket: Connection points on nodes (inputs/outputs).
    Scene: Container managing nodes, edges, and their interactions.

Widget Components:
    NodeEditorWidget: Embeddable widget containing scene and view.
    NodeEditorWindow: Complete standalone window with menus and toolbar.

Extension Points:
    Node: Subclass core.Node to create custom node types.
    NodeRegistry: Register custom nodes with operation codes.
    ThemeEngine: Customize visual appearance.

Example:
    Embedding in an application::

        from node_editor import NodeEditorWidget
        widget = NodeEditorWidget(parent)
        layout.addWidget(widget)

    Creating custom nodes::

        from oncutf.ui.widgets.node_editor.core import Node
        from oncutf.ui.widgets.node_editor.nodes import NodeRegistry

        @NodeRegistry.register(100)
        class MyNode(Node):
            op_code = 100
            op_title = "My Custom Node"

Author:
    Michael Economou

Date:
    2025-12-11

"""

__version__ = "1.0.0"
__author__ = "Michael Economou"

# Initialize graphics class bindings (must be done before using widgets)
# Initialize graphics class bindings (must be done before using widgets)
from oncutf.ui.widgets.node_editor.core import (
    Edge,
    Node,
    Scene,
    Socket,
    _init_graphics_classes,
)

# Node system
from oncutf.ui.widgets.node_editor.nodes import NodeRegistry

# Theme engine
from oncutf.ui.widgets.node_editor.themes import ThemeEngine
from oncutf.ui.widgets.node_editor.themes.dark import DarkTheme
from oncutf.ui.widgets.node_editor.themes.light import LightTheme

# Widgets
from oncutf.ui.widgets.node_editor.widgets import NodeEditorWidget, NodeEditorWindow

_init_graphics_classes()

__all__ = [
    "DarkTheme",
    "Edge",
    "LightTheme",
    # Core
    "Node",
    # Widgets
    "NodeEditorWidget",
    "NodeEditorWindow",
    # Nodes
    "NodeRegistry",
    "Scene",
    "Socket",
    # Themes
    "ThemeEngine",
    "__version__",
]
