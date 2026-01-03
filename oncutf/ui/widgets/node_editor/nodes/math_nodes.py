"""Mathematical operation nodes.

Provides arithmetic and advanced math operations.

Basic operations: Add, Subtract, Multiply, Divide
Extended operations: Power, Sqrt, Abs, Min, Max, Round, Modulo

Author:
    Michael Economou

Date:
    2025-12-12
"""

import math

from PyQt5.QtWidgets import QLabel

from oncutf.ui.widgets.node_editor.core.node import Node
from oncutf.ui.widgets.node_editor.core.socket import LEFT_CENTER, RIGHT_CENTER
from oncutf.ui.widgets.node_editor.graphics.node import QDMGraphicsNode
from oncutf.ui.widgets.node_editor.nodes.registry import NodeRegistry
from oncutf.ui.widgets.node_editor.widgets.content_widget import QDMNodeContentWidget


class MathGraphicsNode(QDMGraphicsNode):
    """Graphics node for math operation nodes."""

    def init_sizes(self):
        """Initialize size parameters for math nodes."""
        super().init_sizes()
        self.width = 160
        self.height = 74
        self.edge_roundness = 6
        self.edge_padding = 0
        self.title_horizontal_padding = 8
        self.title_vertical_padding = 10


class MathContent(QDMNodeContentWidget):
    """Content widget with operation label."""

    def init_ui(self):
        """Initialize the content label."""
        lbl = QLabel(self.node.content_label, self)
        lbl.setObjectName(self.node.content_label_objname)


class MathNode(Node):
    """Base class for binary math operation nodes.

    Subclass this and override eval_operation() to implement
    specific mathematical operations.
    """

    icon = ""
    op_code = 0
    op_title = "Math Operation"
    content_label = ""
    content_label_objname = "math_node"

    _graphics_node_class = MathGraphicsNode
    _content_widget_class = MathContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a math operation node.

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

    def eval_operation(self, input1, input2):
        """Perform the mathematical operation.

        Override this method in subclasses to implement specific operations.

        Args:
            input1: First operand (numeric).
            input2: Second operand (numeric).

        Returns:
            Result of the operation.
        """
        _ = input1, input2  # Unused in base class
        return 0

    def eval(self) -> float | None:
        """Evaluate the math operation node.

        Gets values from both inputs, performs the operation,
        and propagates the result.

        Returns:
            Computed result, or None if inputs are invalid.
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

            # Convert to numbers if possible
            if not isinstance(val1, int | float):
                val1 = float(val1)
            if not isinstance(val2, int | float):
                val2 = float(val2)

            self.value = self.eval_operation(val1, val2)
            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip("")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except (ValueError, TypeError, ZeroDivisionError) as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {str(e)}")
            return None


@NodeRegistry.register(10)
class AddNode(MathNode):
    """Node for adding two numbers.

    Op Code: 10
    Category: Math
    Inputs: 2 (numeric values)
    Outputs: 1 (sum)
    """

    op_code = 10
    op_title = "Add"
    content_label = "+"
    content_label_objname = "math_node_add"

    def eval_operation(self, input1, input2):
        """Add two numbers.

        Args:
            input1: First number.
            input2: Second number.

        Returns:
            Sum of input1 and input2.
        """
        return input1 + input2


@NodeRegistry.register(11)
class SubtractNode(MathNode):
    """Node for subtracting two numbers.

    Op Code: 11
    Category: Math
    Inputs: 2 (numeric values)
    Outputs: 1 (difference)
    """

    op_code = 11
    op_title = "Subtract"
    content_label = "-"
    content_label_objname = "math_node_sub"

    def eval_operation(self, input1, input2):
        """Subtract two numbers.

        Args:
            input1: First number (minuend).
            input2: Second number (subtrahend).

        Returns:
            Difference of input1 - input2.
        """
        return input1 - input2


@NodeRegistry.register(12)
class MultiplyNode(MathNode):
    """Node for multiplying two numbers.

    Op Code: 12
    Category: Math
    Inputs: 2 (numeric values)
    Outputs: 1 (product)
    """

    op_code = 12
    op_title = "Multiply"
    content_label = "×"
    content_label_objname = "math_node_mul"

    def eval_operation(self, input1, input2):
        """Multiply two numbers.

        Args:
            input1: First number.
            input2: Second number.

        Returns:
            Product of input1 * input2.
        """
        return input1 * input2


@NodeRegistry.register(13)
class DivideNode(MathNode):
    """Node for dividing two numbers.

    Op Code: 13
    Category: Math
    Inputs: 2 (numeric values)
    Outputs: 1 (quotient)
    """

    op_code = 13
    op_title = "Divide"
    content_label = "÷"
    content_label_objname = "math_node_div"

    def eval_operation(self, input1, input2):
        """Divide two numbers.

        Args:
            input1: Numerator.
            input2: Denominator.

        Returns:
            Quotient of input1 / input2.

        Raises:
            ZeroDivisionError: If input2 is zero.
        """
        if input2 == 0:
            raise ZeroDivisionError("Division by zero")
        return input1 / input2


# =============================================================================
# Extended Math Operations
# =============================================================================


@NodeRegistry.register(50)
class PowerNode(Node):
    """Node for exponentiation.

    Raises base to the power of exponent (base ** exponent).

    Op Code: 50
    Category: Math
    Inputs: 2 (base, exponent)
    Outputs: 1 (result)
    """

    icon = ""
    op_code = 50
    op_title = "Power"
    content_label = "^"
    content_label_objname = "math_power"

    _graphics_node_class = MathGraphicsNode
    _content_widget_class = MathContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a power node.

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
        """Evaluate the power operation.

        Returns:
            float: Base raised to exponent, or None if inputs are invalid.
        """
        base_node = self.get_input(0)
        exp_node = self.get_input(1)

        if base_node is None or exp_node is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect all inputs")
            return None

        try:
            base = float(base_node.eval())
            exponent = float(exp_node.eval())

            self.value = base**exponent

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip("")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except (ValueError, TypeError, OverflowError) as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {str(e)}")
            return None


@NodeRegistry.register(51)
class SqrtNode(Node):
    """Node for square root.

    Calculates the square root of a number.

    Op Code: 51
    Category: Math
    Inputs: 1 (number)
    Outputs: 1 (square root)
    """

    icon = ""
    op_code = 51
    op_title = "Square Root"
    content_label = "√"
    content_label_objname = "math_sqrt"

    _graphics_node_class = MathGraphicsNode
    _content_widget_class = MathContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a square root node.

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
        """Evaluate the square root operation.

        Returns:
            float: Square root of input, or None if invalid.
        """
        input_node = self.get_input(0)

        if input_node is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect input")
            return None

        try:
            value = float(input_node.eval())

            if value < 0:
                self.mark_invalid()
                self.graphics_node.setToolTip("Cannot take square root of negative number")
                return None

            self.value = math.sqrt(value)

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


@NodeRegistry.register(52)
class AbsNode(Node):
    """Node for absolute value.

    Returns the absolute value of a number.

    Op Code: 52
    Category: Math
    Inputs: 1 (number)
    Outputs: 1 (absolute value)
    """

    icon = ""
    op_code = 52
    op_title = "Absolute"
    content_label = "|x|"
    content_label_objname = "math_abs"

    _graphics_node_class = MathGraphicsNode
    _content_widget_class = MathContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create an absolute value node.

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
        """Evaluate the absolute value operation.

        Returns:
            float: Absolute value of input, or None if invalid.
        """
        input_node = self.get_input(0)

        if input_node is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect input")
            return None

        try:
            value = float(input_node.eval())
            self.value = abs(value)

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


@NodeRegistry.register(53)
class MinNode(Node):
    """Node for minimum of two values.

    Returns the smaller of two numbers.

    Op Code: 53
    Category: Math
    Inputs: 2 (numbers)
    Outputs: 1 (minimum)
    """

    icon = ""
    op_code = 53
    op_title = "Minimum"
    content_label = "min"
    content_label_objname = "math_min"

    _graphics_node_class = MathGraphicsNode
    _content_widget_class = MathContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a minimum node.

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
        """Evaluate the minimum operation.

        Returns:
            float: Minimum of two inputs, or None if invalid.
        """
        i1 = self.get_input(0)
        i2 = self.get_input(1)

        if i1 is None or i2 is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect all inputs")
            return None

        try:
            val1 = float(i1.eval())
            val2 = float(i2.eval())

            self.value = min(val1, val2)

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


@NodeRegistry.register(54)
class MaxNode(Node):
    """Node for maximum of two values.

    Returns the larger of two numbers.

    Op Code: 54
    Category: Math
    Inputs: 2 (numbers)
    Outputs: 1 (maximum)
    """

    icon = ""
    op_code = 54
    op_title = "Maximum"
    content_label = "max"
    content_label_objname = "math_max"

    _graphics_node_class = MathGraphicsNode
    _content_widget_class = MathContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a maximum node.

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
        """Evaluate the maximum operation.

        Returns:
            float: Maximum of two inputs, or None if invalid.
        """
        i1 = self.get_input(0)
        i2 = self.get_input(1)

        if i1 is None or i2 is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect all inputs")
            return None

        try:
            val1 = float(i1.eval())
            val2 = float(i2.eval())

            self.value = max(val1, val2)

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


@NodeRegistry.register(55)
class RoundNode(Node):
    """Node for rounding numbers.

    Rounds a number to specified decimal places.

    Op Code: 55
    Category: Math
    Inputs: 2 (number, decimal places)
    Outputs: 1 (rounded number)
    """

    icon = ""
    op_code = 55
    op_title = "Round"
    content_label = "~"
    content_label_objname = "math_round"

    _graphics_node_class = MathGraphicsNode
    _content_widget_class = MathContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a round node.

        Args:
            scene: Parent scene containing this node.
            inputs: Input socket configuration (default: [1, 1]).
            outputs: Output socket configuration (default: [1]).
        """
        if inputs is None:
            inputs = [1, 1]  # number, decimal places
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
        """Evaluate the round operation.

        Returns:
            float: Rounded number, or None if invalid.
        """
        number_node = self.get_input(0)
        places_node = self.get_input(1)

        if number_node is None or places_node is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect all inputs")
            return None

        try:
            number = float(number_node.eval())
            places = int(places_node.eval())

            self.value = round(number, places)

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


@NodeRegistry.register(56)
class ModuloNode(Node):
    """Node for modulo operation.

    Returns the remainder of division (a % b).

    Op Code: 56
    Category: Math
    Inputs: 2 (dividend, divisor)
    Outputs: 1 (remainder)
    """

    icon = ""
    op_code = 56
    op_title = "Modulo"
    content_label = "%"
    content_label_objname = "math_modulo"

    _graphics_node_class = MathGraphicsNode
    _content_widget_class = MathContent

    def __init__(self, scene, inputs=None, outputs=None):
        """Create a modulo node.

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
        """Evaluate the modulo operation.

        Returns:
            float: Remainder of division, or None if invalid.
        """
        i1 = self.get_input(0)
        i2 = self.get_input(1)

        if i1 is None or i2 is None:
            self.mark_invalid()
            self.mark_descendants_dirty()
            self.graphics_node.setToolTip("Connect all inputs")
            return None

        try:
            val1 = float(i1.eval())
            val2 = float(i2.eval())

            if val2 == 0:
                raise ZeroDivisionError("Modulo by zero")

            self.value = val1 % val2

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip("")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except (ValueError, TypeError, ZeroDivisionError) as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {str(e)}")
            return None
