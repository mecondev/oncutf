"""Tools module for interactive edge manipulation.

This module provides helper classes and validation functions for
interactive edge operations in the node editor:

Classes:
    EdgeDragging: Create new edges by clicking and dragging from sockets.
    EdgeRerouting: Reconnect existing edges to different sockets.
    EdgeIntersect: Insert nodes into edges by dropping them.
    EdgeSnapping: Snap edge endpoints to nearby sockets.

Validator Functions:
    edge_cannot_connect_two_outputs_or_two_inputs: Prevent same-type connections.
    edge_cannot_connect_input_and_output_of_same_node: Prevent self-loops.
    edge_cannot_connect_input_and_output_of_different_type: Enforce type matching.

Register validators with Edge.register_edge_validator() to enable validation.

Author:
    Michael Economou

Date:
    2025-12-11
"""

from oncutf.ui.widgets.node_editor.tools.edge_dragging import EdgeDragging
from oncutf.ui.widgets.node_editor.tools.edge_intersect import EdgeIntersect
from oncutf.ui.widgets.node_editor.tools.edge_rerouting import EdgeRerouting
from oncutf.ui.widgets.node_editor.tools.edge_snapping import EdgeSnapping
from oncutf.ui.widgets.node_editor.tools.edge_validators import (
    edge_cannot_connect_input_and_output_of_different_type,
    edge_cannot_connect_input_and_output_of_same_node,
    edge_cannot_connect_two_outputs_or_two_inputs,
)

__all__ = [
    'EdgeDragging',
    'EdgeRerouting',
    'EdgeIntersect',
    'EdgeSnapping',
    'edge_cannot_connect_two_outputs_or_two_inputs',
    'edge_cannot_connect_input_and_output_of_same_node',
    'edge_cannot_connect_input_and_output_of_different_type',
]
