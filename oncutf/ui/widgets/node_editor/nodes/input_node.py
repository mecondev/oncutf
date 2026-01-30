"""Input nodes for user data entry.

Provides NumberInput and TextInput nodes for entering values into the graph.

Author:
    Michael Economou

Date:
    2025-12-12
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLineEdit, QVBoxLayout

from oncutf.ui.widgets.node_editor.core.node import Node
from oncutf.ui.widgets.node_editor.core.socket import RIGHT_CENTER
from oncutf.ui.widgets.node_editor.graphics.node import QDMGraphicsNode
from oncutf.ui.widgets.node_editor.nodes.registry import NodeRegistry
from oncutf.ui.widgets.node_editor.widgets.content_widget import QDMNodeContentWidget


class InputGraphicsNode(QDMGraphicsNode):
    """Graphics node for input nodes with compact size."""

    def init_sizes(self):
        """Initialize size parameters for input nodes."""
        super().init_sizes()
        self.width = 180
        self.height = 90
        self.edge_roundness = 6
        self.edge_padding = 0
        self.title_horizontal_padding = 8
        self.title_vertical_padding = 10


class NumberInputContent(QDMNodeContentWidget):
    """Content widget with number input field."""

    def init_ui(self):
        """Initialize the number input field."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        self.setLayout(layout)

        self.edit = QLineEdit("0", self)
        self.edit.setAlignment(Qt.AlignRight)
        self.edit.setObjectName("node_input_edit")
        self.edit.textChanged.connect(self.on_value_changed)
        layout.addWidget(self.edit)

    def on_value_changed(self):
        """Handle value changes and trigger node evaluation."""
        if hasattr(self.node, "mark_dirty"):
            self.node.mark_dirty()
        if hasattr(self.node, "eval"):
            self.node.eval()

    def serialize(self):
        """Serialize the input value."""
        return {"value": self.edit.text()}

    def deserialize(self, data, hashmap=None):
        """Restore the input value."""
        _ = hashmap  # Unused
        if "value" in data:
            self.edit.setText(data["value"])
        return True


class TextInputContent(QDMNodeContentWidget):
    """Content widget with text input field."""

    def init_ui(self):
        """Initialize the text input field."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        self.setLayout(layout)

        self.edit = QLineEdit("", self)
        self.edit.setObjectName("node_input_edit")
        self.edit.textChanged.connect(self.on_value_changed)
        layout.addWidget(self.edit)

    def on_value_changed(self):
        """Handle value changes and trigger node evaluation."""
        if hasattr(self.node, "mark_dirty"):
            self.node.mark_dirty()
        if hasattr(self.node, "eval"):
            self.node.eval()

    def serialize(self):
        """Serialize the input value."""
        return {"value": self.edit.text()}

    def deserialize(self, data, hashmap=None):
        """Restore the input value."""
        _ = hashmap  # Unused
        if "value" in data:
            self.edit.setText(data["value"])
        return True


@NodeRegistry.register(1)
class NumberInputNode(Node):
    """Node for entering numeric values.

    Provides a text field for entering numbers. Outputs the parsed
    numeric value (float) to connected nodes.

    Op Code: 1
    Category: Input
    Inputs: None
    Outputs: 1 (numeric value)
    """

    icon = ""
    op_code = 1
    op_title = "Number Input"
    content_label = ""
    content_label_objname = "input_node"

    _graphics_node_class = InputGraphicsNode
    _content_widget_class = NumberInputContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a number input node.

        Args:
            scene: Parent scene containing this node.
            inputs: Unused, number input has no inputs.
            outputs: Output socket configuration (default: [1]).

        """
        _ = inputs  # Unused
        if outputs is None:
            outputs = [1]
        super().__init__(scene, self.__class__.op_title, inputs=[], outputs=outputs)

        self.value = 0.0
        self.mark_dirty()

    def init_settings(self):
        """Configure socket positions."""
        super().init_settings()
        self.output_socket_position = RIGHT_CENTER

    def eval(self) -> float:
        """Evaluate the node and parse the input value.

        Returns:
            float: Parsed numeric value, or 0.0 if invalid.

        """
        try:
            text = self.content.edit.text()
            self.value = float(text) if text else 0.0
            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip("")
        except ValueError:
            self.value = 0.0
            self.mark_invalid(True)
            self.graphics_node.setToolTip("Invalid number format")

        self.mark_descendants_dirty()
        self.eval_children()

        return self.value


@NodeRegistry.register(2)
class TextInputNode(Node):
    """Node for entering text values.

    Provides a text field for entering string values. Outputs the
    text string to connected nodes.

    Op Code: 2
    Category: Input
    Inputs: None
    Outputs: 1 (text string)
    """

    icon = ""
    op_code = 2
    op_title = "Text Input"
    content_label = ""
    content_label_objname = "input_node"

    _graphics_node_class = InputGraphicsNode
    _content_widget_class = TextInputContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a text input node.

        Args:
            scene: Parent scene containing this node.
            inputs: Unused, text input has no inputs.
            outputs: Output socket configuration (default: [1]).

        """
        _ = inputs  # Unused
        if outputs is None:
            outputs = [1]
        super().__init__(scene, self.__class__.op_title, inputs=[], outputs=outputs)

        self.value = ""
        self.mark_dirty()

    def init_settings(self):
        """Configure socket positions."""
        super().init_settings()
        self.output_socket_position = RIGHT_CENTER

    def eval(self):
        """Evaluate the node and get the input text.

        Returns:
            str: Text value from the input field.

        """
        self.value = self.content.edit.text()
        self.mark_dirty(False)
        self.mark_invalid(False)
        self.graphics_node.setToolTip("")

        self.mark_descendants_dirty()
        self.eval_children()

        return self.value
