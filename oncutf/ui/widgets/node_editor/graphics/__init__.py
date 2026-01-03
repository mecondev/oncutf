"""Graphics module for Qt visual representation of node editor components.

This module contains Qt graphics items and views for rendering the
visual node graph interface:

Core Graphics Items:
    QDMGraphicsSocket: Colored circle for socket connection points.
    QDMGraphicsNode: Node rectangle with title, content, and sockets.
    QDMGraphicsEdge: Path connecting sockets with multiple styles.
    QDMGraphicsScene: Scene with grid background and selection signals.
    QDMGraphicsView: View with zoom, pan, and interaction handling.
    QDMCutLine: Dashed line for cutting multiple edges.

Path Calculators:
    GraphicsEdgePathBase: Abstract base for path computation.
    GraphicsEdgePathDirect: Straight line path.
    GraphicsEdgePathBezier: Smooth Bezier curve path.
    GraphicsEdgePathSquare: Right-angle stepped path.
    GraphicsEdgePathImprovedSharp: Sharp corners with horizontal ends.
    GraphicsEdgePathImprovedBezier: Adaptive Bezier with horizontal ends.

Author:
    Michael Economou

Date:
    2025-12-11
"""

from oncutf.ui.widgets.node_editor.graphics.cutline import QDMCutLine
from oncutf.ui.widgets.node_editor.graphics.edge import QDMGraphicsEdge
from oncutf.ui.widgets.node_editor.graphics.edge_path import (
    GraphicsEdgePathBase,
    GraphicsEdgePathBezier,
    GraphicsEdgePathDirect,
    GraphicsEdgePathImprovedBezier,
    GraphicsEdgePathImprovedSharp,
    GraphicsEdgePathSquare,
)
from oncutf.ui.widgets.node_editor.graphics.node import QDMGraphicsNode
from oncutf.ui.widgets.node_editor.graphics.scene import QDMGraphicsScene
from oncutf.ui.widgets.node_editor.graphics.socket import QDMGraphicsSocket
from oncutf.ui.widgets.node_editor.graphics.view import QDMGraphicsView

__all__ = [
    # Core items
    "QDMGraphicsSocket",
    "QDMGraphicsNode",
    "QDMGraphicsEdge",
    "QDMGraphicsScene",
    "QDMGraphicsView",
    "QDMCutLine",
    # Path calculators
    "GraphicsEdgePathBase",
    "GraphicsEdgePathDirect",
    "GraphicsEdgePathBezier",
    "GraphicsEdgePathSquare",
    "GraphicsEdgePathImprovedSharp",
    "GraphicsEdgePathImprovedBezier",
]
