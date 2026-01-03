"""Output nodes for displaying computed results.

Provides OutputNode for displaying values at graph endpoints.

Author:
    Michael Economou

Date:
    2025-12-12
"""

from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QVBoxLayout

from oncutf.ui.widgets.node_editor.core.node import Node
from oncutf.ui.widgets.node_editor.core.socket import LEFT_CENTER
from oncutf.ui.widgets.node_editor.graphics.node import QDMGraphicsNode
from oncutf.ui.widgets.node_editor.nodes.registry import NodeRegistry
from oncutf.ui.widgets.node_editor.widgets.content_widget import QDMNodeContentWidget


class OutputGraphicsNode(QDMGraphicsNode):
    """Graphics node for output nodes with compact size."""

    def init_sizes(self):
        """Initialize size parameters for output nodes."""
        super().init_sizes()
        self.width = 180
        self.height = 90
        self.edge_roundness = 6
        self.edge_padding = 0
        self.title_horizontal_padding = 8
        self.title_vertical_padding = 10


class OutputContent(QDMNodeContentWidget):
    """Content widget with result display label."""

    def init_ui(self):
        """Initialize the output display label."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        self.setLayout(layout)

        self.label = QLabel("---", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setObjectName("node_output_label")
        layout.addWidget(self.label)

    def set_value(self, value):
        """Update the displayed value.

        Args:
            value: Value to display (will be converted to string).
        """
        if value is None:
            self.label.setText("---")
        else:
            self.label.setText(str(value))


@NodeRegistry.register(3)
class OutputNode(Node):
    """Node for displaying computation results.

    Shows the value from a connected input node. Typically used as
    a graph endpoint to visualize final results.

    Op Code: 3
    Category: Output
    Inputs: 1 (any value)
    Outputs: None
    """

    icon = ""
    op_code = 3
    op_title = "Output"
    content_label = ""
    content_label_objname = "output_node"

    _graphics_node_class = OutputGraphicsNode
    _content_widget_class = OutputContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create an output node.

        Args:
            scene: Parent scene containing this node.
            inputs: Input socket configuration (default: [1]).
            outputs: Unused, output node has no outputs.
        """
        _ = outputs  # Unused
        if inputs is None:
            inputs = [1]
        super().__init__(scene, self.__class__.op_title, inputs=inputs, outputs=[])

        self.value = None
        self.mark_dirty()

    def init_settings(self):
        """Configure socket positions."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER

    def eval(self) -> Any:
        """Evaluate the node and display the input value.

        Returns:
            The input value, or None if not connected.
        """
        input_node = self.get_input(0)

        if input_node is None:
            self.value = None
            self.content.set_value(None)
            self.mark_invalid(True)
            self.graphics_node.setToolTip("Connect an input")
            return None

        # Get value from connected node
        self.value = input_node.eval()
        self.content.set_value(self.value)

        self.mark_dirty(False)
        self.mark_invalid(False)
        self.graphics_node.setToolTip("")

        return self.value
