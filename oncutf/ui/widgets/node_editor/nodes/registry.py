"""Central registry for node type management.

This module provides NodeRegistry, which manages registration and
lookup of node types by their unique operation codes (op_codes).

Usage:
    Register nodes with decorator or manual call::

        from oncutf.ui.widgets.node_editor.core import Node
        from oncutf.ui.widgets.node_editor.nodes import NodeRegistry

        # Using decorator
        @NodeRegistry.register(100)
        class MyNode(Node):
            op_code = 100
            op_title = "My Node"

        # Manual registration
        NodeRegistry.register_node(101, AnotherNode)

        # Get node class by op_code
        node_class = NodeRegistry.get_node_class(100)

Author:
    Michael Economou

Date:
    2025-12-11
"""

import logging
from collections.abc import Callable
from typing import ClassVar

logger = logging.getLogger(__name__)


class NodeRegistry:
    """Central registry for all node types.

    Maintains a dictionary mapping operation codes to node classes.
    Built-in nodes use op_codes 1-113. Custom nodes should use 200+.

    Attributes:
        _nodes: Dictionary mapping op_codes to node classes.

    """

    _nodes: ClassVar[dict[int, type]] = {}

    @classmethod
    def register(cls, op_code: int) -> Callable:
        """Decorator to register a node class with an op_code.

        Args:
            op_code: Unique identifier for the node type.

        Returns:
            Decorator function that registers the class.

        Raises:
            ValueError: If op_code is already registered.

        Example:
            Register a custom node::

                @NodeRegistry.register(100)
                class MyNode(Node):
                    op_code = 100
                    op_title = "My Node"

        """

        def decorator(node_class: type) -> type:
            """Register the node class and set its op_code attribute.

            Args:
                node_class: Node class to register.

            Returns:
                The registered node class unchanged.

            Raises:
                ValueError: If op_code already registered.

            """
            if op_code in cls._nodes:
                existing = cls._nodes[op_code].__name__
                logger.error(
                    "Duplicate op_code %s: already registered to %s, cannot register %s",
                    op_code,
                    existing,
                    node_class.__name__,
                )
                raise ValueError(f"OpCode {op_code} already registered to {existing}")
            cls._nodes[op_code] = node_class
            node_class.op_code = op_code
            logger.debug("Registered node: %s with op_code %s", node_class.__name__, op_code)
            return node_class

        return decorator

    @classmethod
    def register_node(cls, op_code: int, node_class: type) -> None:
        """Register a node class without using decorator.

        Args:
            op_code: Unique identifier for the node type.
            node_class: Node class to register.

        Raises:
            ValueError: If op_code is already registered.

        """
        if op_code in cls._nodes:
            existing = cls._nodes[op_code].__name__
            logger.error(
                "Duplicate op_code %s: already registered to %s, cannot register %s",
                op_code,
                existing,
                node_class.__name__,
            )
            raise ValueError(f"OpCode {op_code} already registered to {existing}")
        cls._nodes[op_code] = node_class
        node_class.op_code = op_code
        logger.debug("Registered node: %s with op_code %s", node_class.__name__, op_code)

    @classmethod
    def get_node_class(cls, op_code: int) -> type | None:
        """Look up a node class by its op_code.

        Args:
            op_code: Operation code to look up.

        Returns:
            Node class, or None if not registered.

        """
        return cls._nodes.get(op_code)

    @classmethod
    def get_all_nodes(cls) -> dict[int, type]:
        """Get all registered node types.

        Returns:
            Copy of dictionary mapping op_codes to node classes.

        """
        return cls._nodes.copy()

    @classmethod
    def get_nodes_by_category(cls, category: str) -> dict[int, type]:
        """Get all nodes belonging to a category.

        Args:
            category: Category name to filter by.

        Returns:
            Dictionary of matching nodes (op_code -> class).

        """
        return {
            op_code: node_class
            for op_code, node_class in cls._nodes.items()
            if getattr(node_class, "category", None) == category
        }

    @classmethod
    def clear(cls) -> None:
        """Clear all registered nodes.

        Primarily useful for testing to reset registry state.
        """
        cls._nodes.clear()

    @classmethod
    def unregister(cls, op_code: int) -> bool:
        """Unregister a node by op_code.

        Args:
            op_code: The op_code to unregister

        Returns:
            True if node was unregistered, False if not found

        """
        if op_code in cls._nodes:
            del cls._nodes[op_code]
            return True
        return False
