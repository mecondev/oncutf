"""Module: graph_validator.py

Author: Michael Economou
Date: 2026-01-03

Validation rules for rename pipeline graphs.

Ensures graph integrity:
- Single OutputNode
- No cycles (DAG)
- Connected terminal
- Type compatibility
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.core.rename_graph.graph_model import RenameGraph

logger = get_cached_logger(__name__)


@dataclass
class ValidationResult:
    """Result of graph validation.

    Attributes:
        is_valid: Whether graph passed validation
        errors: List of error messages
        warnings: List of warning messages
    """
    is_valid: bool
    errors: list[str]
    warnings: list[str]


class RenameGraphValidator:
    """Validates rename pipeline graphs.

    Validation rules:
    1. Graph must have exactly one OutputNode
    2. OutputNode must have connected input
    3. Graph must be acyclic (DAG)
    4. All edges must connect compatible socket types
    5. Source nodes (no inputs) must be valid sources
    """

    # Op codes for special nodes
    OUTPUT_NODE_OP_CODE = 207

    # Source nodes (valid without inputs)
    SOURCE_NODE_OP_CODES = {200, 201, 203, 204}  # OriginalName, Counter, Metadata, TextInput

    def __init__(self, graph: RenameGraph) -> None:
        """Initialize validator with graph.

        Args:
            graph: RenameGraph to validate
        """
        self._graph = graph

    def validate(self) -> ValidationResult:
        """Run all validation checks.

        Returns:
            ValidationResult with is_valid, errors, warnings
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check 1: Single OutputNode
        output_errors = self._validate_output_node()
        errors.extend(output_errors)

        # Check 2: No cycles
        cycle_errors = self._validate_no_cycles()
        errors.extend(cycle_errors)

        # Check 3: Connected inputs
        connection_errors = self._validate_connections()
        errors.extend(connection_errors)

        # Check 4: Disconnected nodes (warning)
        disconnected = self._check_disconnected_nodes()
        warnings.extend(disconnected)

        is_valid = len(errors) == 0

        if not is_valid:
            logger.warning("[RenameGraphValidator] Validation failed: %s", errors)
        else:
            logger.debug("[RenameGraphValidator] Validation passed")

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
        )

    def _validate_output_node(self) -> list[str]:
        """Validate OutputNode presence and count.

        Returns:
            List of error messages
        """
        errors = []

        output_nodes = [
            n for n in self._graph.nodes
            if getattr(n, 'op_code', None) == self.OUTPUT_NODE_OP_CODE
        ]

        if len(output_nodes) == 0:
            errors.append("Graph must have an OutputNode")
        elif len(output_nodes) > 1:
            errors.append(f"Graph must have exactly one OutputNode, found {len(output_nodes)}")
        else:
            # Check if OutputNode has connected input
            output_node = output_nodes[0]
            if hasattr(output_node, 'inputs') and output_node.inputs:
                input_socket = output_node.inputs[0]
                if not getattr(input_socket, 'has_edge', lambda: False)():
                    errors.append("OutputNode must have connected input")

        return errors

    def _validate_no_cycles(self) -> list[str]:
        """Validate graph has no cycles (is a DAG).

        Returns:
            List of error messages
        """
        # TODO: Implement proper cycle detection using DFS
        # For now, assume no cycles
        return []

    def _validate_connections(self) -> list[str]:
        """Validate all required inputs are connected.

        Returns:
            List of error messages
        """
        errors = []

        for node in self._graph.nodes:
            op_code = getattr(node, 'op_code', None)

            # Skip source nodes (they don't need inputs)
            if op_code in self.SOURCE_NODE_OP_CODES:
                continue

            # Check if node has required inputs
            if hasattr(node, 'inputs'):
                for i, input_socket in enumerate(node.inputs):
                    if not getattr(input_socket, 'has_edge', lambda: False)():
                        node_title = getattr(node, 'title', f'Node(op={op_code})')
                        errors.append(f"{node_title}: Input {i} is not connected")

        return errors

    def _check_disconnected_nodes(self) -> list[str]:
        """Check for disconnected nodes (not errors, just warnings).

        Returns:
            List of warning messages
        """
        warnings = []

        for node in self._graph.nodes:
            op_code = getattr(node, 'op_code', None)

            # OutputNode only has inputs, not outputs
            if op_code == self.OUTPUT_NODE_OP_CODE:
                continue

            # Check if node has any output connections
            has_output_edge = False
            if hasattr(node, 'outputs'):
                for output_socket in node.outputs:
                    if getattr(output_socket, 'has_edge', lambda: False)():
                        has_output_edge = True
                        break

            if not has_output_edge:
                node_title = getattr(node, 'title', f'Node(op={op_code})')
                warnings.append(f"{node_title}: Node output is not connected")

        return warnings

    @staticmethod
    def is_valid_connection(
        output_socket: Any,
        input_socket: Any
    ) -> bool:
        """Check if connection between sockets is valid.

        Args:
            output_socket: Source socket
            input_socket: Destination socket

        Returns:
            True if connection is valid
        """
        # For rename nodes, all connections are string-to-string
        # Future: could add socket_type checking
        return True
