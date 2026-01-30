"""List manipulation nodes for the node editor.

This module provides nodes for working with lists:
- CreateList: Create a list from multiple inputs
- GetItem: Access list element by index
- ListLength: Get the length of a list
- Append: Add element to list
- Join: Join list elements into a string

All list operations follow Python's standard list semantics.
"""

import logging
from typing import Any

from oncutf.ui.widgets.node_editor.core.node import Node
from oncutf.ui.widgets.node_editor.core.socket import LEFT_CENTER, RIGHT_CENTER
from oncutf.ui.widgets.node_editor.nodes.registry import NodeRegistry

logger = logging.getLogger(__name__)


@NodeRegistry.register(90)
class CreateListNode(Node):
    """Create a list from multiple input values.

    Inputs:
        - Value 1, Value 2, Value 3 (any type)

    Outputs:
        - List containing all input values

    Behavior:
        - Collects all connected inputs into a list
        - Maintains input order
        - Skips unconnected inputs
    """

    op_code = 90
    op_title = "Create List"
    content_label = "[ ]"
    content_label_objname = "node_create_list"

    def __init__(self, scene):
        """Initialize CreateListNode with multiple inputs and one output."""
        super().__init__(scene, self.__class__.op_title, inputs=[5, 5, 5], outputs=[5])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def eval(self) -> Any:
        """Create a list from all connected input values.

        Returns:
            list: List of all input values, or empty list if no inputs.

        """
        if not self.is_dirty() and not self.is_invalid():
            return self.value

        try:
            # Collect all connected input values
            result_list = []
            for i in range(len(self.inputs)):
                input_socket = self.get_input(i)
                if input_socket and input_socket.hasEdges():
                    value = input_socket.getValue()
                    result_list.append(value)

            self.value = result_list

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip(f"List: {self.value}")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except Exception as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {e}")
            logger.error("CreateListNode eval error: %s", e)
            return None


@NodeRegistry.register(91)
class GetItemNode(Node):
    """Get an item from a list by index.

    Inputs:
        - List (list or string)
        - Index (integer)

    Outputs:
        - Item at the specified index

    Behavior:
        - Supports negative indices (Python-style)
        - Returns None for out-of-range indices
        - Works with strings (returns character)
    """

    op_code = 91
    op_title = "Get Item"
    content_label = "[i]"
    content_label_objname = "node_get_item"

    def __init__(self, scene):
        """Initialize GetItemNode with list and index inputs."""
        super().__init__(scene, self.__class__.op_title, inputs=[5, 1], outputs=[5])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def eval(self) -> Any:
        """Get item from list at specified index.

        Returns:
            any: Item at index, or None if error.

        """
        if not self.is_dirty() and not self.is_invalid():
            return self.value

        try:
            # Get list input
            list_socket = self.get_input(0)
            if not list_socket or not list_socket.hasEdges():
                self.mark_invalid()
                self.graphics_node.setToolTip("Missing list input")
                self.value = None
                return None

            input_list = list_socket.getValue()

            # Get index input
            index_socket = self.get_input(1)
            if not index_socket or not index_socket.hasEdges():
                self.mark_invalid()
                self.graphics_node.setToolTip("Missing index input")
                self.value = None
                return None

            index = index_socket.getValue()

            # Validate inputs
            if input_list is None:
                self.mark_invalid()
                self.graphics_node.setToolTip("List is None")
                self.value = None
                return None

            if not isinstance(input_list, list | tuple | str):
                self.mark_invalid()
                self.graphics_node.setToolTip(f"Input is not a list: {type(input_list).__name__}")
                self.value = None
                return None

            if not isinstance(index, int | float):
                self.mark_invalid()
                self.graphics_node.setToolTip("Index must be a number")
                self.value = None
                return None

            # Convert float to int
            index = int(index)

            # Get item at index
            try:
                self.value = input_list[index]
            except IndexError:
                self.mark_invalid()
                self.graphics_node.setToolTip(
                    f"Index {index} out of range (length: {len(input_list)})"
                )
                self.value = None
                return None

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip(f"Item: {self.value!r}")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except Exception as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {e}")
            logger.error("GetItemNode eval error: %s", e)
            return None


@NodeRegistry.register(92)
class ListLengthNode(Node):
    """Get the length of a list or string.

    Inputs:
        - List/String (list, tuple, or string)

    Outputs:
        - Length (integer)

    Behavior:
        - Returns the number of items in a list
        - Works with strings (returns character count)
        - Returns 0 for None
    """

    op_code = 92
    op_title = "List Length"
    content_label = "len()"
    content_label_objname = "node_list_length"

    def __init__(self, scene):
        """Initialize ListLengthNode with one input and one output."""
        super().__init__(scene, self.__class__.op_title, inputs=[5], outputs=[1])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def eval(self) -> Any:
        """Get length of input list or string.

        Returns:
            int: Length of the input, or None if error.

        """
        if not self.is_dirty() and not self.is_invalid():
            return self.value

        try:
            # Get input
            input_socket = self.get_input(0)
            if not input_socket or not input_socket.hasEdges():
                self.mark_invalid()
                self.graphics_node.setToolTip("Missing input connection")
                self.value = None
                return None

            input_value = input_socket.getValue()

            # Handle None
            if input_value is None:
                self.value = 0
            # Check if it has a length
            elif hasattr(input_value, "__len__"):
                self.value = len(input_value)
            else:
                self.mark_invalid()
                self.graphics_node.setToolTip(f"Cannot get length of {type(input_value).__name__}")
                self.value = None
                return None

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip(f"Length: {self.value}")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except Exception as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {e}")
            logger.error("ListLengthNode eval error: %s", e)
            return None


@NodeRegistry.register(93)
class AppendNode(Node):
    """Append an item to a list (creates a new list).

    Inputs:
        - List (list)
        - Item (any type)

    Outputs:
        - New list with item appended

    Behavior:
        - Creates a new list (does not modify input)
        - If list input is None, creates new list with item
        - Converts non-list inputs to lists
    """

    op_code = 93
    op_title = "Append"
    content_label = "+ item"
    content_label_objname = "node_append"

    def __init__(self, scene):
        """Initialize AppendNode with list and item inputs."""
        super().__init__(scene, self.__class__.op_title, inputs=[5, 5], outputs=[5])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def eval(self) -> Any:
        """Append item to list.

        Returns:
            list: New list with item appended, or None if error.

        """
        if not self.is_dirty() and not self.is_invalid():
            return self.value

        try:
            # Get list input
            list_socket = self.get_input(0)
            if not list_socket or not list_socket.hasEdges():
                self.mark_invalid()
                self.graphics_node.setToolTip("Missing list input")
                self.value = None
                return None

            input_list = list_socket.getValue()

            # Get item input
            item_socket = self.get_input(1)
            if not item_socket or not item_socket.hasEdges():
                self.mark_invalid()
                self.graphics_node.setToolTip("Missing item input")
                self.value = None
                return None

            item = item_socket.getValue()

            # Handle None list
            if input_list is None:
                self.value = [item]
            # If it's a list, append to copy
            elif isinstance(input_list, list):
                self.value = input_list.copy()
                self.value.append(item)
            # Convert tuple to list
            elif isinstance(input_list, tuple):
                self.value = list(input_list)
                self.value.append(item)
            # Wrap non-list in list
            else:
                self.value = [input_list, item]

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip(f"Result: {self.value}")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except Exception as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {e}")
            logger.error("AppendNode eval error: %s", e)
            return None


@NodeRegistry.register(94)
class JoinNode(Node):
    """Join list elements into a string.

    Inputs:
        - List (list of values)
        - Separator (string, optional - default: empty string)

    Outputs:
        - Joined string

    Behavior:
        - Converts all elements to strings
        - Uses separator between elements
        - Empty list produces empty string
    """

    op_code = 94
    op_title = "Join"
    content_label = "join()"
    content_label_objname = "node_join"

    def __init__(self, scene):
        """Initialize JoinNode with list and separator inputs."""
        super().__init__(scene, self.__class__.op_title, inputs=[5, 3], outputs=[3])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def eval(self) -> Any:
        """Join list elements into a string.

        Returns:
            str: Joined string, or None if error.

        """
        if not self.is_dirty() and not self.is_invalid():
            return self.value

        try:
            # Get list input
            list_socket = self.get_input(0)
            if not list_socket or not list_socket.hasEdges():
                self.mark_invalid()
                self.graphics_node.setToolTip("Missing list input")
                self.value = None
                return None

            input_list = list_socket.getValue()

            # Get separator input (optional)
            separator = ""
            sep_socket = self.get_input(1)
            if sep_socket and sep_socket.hasEdges():
                sep_value = sep_socket.getValue()
                if sep_value is not None:
                    separator = str(sep_value)
            # Validate input
            if input_list is None:
                self.value = ""
            elif isinstance(input_list, list | tuple):
                # Convert all elements to strings and join
                self.value = separator.join(str(item) for item in input_list)
            elif isinstance(input_list, str):
                # Already a string
                self.value = input_list
            else:
                # Convert single value to string
                self.value = str(input_list)

            self.mark_dirty(False)
            self.mark_invalid(False)
            self.graphics_node.setToolTip(f"Result: {self.value!r}")

            self.mark_descendants_dirty()
            self.eval_children()

            return self.value

        except Exception as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Error: {e}")
            logger.error("JoinNode eval error: %s", e)
            return None
