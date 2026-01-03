"""Module: graph_model.py

Author: Michael Economou
Date: 2026-01-03

Rename pipeline graph model.

Extends the node_editor Scene with rename-specific functionality:
- File context for node evaluation
- Pipeline execution order
- Rename-specific serialization
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

logger = get_cached_logger(__name__)


class RenameGraph:
    """Graph model for rename pipeline.

    Manages nodes and edges representing a rename operation flow.
    Provides context (current FileItem) during evaluation.

    Attributes:
        _nodes: List of nodes in the graph
        _edges: List of edges connecting nodes
        _current_file: FileItem being processed during evaluation
        _file_index: Current file index in batch
    """

    def __init__(self) -> None:
        """Initialize empty rename graph."""
        self._nodes: list[Any] = []
        self._edges: list[Any] = []
        self._current_file: FileItem | None = None
        self._file_index: int = 0
        self._total_files: int = 0

        logger.debug("[RenameGraph] Initialized empty graph")

    @property
    def nodes(self) -> list[Any]:
        """Get all nodes in graph."""
        return self._nodes.copy()

    @property
    def edges(self) -> list[Any]:
        """Get all edges in graph."""
        return self._edges.copy()

    @property
    def current_file(self) -> FileItem | None:
        """Get current file being processed."""
        return self._current_file

    @property
    def file_index(self) -> int:
        """Get current file index in batch."""
        return self._file_index

    @property
    def total_files(self) -> int:
        """Get total files in batch."""
        return self._total_files

    def set_file_context(
        self,
        file_item: FileItem,
        index: int,
        total: int
    ) -> None:
        """Set current file context for evaluation.

        Args:
            file_item: File being processed
            index: Index in batch (0-based)
            total: Total files in batch
        """
        self._current_file = file_item
        self._file_index = index
        self._total_files = total

    def clear_file_context(self) -> None:
        """Clear file context after evaluation."""
        self._current_file = None
        self._file_index = 0
        self._total_files = 0

    def add_node(self, node: Any) -> None:
        """Add node to graph.

        Args:
            node: Node instance to add
        """
        self._nodes.append(node)
        logger.debug("[RenameGraph] Added node: %s", type(node).__name__)

    def remove_node(self, node: Any) -> None:
        """Remove node from graph.

        Args:
            node: Node instance to remove
        """
        if node in self._nodes:
            self._nodes.remove(node)
            # Also remove connected edges
            self._edges = [e for e in self._edges if node not in (e.start_node, e.end_node)]
            logger.debug("[RenameGraph] Removed node: %s", type(node).__name__)

    def add_edge(self, edge: Any) -> None:
        """Add edge to graph.

        Args:
            edge: Edge instance to add
        """
        self._edges.append(edge)

    def remove_edge(self, edge: Any) -> None:
        """Remove edge from graph.

        Args:
            edge: Edge instance to remove
        """
        if edge in self._edges:
            self._edges.remove(edge)

    def find_output_node(self) -> Any | None:
        """Find the OutputNode in graph.

        Returns:
            OutputNode instance or None if not found
        """
        for node in self._nodes:
            if getattr(node, 'op_code', None) == 207:  # OutputNode op_code
                return node
        return None

    def get_topological_order(self) -> list[Any]:
        """Get nodes in topological order for execution.

        Returns:
            List of nodes ordered for execution (sources first)
        """
        # TODO: Implement proper topological sort
        # For now, return nodes as-is
        return self._nodes.copy()

    def serialize(self) -> dict[str, Any]:
        """Serialize graph to dict.

        Returns:
            Dict representation of graph
        """
        return {
            "version": "1.0.0",
            "nodes": [n.serialize() for n in self._nodes if hasattr(n, 'serialize')],
            "edges": [e.serialize() for e in self._edges if hasattr(e, 'serialize')],
        }

    def deserialize(self, data: dict[str, Any]) -> bool:
        """Deserialize graph from dict.

        Args:
            data: Dict representation of graph

        Returns:
            True if successful
        """
        # TODO: Implement deserialization
        logger.debug("[RenameGraph] Deserialize called with version: %s", data.get("version"))
        return True

    def clear(self) -> None:
        """Clear all nodes and edges."""
        self._nodes.clear()
        self._edges.clear()
        self.clear_file_context()
        logger.debug("[RenameGraph] Cleared graph")
