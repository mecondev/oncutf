"""Type conversion nodes for the node editor.

This module provides nodes for converting between different data types:
- ToString: Convert any value to string
- ToNumber: Convert value to float
- ToBool: Convert value to boolean
- ToInt: Convert value to integer

All conversion nodes follow Python's standard conversion rules.
"""

import logging
from typing import Any

from oncutf.ui.widgets.node_editor.core.node import Node
from oncutf.ui.widgets.node_editor.core.socket import LEFT_CENTER, RIGHT_CENTER
from oncutf.ui.widgets.node_editor.nodes.registry import NodeRegistry

logger = logging.getLogger(__name__)


@NodeRegistry.register(70)
class ToStringNode(Node):
    """Convert any value to string representation.

    Inputs:
        - Value (any type)

    Outputs:
        - String representation

    Conversion Rules:
        - Numbers: "123", "45.67"
        - Booleans: "True", "False"
        - None: "None"
        - Lists/dicts: str() representation
    """

    op_code = 70
    op_title = "To String"
    content_label = "→str"
    content_label_objname = "node_to_string"

    def __init__(self, scene):
        """Initialize ToStringNode with one input and one output."""
        super().__init__(scene, self.__class__.op_title, inputs=[5], outputs=[5])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def eval(self) -> Any:
        """Convert input value to string.

        Returns:
            str: String representation of input value, or None if no input.

        """
        if not self.is_dirty() and not self.is_invalid():
            return self.value

        try:
            # Get input value
            input_socket = self.get_input(0)
            if not input_socket or not input_socket.hasEdges():
                self.mark_invalid()
                self.graphics_node.setToolTip("Missing input connection")
                self.value = None
                return None

            input_value = input_socket.getValue()

            # Convert to string
            if input_value is None:
                self.value = "None"
            else:
                self.value = str(input_value)

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip(f"Output: {self.value!r}")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except Exception as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {e}")
            logger.error("ToStringNode eval error: %s", e)
            return None


@NodeRegistry.register(71)
class ToNumberNode(Node):
    """Convert value to floating point number.

    Inputs:
        - Value (string, int, bool, or number)

    Outputs:
        - Float number

    Conversion Rules:
        - Strings: Parse as float ("123.45" → 123.45)
        - Integers: Direct conversion (42 → 42.0)
        - Booleans: True → 1.0, False → 0.0
        - Invalid strings: Error (marked invalid)
    """

    op_code = 71
    op_title = "To Number"
    content_label = "→float"
    content_label_objname = "node_to_number"

    def __init__(self, scene):
        """Initialize ToNumberNode with one input and one output."""
        super().__init__(scene, self.__class__.op_title, inputs=[5], outputs=[1])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def eval(self) -> Any:
        """Convert input value to float.

        Returns:
            float: Converted number, or None if conversion fails.

        """
        if not self.is_dirty() and not self.is_invalid():
            return self.value

        try:
            # Get input value
            input_socket = self.get_input(0)
            if not input_socket or not input_socket.hasEdges():
                self.mark_invalid()
                self.graphics_node.setToolTip("Missing input connection")
                self.value = None
                return None

            input_value = input_socket.getValue()

            # Convert to float
            if input_value is None:
                self.mark_invalid()
                self.graphics_node.setToolTip("Cannot convert None to number")
                self.value = None
                return None

            if isinstance(input_value, bool):
                # Handle bool before checking numeric (bool is subclass of int)
                self.value = 1.0 if input_value else 0.0
            elif isinstance(input_value, int | float):
                self.value = float(input_value)
            elif isinstance(input_value, str):
                # Try to parse string
                self.value = float(input_value)
            else:
                self.mark_invalid()
                self.graphics_node.setToolTip(
                    f"Cannot convert {type(input_value).__name__} to number"
                )
                self.value = None
                return None

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip(f"Output: {self.value}")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except ValueError as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Invalid number format: {e}")
            logger.error("ToNumberNode conversion error: %s", e)
            return None
        except Exception as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {e}")
            logger.error("ToNumberNode eval error: %s", e)
            return None


@NodeRegistry.register(72)
class ToBoolNode(Node):
    """Convert value to boolean.

    Inputs:
        - Value (any type)

    Outputs:
        - Boolean

    Conversion Rules:
        - Numbers: 0 → False, non-zero → True
        - Strings: empty → False, non-empty → True
        - Special: "false"/"0" → False (case-insensitive)
        - None: False
        - Collections: empty → False, non-empty → True
    """

    op_code = 72
    op_title = "To Bool"
    content_label = "→bool"
    content_label_objname = "node_to_bool"

    def __init__(self, scene):
        """Initialize ToBoolNode with one input and one output."""
        super().__init__(scene, self.__class__.op_title, inputs=[5], outputs=[4])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def eval(self) -> Any:
        """Convert input value to boolean.

        Returns:
            bool: Converted boolean, or None if no input.

        """
        if not self.is_dirty() and not self.is_invalid():
            return self.value

        try:
            # Get input value
            input_socket = self.get_input(0)
            if not input_socket or not input_socket.hasEdges():
                self.mark_invalid()
                self.graphics_node.setToolTip("Missing input connection")
                self.value = None
                return None

            input_value = input_socket.getValue()

            # Convert to bool
            if input_value is None:
                self.value = False
            elif isinstance(input_value, str):
                # Special handling for string boolean representations
                lower_val = input_value.lower()
                if lower_val in ("false", "0", "no", ""):
                    self.value = False
                else:
                    self.value = True
            else:
                # Use Python's truthiness
                self.value = bool(input_value)

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip(f"Output: {self.value}")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except Exception as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {e}")
            logger.error("ToBoolNode eval error: %s", e)
            return None


@NodeRegistry.register(73)
class ToIntNode(Node):
    """Convert value to integer.

    Inputs:
        - Value (string, float, bool, or int)

    Outputs:
        - Integer

    Conversion Rules:
        - Floats: Truncate decimal part (3.9 → 3)
        - Strings: Parse as integer ("42" → 42)
        - Booleans: True → 1, False → 0
        - Invalid strings: Error (marked invalid)
    """

    op_code = 73
    op_title = "To Int"
    content_label = "→int"
    content_label_objname = "node_to_int"

    def __init__(self, scene):
        """Initialize ToIntNode with one input and one output."""
        super().__init__(scene, self.__class__.op_title, inputs=[5], outputs=[1])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def eval(self) -> Any:
        """Convert input value to integer.

        Returns:
            int: Converted integer, or None if conversion fails.

        """
        if not self.is_dirty() and not self.is_invalid():
            return self.value

        try:
            # Get input value
            input_socket = self.get_input(0)
            if not input_socket or not input_socket.hasEdges():
                self.mark_invalid()
                self.graphics_node.setToolTip("Missing input connection")
                self.value = None
                return None

            input_value = input_socket.getValue()

            # Convert to int
            if input_value is None:
                self.mark_invalid()
                self.graphics_node.setToolTip("Cannot convert None to integer")
                self.value = None
                return None

            if isinstance(input_value, bool):
                # Handle bool before checking numeric (bool is subclass of int)
                self.value = 1 if input_value else 0
            elif isinstance(input_value, int):
                self.value = input_value
            elif isinstance(input_value, float):
                # Truncate (not round)
                self.value = int(input_value)
            elif isinstance(input_value, str):
                # Try to parse string
                self.value = int(input_value)
            else:
                self.mark_invalid()
                self.graphics_node.setToolTip(
                    f"Cannot convert {type(input_value).__name__} to integer"
                )
                self.value = None
                return None

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip(f"Output: {self.value}")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except ValueError as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Invalid integer format: {e}")
            logger.error("ToIntNode conversion error: %s", e)
            return None
        except Exception as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {e}")
            logger.error("ToIntNode eval error: %s", e)
            return None
