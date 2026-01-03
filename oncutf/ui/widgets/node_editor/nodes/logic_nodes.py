"""Logic and comparison nodes.

Provides comparison, conditional logic, and boolean operations.

Comparison: Equal, NotEqual, <, <=, >, >=
Conditional: If/Switch
Boolean: AND, OR, NOT, XOR

Author:
    Michael Economou

Date:
    2025-12-12
"""

from PyQt5.QtWidgets import QLabel

from oncutf.ui.widgets.node_editor.core.node import Node
from oncutf.ui.widgets.node_editor.core.socket import LEFT_CENTER, RIGHT_CENTER
from oncutf.ui.widgets.node_editor.graphics.node import QDMGraphicsNode
from oncutf.ui.widgets.node_editor.nodes.registry import NodeRegistry
from oncutf.ui.widgets.node_editor.widgets.content_widget import QDMNodeContentWidget


class LogicGraphicsNode(QDMGraphicsNode):
    """Graphics node for logic operation nodes."""

    def init_sizes(self):
        """Initialize size parameters for logic nodes."""
        super().init_sizes()
        self.width = 160
        self.height = 74
        self.edge_roundness = 6
        self.edge_padding = 0
        self.title_horizontal_padding = 8
        self.title_vertical_padding = 10


class LogicContent(QDMNodeContentWidget):
    """Content widget with operation label."""

    def init_ui(self):
        """Initialize the content label."""
        lbl = QLabel(self.node.content_label, self)
        lbl.setObjectName(self.node.content_label_objname)


class CompareNode(Node):
    """Base class for comparison operation nodes.

    Subclass this and override compareOperation() to implement
    specific comparison operations.
    """

    icon = ""
    op_code = 0
    op_title = "Compare"
    content_label = ""
    content_label_objname = "logic_node"

    _graphics_node_class = LogicGraphicsNode
    _content_widget_class = LogicContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a comparison node.

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

    def compare_operation(self, input1, input2):
        """Perform the comparison operation.

        Override this method in subclasses to implement specific comparisons.

        Args:
            input1: First value to compare.
            input2: Second value to compare.

        Returns:
            bool: Result of the comparison.
        """
        _ = input1, input2  # Unused in base class
        return False

    def eval(self) -> bool | None:
        """Evaluate the comparison node.

        Gets values from both inputs, performs the comparison,
        and returns a boolean result.

        Returns:
            bool: Comparison result, or None if inputs are invalid.
        """
        i1 = self.get_input(0)
        i2 = self.get_input(1)

        if i1 is None or i2 is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect all inputs")
            return None

        try:
            val1 = i1.eval()
            val2 = i2.eval()

            self.value = self.compare_operation(val1, val2)
            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip("")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except (ValueError, TypeError) as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {str(e)}")
            return None


@NodeRegistry.register(20)
class EqualNode(CompareNode):
    """Node for equality comparison (==).

    Op Code: 20
    Category: Logic
    Inputs: 2 (any values)
    Outputs: 1 (boolean)
    """

    op_code = 20
    op_title = "Equal"
    content_label = "=="
    content_label_objname = "logic_node_eq"

    def compare_operation(self, input1, input2):
        """Check if two values are equal.

        Args:
            input1: First value.
            input2: Second value.

        Returns:
            bool: True if values are equal.
        """
        return input1 == input2


@NodeRegistry.register(21)
class NotEqualNode(CompareNode):
    """Node for inequality comparison (!=).

    Op Code: 21
    Category: Logic
    Inputs: 2 (any values)
    Outputs: 1 (boolean)
    """

    op_code = 21
    op_title = "Not Equal"
    content_label = "!="
    content_label_objname = "logic_node_neq"

    def compare_operation(self, input1, input2):
        """Check if two values are not equal.

        Args:
            input1: First value.
            input2: Second value.

        Returns:
            bool: True if values are not equal.
        """
        return input1 != input2


@NodeRegistry.register(22)
class LessThanNode(CompareNode):
    """Node for less-than comparison (<).

    Op Code: 22
    Category: Logic
    Inputs: 2 (comparable values)
    Outputs: 1 (boolean)
    """

    op_code = 22
    op_title = "Less Than"
    content_label = "<"
    content_label_objname = "logic_node_lt"

    def compare_operation(self, input1, input2):
        """Check if first value is less than second.

        Args:
            input1: First value.
            input2: Second value.

        Returns:
            bool: True if input1 < input2.
        """
        return input1 < input2


@NodeRegistry.register(23)
class LessEqualNode(CompareNode):
    """Node for less-than-or-equal comparison (<=).

    Op Code: 23
    Category: Logic
    Inputs: 2 (comparable values)
    Outputs: 1 (boolean)
    """

    op_code = 23
    op_title = "Less or Equal"
    content_label = "<="
    content_label_objname = "logic_node_le"

    def compare_operation(self, input1, input2):
        """Check if first value is less than or equal to second.

        Args:
            input1: First value.
            input2: Second value.

        Returns:
            bool: True if input1 <= input2.
        """
        return input1 <= input2


@NodeRegistry.register(24)
class GreaterThanNode(CompareNode):
    """Node for greater-than comparison (>).

    Op Code: 24
    Category: Logic
    Inputs: 2 (comparable values)
    Outputs: 1 (boolean)
    """

    op_code = 24
    op_title = "Greater Than"
    content_label = ">"
    content_label_objname = "logic_node_gt"

    def compare_operation(self, input1, input2):
        """Check if first value is greater than second.

        Args:
            input1: First value.
            input2: Second value.

        Returns:
            bool: True if input1 > input2.
        """
        return input1 > input2


@NodeRegistry.register(25)
class GreaterEqualNode(CompareNode):
    """Node for greater-than-or-equal comparison (>=).

    Op Code: 25
    Category: Logic
    Inputs: 2 (comparable values)
    Outputs: 1 (boolean)
    """

    op_code = 25
    op_title = "Greater or Equal"
    content_label = ">="
    content_label_objname = "logic_node_ge"

    def compare_operation(self, input1, input2):
        """Check if first value is greater than or equal to second.

        Args:
            input1: First value.
            input2: Second value.

        Returns:
            bool: True if input1 >= input2.
        """
        return input1 >= input2


@NodeRegistry.register(30)
class IfNode(Node):
    """Conditional switch node.

    Outputs one of two input values based on a boolean condition.
    If condition is True, outputs value from input 1 (true_value).
    If condition is False, outputs value from input 2 (false_value).

    Op Code: 30
    Category: Logic
    Inputs: 3 (condition, true_value, false_value)
    Outputs: 1 (selected value)
    """

    icon = ""
    op_code = 30
    op_title = "If / Switch"
    content_label = "?"
    content_label_objname = "logic_node_if"

    _graphics_node_class = LogicGraphicsNode
    _content_widget_class = LogicContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create an if/switch node.

        Args:
            scene: Parent scene containing this node.
            inputs: Input socket configuration (default: [1, 1, 1]).
            outputs: Output socket configuration (default: [1]).
        """
        if inputs is None:
            inputs = [1, 1, 1]  # condition, true_value, false_value
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

    def eval(self):
        """Evaluate the if/switch node.

        Returns:
            Value from true_value input if condition is True,
            value from false_value input if condition is False,
            or None if inputs are invalid.
        """
        condition_node = self.get_input(0)
        true_node = self.get_input(1)
        false_node = self.get_input(2)

        if condition_node is None or true_node is None or false_node is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect all inputs")
            return None

        try:
            condition = condition_node.eval()
            true_value = true_node.eval()
            false_value = false_node.eval()

            # Select output based on condition
            self.value = true_value if condition else false_value

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip("")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except (ValueError, TypeError) as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {str(e)}")
            return None


# =============================================================================
# Boolean Logic Operations
# =============================================================================


@NodeRegistry.register(60)
class AndNode(Node):
    """Node for logical AND operation.

    Returns True if both inputs are truthy.

    Op Code: 60
    Category: Logic
    Inputs: 2 (boolean/values)
    Outputs: 1 (boolean)
    """

    icon = ""
    op_code = 60
    op_title = "AND"
    content_label = "&&"
    content_label_objname = "logic_and"

    _graphics_node_class = LogicGraphicsNode
    _content_widget_class = LogicContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create an AND node.

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

    def eval(self):
        """Evaluate the AND operation.

        Returns:
            bool: True if both inputs are truthy, or None if invalid.
        """
        i1 = self.get_input(0)
        i2 = self.get_input(1)

        if i1 is None or i2 is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect all inputs")
            return None

        try:
            val1 = i1.eval()
            val2 = i2.eval()

            self.value = bool(val1) and bool(val2)

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip("")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except (ValueError, TypeError) as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {str(e)}")
            return None


@NodeRegistry.register(61)
class OrNode(Node):
    """Node for logical OR operation.

    Returns True if at least one input is truthy.

    Op Code: 61
    Category: Logic
    Inputs: 2 (boolean/values)
    Outputs: 1 (boolean)
    """

    icon = ""
    op_code = 61
    op_title = "OR"
    content_label = "||"
    content_label_objname = "logic_or"

    _graphics_node_class = LogicGraphicsNode
    _content_widget_class = LogicContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create an OR node.

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

    def eval(self):
        """Evaluate the OR operation.

        Returns:
            bool: True if any input is truthy, or None if invalid.
        """
        i1 = self.get_input(0)
        i2 = self.get_input(1)

        if i1 is None or i2 is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect all inputs")
            return None

        try:
            val1 = i1.eval()
            val2 = i2.eval()

            self.value = bool(val1) or bool(val2)

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip("")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except (ValueError, TypeError) as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {str(e)}")
            return None


@NodeRegistry.register(62)
class NotNode(Node):
    """Node for logical NOT operation.

    Returns the negation of the input boolean value.

    Op Code: 62
    Category: Logic
    Inputs: 1 (boolean/value)
    Outputs: 1 (boolean)
    """

    icon = ""
    op_code = 62
    op_title = "NOT"
    content_label = "!"
    content_label_objname = "logic_not"

    _graphics_node_class = LogicGraphicsNode
    _content_widget_class = LogicContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a NOT node.

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

    def eval(self):
        """Evaluate the NOT operation.

        Returns:
            bool: Negation of input, or None if invalid.
        """
        input_node = self.get_input(0)

        if input_node is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect input")
            return None

        try:
            value = input_node.eval()
            self.value = not bool(value)

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip("")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except (ValueError, TypeError) as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {str(e)}")
            return None


@NodeRegistry.register(63)
class XorNode(Node):
    """Node for logical XOR (exclusive OR) operation.

    Returns True if exactly one input is truthy (not both, not neither).

    Op Code: 63
    Category: Logic
    Inputs: 2 (boolean/values)
    Outputs: 1 (boolean)
    """

    icon = ""
    op_code = 63
    op_title = "XOR"
    content_label = "⊕"
    content_label_objname = "logic_xor"

    _graphics_node_class = LogicGraphicsNode
    _content_widget_class = LogicContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create an XOR node.

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

    def eval(self):
        """Evaluate the XOR operation.

        Returns:
            bool: True if exactly one input is truthy, or None if invalid.
        """
        i1 = self.get_input(0)
        i2 = self.get_input(1)

        if i1 is None or i2 is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect all inputs")
            return None

        try:
            val1 = bool(i1.eval())
            val2 = bool(i2.eval())

            # XOR: True if exactly one is True
            self.value = val1 != val2

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip("")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except (ValueError, TypeError) as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {str(e)}")
            return None
