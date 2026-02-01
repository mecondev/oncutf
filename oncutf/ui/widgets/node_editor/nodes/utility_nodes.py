"""Utility nodes for debugging and special operations.

Provides utility nodes: Constant, Print, Comment, Clamp, Random.

Author:
    Michael Economou

Date:
    2025-12-12
"""

import logging
import random
from typing import Any

from PyQt5.QtWidgets import QLabel, QLineEdit, QTextEdit

from oncutf.ui.widgets.node_editor.core.node import Node
from oncutf.ui.widgets.node_editor.core.socket import LEFT_CENTER, RIGHT_CENTER
from oncutf.ui.widgets.node_editor.graphics.node import QDMGraphicsNode
from oncutf.ui.widgets.node_editor.nodes.registry import NodeRegistry
from oncutf.ui.widgets.node_editor.widgets.content_widget import QDMNodeContentWidget

logger = logging.getLogger(__name__)


class UtilityGraphicsNode(QDMGraphicsNode):
    """Graphics node for utility nodes."""

    def init_sizes(self):
        """Initialize size parameters for utility nodes."""
        super().init_sizes()
        self.width = 180
        self.height = 100
        self.edge_roundness = 6
        self.edge_padding = 0
        self.title_horizontal_padding = 8
        self.title_vertical_padding = 10


class ConstantContent(QDMNodeContentWidget):
    """Content widget for constant value input."""

    def init_ui(self):
        """Initialize the input field."""
        self.edit = QLineEdit("0", self)
        self.edit.setObjectName("constant_edit")
        self.edit.textChanged.connect(self.node.on_input_changed)


class CommentContent(QDMNodeContentWidget):
    """Content widget for comment text."""

    def init_ui(self):
        """Initialize the comment text area."""
        self.edit = QTextEdit("Comment", self)
        self.edit.setObjectName("comment_edit")
        self.edit.setMaximumHeight(80)


class UtilityContent(QDMNodeContentWidget):
    """Content widget with simple label."""

    def init_ui(self):
        """Initialize the content label."""
        lbl = QLabel(self.node.content_label, self)
        lbl.setObjectName(self.node.content_label_objname)


@NodeRegistry.register(80)
class ConstantNode(Node):
    """Node for constant immutable value.

    Provides a constant value that can be set once and doesn't change.
    Useful for providing fixed parameters to other nodes.

    Op Code: 80
    Category: Utility
    Inputs: 0
    Outputs: 1 (constant value)
    """

    icon = ""
    op_code = 80
    op_title = "Constant"
    content_label = ""
    content_label_objname = "utility_constant"

    _graphics_node_class = UtilityGraphicsNode
    _content_widget_class = ConstantContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a constant node.

        Args:
            scene: Parent scene containing this node.
            inputs: Input socket configuration (default: []).
            outputs: Output socket configuration (default: [1]).

        """
        if inputs is None:
            inputs = []
        if outputs is None:
            outputs = [1]
        super().__init__(scene, self.__class__.op_title, inputs, outputs)

        self.value = 0
        self.mark_dirty()

    def init_settings(self):
        """Configure socket positions."""
        super().init_settings()
        self.output_socket_position = RIGHT_CENTER

    def on_input_changed(self, text):
        """Handle text input change.

        Args:
            text: New text value from input field.

        """
        self.mark_dirty()
        self.eval()

    def eval(self) -> Any:
        """Evaluate the constant value.

        Returns:
            Parsed value from input field (number or string).

        """
        try:
            text = self.content.edit.text()
            # Try to parse as number
            try:
                self.value = float(text)
                if self.value.is_integer():
                    self.value = int(self.value)
            except ValueError:
                # Keep as string
                self.value = text

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip("")

            self.mark_descendants_dirty()
            self.eval_children()
        except Exception as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {e!s}")
            return None
        else:
            return self.value

    def serialize(self):
        """Serialize node state.

        Returns:
            dict: Serialized node data with constant value.

        """
        res = super().serialize()
        res["value"] = self.content.edit.text()
        return res

    def deserialize(self, data, hashmap=None, restore_id=True, *args, **kwargs):
        """Deserialize node state.

        Args:
            data: Serialized node data.
            hashmap: ID mapping for node reconstruction.
            restore_id: Whether to restore original node ID.

        """
        if hashmap is None:
            hashmap = {}
        res = super().deserialize(data, hashmap, restore_id)
        try:
            value = data["value"]
            self.content.edit.setText(str(value))
            return True & res
        except Exception:
            return res


@NodeRegistry.register(81)
class PrintNode(Node):
    """Node for debug output to console.

    Prints input value to console/logger and passes it through.
    Useful for debugging node graphs.

    Op Code: 81
    Category: Utility
    Inputs: 1 (value to print)
    Outputs: 1 (same value, pass-through)
    """

    icon = ""
    op_code = 81
    op_title = "Print"
    content_label = "🖨️"
    content_label_objname = "utility_print"

    _graphics_node_class = UtilityGraphicsNode
    _content_widget_class = UtilityContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a print node.

        Args:
            scene: Parent scene containing this node.
            inputs: Input socket configuration (default: [1]).
            outputs: Output socket configuration (default: [1]).

        """
        if inputs is None:
            inputs = [1]
        if outputs is None:
            outputs = [1]
        super().__init__(scene, self.__class__.op_title, inputs, outputs)

        self.value = None
        self.mark_dirty()

    def init_settings(self):
        """Configure socket positions."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def eval(self) -> Any:
        """Evaluate the print operation.

        Prints input value and passes it through.

        Returns:
            Input value (pass-through).

        """
        input_node = self.get_input(0)

        if input_node is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect input")
            return None

        try:
            value = input_node.eval()
            self.value = value

            logger.info("PrintNode %s output %s", self.id, self.value)

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip(f"Output: {self.value}")

            self.mark_descendants_dirty()
            self.eval_children()
        except Exception as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {e!s}")
            return None
        else:
            return self.value


@NodeRegistry.register(82)
class CommentNode(Node):
    """Node for annotations and notes.

    Provides a text area for adding comments to the node graph.
    Has no inputs or outputs, purely for documentation.

    Op Code: 82
    Category: Utility
    Inputs: 0
    Outputs: 0
    """

    icon = ""
    op_code = 82
    op_title = "Comment"
    content_label = ""
    content_label_objname = "utility_comment"

    _graphics_node_class = UtilityGraphicsNode
    _content_widget_class = CommentContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a comment node.

        Args:
            scene: Parent scene containing this node.
            inputs: Input socket configuration (default: []).
            outputs: Output socket configuration (default: []).

        """
        if inputs is None:
            inputs = []
        if outputs is None:
            outputs = []
        super().__init__(scene, self.__class__.op_title, inputs, outputs)

    def eval(self) -> Any:
        """Comment nodes don't evaluate.

        Returns:
            None: Comments are not evaluated.

        """
        return None

    def serialize(self):
        """Serialize node state.

        Returns:
            dict: Serialized node data with comment text.

        """
        res = super().serialize()
        res["comment"] = self.content.edit.toPlainText()
        return res

    def deserialize(self, data, hashmap=None, restore_id=True, *args, **kwargs):
        """Deserialize node state.

        Args:
            data: Serialized node data.
            hashmap: ID mapping for node reconstruction.
            restore_id: Whether to restore original node ID.

        """
        if hashmap is None:
            hashmap = {}
        res = super().deserialize(data, hashmap, restore_id)
        try:
            comment = data["comment"]
            self.content.edit.setPlainText(comment)
            return True & res
        except Exception:
            return res


@NodeRegistry.register(83)
class ClampNode(Node):
    """Node for clamping value to range.

    Restricts input value to be within [min, max] range.

    Op Code: 83
    Category: Utility
    Inputs: 3 (value, min, max)
    Outputs: 1 (clamped value)
    """

    icon = ""
    op_code = 83
    op_title = "Clamp"
    content_label = "⊓⊔"
    content_label_objname = "utility_clamp"

    _graphics_node_class = UtilityGraphicsNode
    _content_widget_class = UtilityContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a clamp node.

        Args:
            scene: Parent scene containing this node.
            inputs: Input socket configuration (default: [1, 1, 1]).
            outputs: Output socket configuration (default: [1]).

        """
        if inputs is None:
            inputs = [1, 1, 1]  # value, min, max
        if outputs is None:
            outputs = [1]
        super().__init__(scene, self.__class__.op_title, inputs, outputs)

        self.value = None
        self.mark_dirty()

    def init_settings(self):
        """Configure socket positions."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def eval(self) -> Any:
        """Evaluate the clamp operation.

        Returns:
            float: Value clamped to [min, max] range.

        """
        value_node = self.get_input(0)
        min_node = self.get_input(1)
        max_node = self.get_input(2)

        if value_node is None or min_node is None or max_node is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect all inputs")
            return None

        try:
            value = float(value_node.eval())
            min_val = float(min_node.eval())
            max_val = float(max_node.eval())

            # Ensure min <= max
            if min_val > max_val:
                min_val, max_val = max_val, min_val

            # Clamp value
            self.value = max(min_val, min(max_val, value))

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip(f"Clamped: {self.value}")

            self.mark_descendants_dirty()
            self.eval_children()
        except (ValueError, TypeError) as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {e!s}")
            return None
        else:
            return self.value


@NodeRegistry.register(84)
class RandomNode(Node):
    """Node for random number generation.

    Generates a random number between min and max (inclusive).

    Op Code: 84
    Category: Utility
    Inputs: 2 (min, max)
    Outputs: 1 (random number)
    """

    icon = ""
    op_code = 84
    op_title = "Random"
    content_label = "🎲"
    content_label_objname = "utility_random"

    _graphics_node_class = UtilityGraphicsNode
    _content_widget_class = UtilityContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a random node.

        Args:
            scene: Parent scene containing this node.
            inputs: Input socket configuration (default: [1, 1]).
            outputs: Output socket configuration (default: [1]).

        """
        if inputs is None:
            inputs = [1, 1]  # min, max
        if outputs is None:
            outputs = [1]
        super().__init__(scene, self.__class__.op_title, inputs, outputs)

        self.value = None
        self.mark_dirty()

    def init_settings(self):
        """Configure socket positions."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def eval(self) -> Any:
        """Evaluate the random operation.

        Returns:
            float: Random number between min and max.

        """
        min_node = self.get_input(0)
        max_node = self.get_input(1)

        if min_node is None or max_node is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect all inputs")
            return None

        try:
            min_val = float(min_node.eval())
            max_val = float(max_node.eval())

            # Ensure min <= max
            if min_val > max_val:
                min_val, max_val = max_val, min_val

            # Generate random number
            self.value = random.uniform(min_val, max_val)

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip(f"Random: {self.value:.2f}")

            self.mark_descendants_dirty()
            self.eval_children()
        except (ValueError, TypeError) as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {e!s}")
            return None
        else:
            return self.value
