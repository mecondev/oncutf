"""Package: rename_graph

Author: Michael Economou
Date: 2026-01-03

Domain layer for node-based rename pipeline graph.

This package provides Qt-free graph model for visual rename pipeline building.
It separates domain logic from UI concerns, following the node_editor architecture.

Components:
    RenameGraph: Graph model extending node_editor Scene for rename-specific logic
    RenameGraphValidator: Connection rules for rename nodes
    RenameGraphExecutor: Execute graph to generate filenames

Usage:
    from oncutf.core.rename_graph import RenameGraph, RenameGraphExecutor

    graph = RenameGraph()
    # ... build graph with nodes ...
    executor = RenameGraphExecutor(graph)
    filenames = executor.execute(file_items)
"""

from oncutf.core.rename_graph.graph_executor import RenameGraphExecutor
from oncutf.core.rename_graph.graph_model import RenameGraph
from oncutf.core.rename_graph.graph_validator import RenameGraphValidator

__all__ = [
    "RenameGraph",
    "RenameGraphValidator",
    "RenameGraphExecutor",
]
