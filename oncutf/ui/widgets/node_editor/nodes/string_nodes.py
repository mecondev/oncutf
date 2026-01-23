"""String operation nodes.

Provides string manipulation operations: concatenate, format, length, substring, split.

Author:
    Michael Economou

Date:
    2025-12-12
"""

from typing import Any

from PyQt5.QtWidgets import QLabel

from oncutf.ui.widgets.node_editor.core.node import Node
from oncutf.ui.widgets.node_editor.core.socket import LEFT_CENTER, RIGHT_CENTER
from oncutf.ui.widgets.node_editor.graphics.node import QDMGraphicsNode
from oncutf.ui.widgets.node_editor.nodes.registry import NodeRegistry
from oncutf.ui.widgets.node_editor.widgets.content_widget import QDMNodeContentWidget


class StringGraphicsNode(QDMGraphicsNode):
    """Graphics node for string operation nodes."""

    def init_sizes(self):
        """Initialize size parameters for string nodes."""
        super().init_sizes()
        self.width = 160
        self.height = 74
        self.edge_roundness = 6
        self.edge_padding = 0
        self.title_horizontal_padding = 8
        self.title_vertical_padding = 10


class StringContent(QDMNodeContentWidget):
    """Content widget with operation label."""

    def init_ui(self):
        """Initialize the content label."""
        lbl = QLabel(self.node.content_label, self)
        lbl.setObjectName(self.node.content_label_objname)


@NodeRegistry.register(40)
class ConcatenateNode(Node):
    """Node for concatenating two strings.

    Joins two string values together (a + b).

    Op Code: 40
    Category: String
    Inputs: 2 (string values)
    Outputs: 1 (concatenated string)
    """

    icon = ""
    op_code = 40
    op_title = "Concatenate"
    content_label = "+"
    content_label_objname = "string_node_concat"

    _graphics_node_class = StringGraphicsNode
    _content_widget_class = StringContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a concatenate node.

        Args:
            scene: Parent scene containing this node.
            inputs: Input socket configuration (default: [1, 1]).
            outputs: Output socket configuration (default: [1]).

        """
        if inputs is None:
            inputs = [1, 1]
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
        """Evaluate the concatenate operation.

        Returns:
            str: Concatenated string, or None if inputs are invalid.

        """
        i1 = self.get_input(0)
        i2 = self.get_input(1)

        if i1 is None or i2 is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect all inputs")
            return None

        try:
            val1 = str(i1.eval())
            val2 = str(i2.eval())

            self.value = val1 + val2
            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip("")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except (ValueError, TypeError) as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {e!s}")
            return None


@NodeRegistry.register(41)
class FormatNode(Node):
    """Node for string formatting.

    Formats a string using the first input as template and the second as value.
    Example: "Value: {}" with 42 -> "Value: 42"

    Op Code: 41
    Category: String
    Inputs: 2 (format template, value)
    Outputs: 1 (formatted string)
    """

    icon = ""
    op_code = 41
    op_title = "Format"
    content_label = "{}"
    content_label_objname = "string_node_format"

    _graphics_node_class = StringGraphicsNode
    _content_widget_class = StringContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a format node.

        Args:
            scene: Parent scene containing this node.
            inputs: Input socket configuration (default: [1, 1]).
            outputs: Output socket configuration (default: [1]).

        """
        if inputs is None:
            inputs = [1, 1]
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
        """Evaluate the format operation.

        Returns:
            str: Formatted string, or None if inputs are invalid.

        """
        i1 = self.get_input(0)
        i2 = self.get_input(1)

        if i1 is None or i2 is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect all inputs")
            return None

        try:
            template = str(i1.eval())
            value = i2.eval()

            # Support both {} and {0} placeholders
            if "{}" in template:
                self.value = template.replace("{}", str(value), 1)
            else:
                self.value = template.format(value)

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip("")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except (ValueError, TypeError, KeyError) as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Format error: {e!s}")
            return None


@NodeRegistry.register(42)
class LengthNode(Node):
    """Node for getting string or list length.

    Returns the length of a string or the number of elements in a list.

    Op Code: 42
    Category: String
    Inputs: 1 (string or list)
    Outputs: 1 (length as number)
    """

    icon = ""
    op_code = 42
    op_title = "Length"
    content_label = "len"
    content_label_objname = "string_node_length"

    _graphics_node_class = StringGraphicsNode
    _content_widget_class = StringContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a length node.

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
        """Evaluate the length operation.

        Returns:
            int: Length of input, or None if input is invalid.

        """
        i1 = self.get_input(0)

        if i1 is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect input")
            return None

        try:
            value = i1.eval()

            # Get length of string, list, or other sequence
            self.value = len(value)

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip("")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except (TypeError, AttributeError) as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Cannot get length: {e!s}")
            return None


@NodeRegistry.register(43)
class SubstringNode(Node):
    """Node for extracting a substring.

    Extracts a substring from start to end index (Python slicing).

    Op Code: 43
    Category: String
    Inputs: 3 (string, start index, end index)
    Outputs: 1 (substring)
    """

    icon = ""
    op_code = 43
    op_title = "Substring"
    content_label = "[::]"
    content_label_objname = "string_node_substring"

    _graphics_node_class = StringGraphicsNode
    _content_widget_class = StringContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a substring node.

        Args:
            scene: Parent scene containing this node.
            inputs: Input socket configuration (default: [1, 1, 1]).
            outputs: Output socket configuration (default: [1]).

        """
        if inputs is None:
            inputs = [1, 1, 1]  # string, start, end
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
        """Evaluate the substring operation.

        Returns:
            str: Extracted substring, or None if inputs are invalid.

        """
        string_node = self.get_input(0)
        start_node = self.get_input(1)
        end_node = self.get_input(2)

        if string_node is None or start_node is None or end_node is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect all inputs")
            return None

        try:
            string = str(string_node.eval())
            start = int(start_node.eval())
            end = int(end_node.eval())

            self.value = string[start:end]

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip("")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except (ValueError, TypeError, IndexError) as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Substring error: {e!s}")
            return None


@NodeRegistry.register(44)
class SplitNode(Node):
    """Node for splitting a string.

    Splits a string by a delimiter into a list of strings.

    Op Code: 44
    Category: String
    Inputs: 2 (string, delimiter)
    Outputs: 1 (list of strings)
    """

    icon = ""
    op_code = 44
    op_title = "Split"
    content_label = "split"
    content_label_objname = "string_node_split"

    _graphics_node_class = StringGraphicsNode
    _content_widget_class = StringContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a split node.

        Args:
            scene: Parent scene containing this node.
            inputs: Input socket configuration (default: [1, 1]).
            outputs: Output socket configuration (default: [1]).

        """
        if inputs is None:
            inputs = [1, 1]  # string, delimiter
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
        """Evaluate the split operation.

        Returns:
            list: List of string parts, or None if inputs are invalid.

        """
        string_node = self.get_input(0)
        delimiter_node = self.get_input(1)

        if string_node is None or delimiter_node is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect all inputs")
            return None

        try:
            string = str(string_node.eval())
            delimiter = str(delimiter_node.eval())

            # If delimiter is empty, split by whitespace
            if not delimiter:
                self.value = string.split()
            else:
                self.value = string.split(delimiter)

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip("")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except (ValueError, TypeError) as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Split error: {e!s}")
            return None
