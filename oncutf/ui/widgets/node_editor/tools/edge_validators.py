"""Edge validation callback functions.

This module provides validation functions that can be registered with the
Edge class to enforce connection rules. Validators are called before an
edge is created to determine if the connection is allowed.

Example:
    Register validators to the Edge class::

        from oncutf.ui.widgets.node_editor.tools.edge_validators import (
            edge_cannot_connect_two_outputs_or_two_inputs,
            edge_cannot_connect_input_and_output_of_same_node,
        )

        Edge.register_edge_validator(edge_cannot_connect_two_outputs_or_two_inputs)
        Edge.register_edge_validator(edge_cannot_connect_input_and_output_of_same_node)

Available validators:
    - edge_cannot_connect_two_outputs_or_two_inputs: Prevents output-output or input-input
    - edge_cannot_connect_input_and_output_of_same_node: Prevents self-connections
    - edge_cannot_connect_input_and_output_of_different_type: Enforces type matching

Author:
    Michael Economou

Date:
    2025-12-11
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oncutf.ui.widgets.node_editor.core.socket import Socket


def edge_cannot_connect_two_outputs_or_two_inputs(
    input_socket: Socket, output_socket: Socket
) -> bool:
    """Prevent connecting two outputs or two inputs together.

    Edges must connect an output socket to an input socket, not
    two sockets of the same direction.

    Args:
        input_socket: First socket in the connection.
        output_socket: Second socket in the connection.

    Returns:
        True if valid (output-to-input), False if invalid.
    """
    return not (
        (input_socket.is_output and output_socket.is_output)
        or (input_socket.is_input and output_socket.is_input)
    )


def edge_cannot_connect_input_and_output_of_same_node(
    input_socket: Socket, output_socket: Socket
) -> bool:
    """Prevent connecting a node to itself.

    A node cannot have an edge from one of its outputs to one of
    its own inputs.

    Args:
        input_socket: First socket in the connection.
        output_socket: Second socket in the connection.

    Returns:
        True if valid (different nodes), False if same node.
    """
    return input_socket.node != output_socket.node


def edge_cannot_connect_input_and_output_of_different_type(
    input_socket: Socket, output_socket: Socket
) -> bool:
    """Enforce socket type matching for connections.

    Only sockets of the same type (indicated by color) can be
    connected together.

    Args:
        input_socket: First socket in the connection.
        output_socket: Second socket in the connection.

    Returns:
        True if types match, False if different types.
    """
    return input_socket.socket_type == output_socket.socket_type
