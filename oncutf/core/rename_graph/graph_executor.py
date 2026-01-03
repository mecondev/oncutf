"""Module: graph_executor.py

Author: Michael Economou
Date: 2026-01-03

Execute rename pipeline graphs to generate filenames.

Traverses graph in topological order, evaluates each node,
and collects final filename from OutputNode.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from oncutf.core.rename_graph.graph_validator import RenameGraphValidator, ValidationResult
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.core.rename_graph.graph_model import RenameGraph
    from oncutf.models.file_item import FileItem

logger = get_cached_logger(__name__)


class GraphExecutionError(Exception):
    """Raised when graph execution fails."""


class RenameGraphExecutor:
    """Executes rename pipeline graph to generate filenames.

    Takes a validated graph and list of FileItems, executes the graph
    for each file, and returns the generated filenames.

    Attributes:
        _graph: RenameGraph to execute
        _validator: Validator for pre-execution checks
    """

    def __init__(self, graph: RenameGraph) -> None:
        """Initialize executor with graph.

        Args:
            graph: RenameGraph to execute
        """
        self._graph = graph
        self._validator = RenameGraphValidator(graph)

    def validate(self) -> ValidationResult:
        """Validate graph before execution.

        Returns:
            ValidationResult with is_valid, errors, warnings
        """
        return self._validator.validate()

    def execute(
        self,
        file_items: list[FileItem],
        validate_first: bool = True,
    ) -> list[str]:
        """Execute graph for all file items.

        Args:
            file_items: List of files to process
            validate_first: Whether to validate graph before execution

        Returns:
            List of generated filenames (same order as file_items)

        Raises:
            GraphExecutionError: If validation fails or execution error
        """
        # Validate graph
        if validate_first:
            result = self.validate()
            if not result.is_valid:
                raise GraphExecutionError(
                    f"Graph validation failed: {', '.join(result.errors)}"
                )

        filenames: list[str] = []
        total = len(file_items)

        logger.debug("[RenameGraphExecutor] Executing graph for %d files", total)

        for index, file_item in enumerate(file_items):
            try:
                filename = self._execute_single(file_item, index, total)
                filenames.append(filename)
            except Exception as e:
                logger.error(
                    "[RenameGraphExecutor] Failed on file %s: %s",
                    file_item.full_path, e
                )
                # Use original name on error
                filenames.append(file_item.name)

        return filenames

    def _execute_single(
        self,
        file_item: FileItem,
        index: int,
        total: int
    ) -> str:
        """Execute graph for single file.

        Args:
            file_item: File to process
            index: Index in batch (0-based)
            total: Total files in batch

        Returns:
            Generated filename
        """
        # Set file context
        self._graph.set_file_context(file_item, index, total)

        try:
            # Get topological order
            nodes = self._graph.get_topological_order()

            # Evaluate all nodes (they cache their values)
            for node in nodes:
                if hasattr(node, 'eval'):
                    node.eval()

            # Get result from OutputNode
            output_node = self._graph.find_output_node()
            if output_node is None:
                raise GraphExecutionError("No OutputNode found")

            # Get value from OutputNode
            result = getattr(output_node, 'value', None)
            if result is None:
                # Fallback: try to get from input
                if hasattr(output_node, 'get_input'):
                    input_node = output_node.get_input(0)
                    if input_node is not None:
                        result = input_node.eval()

            if result is None:
                result = file_item.name  # Fallback to original

            return str(result)

        finally:
            # Clear context
            self._graph.clear_file_context()

    def execute_preview(
        self,
        file_item: FileItem,
        index: int = 0,
        total: int = 1,
    ) -> str | None:
        """Execute graph for preview (single file, no validation).

        Args:
            file_item: File to preview
            index: Index in batch
            total: Total files

        Returns:
            Generated filename or None on error
        """
        try:
            return self._execute_single(file_item, index, total)
        except Exception as e:
            logger.debug("[RenameGraphExecutor] Preview failed: %s", e)
            return None

    def get_execution_order(self) -> list[dict[str, Any]]:
        """Get execution order for debugging/visualization.

        Returns:
            List of node info dicts in execution order
        """
        nodes = self._graph.get_topological_order()
        return [
            {
                "title": getattr(n, 'title', 'Unknown'),
                "op_code": getattr(n, 'op_code', None),
                "id": getattr(n, 'sid', id(n)),
            }
            for n in nodes
        ]
