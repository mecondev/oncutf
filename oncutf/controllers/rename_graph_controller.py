"""Module: rename_graph_controller.py

Author: Michael Economou
Date: 2026-01-03

Controller bridging node editor UI and rename pipeline execution.

Responsibilities:
- Manage graph instance lifecycle
- Convert between graph and linear module formats
- Coordinate with UnifiedRenameEngine for execution
- Handle save/load of graph configurations
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from oncutf.core.rename_graph import RenameGraph, RenameGraphExecutor, RenameGraphValidator
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.controllers.module_orchestrator import ModuleOrchestrator
    from oncutf.models.file_item import FileItem

logger = get_cached_logger(__name__)


class RenameGraphController:
    """Controller for rename pipeline graph operations.

    Bridges the node editor UI with the rename execution system.
    Provides conversion between visual graph and module pipeline.

    Attributes:
        _graph: Current RenameGraph instance
        _orchestrator: ModuleOrchestrator for module compatibility
        _executor: Graph executor instance
    """

    def __init__(
        self,
        orchestrator: ModuleOrchestrator | None = None
    ) -> None:
        """Initialize controller.

        Args:
            orchestrator: Optional ModuleOrchestrator for module conversion
        """
        self._graph = RenameGraph()
        self._orchestrator = orchestrator
        self._executor = RenameGraphExecutor(self._graph)
        self._is_modified = False

        logger.info("[RenameGraphController] Initialized")

    @property
    def graph(self) -> RenameGraph:
        """Get current graph instance."""
        return self._graph

    @property
    def is_modified(self) -> bool:
        """Check if graph has unsaved changes."""
        return self._is_modified

    def new_graph(self) -> None:
        """Create new empty graph."""
        self._graph = RenameGraph()
        self._executor = RenameGraphExecutor(self._graph)
        self._is_modified = False
        logger.debug("[RenameGraphController] Created new graph")

    def validate(self) -> tuple[bool, list[str], list[str]]:
        """Validate current graph.

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        validator = RenameGraphValidator(self._graph)
        result = validator.validate()
        return result.is_valid, result.errors, result.warnings

    def execute_preview(
        self,
        file_items: list[FileItem]
    ) -> list[tuple[str, str]]:
        """Execute graph for preview (original_name, new_name pairs).

        Args:
            file_items: Files to preview

        Returns:
            List of (original_name, new_name) tuples
        """
        results: list[tuple[str, str]] = []

        total = len(file_items)
        for index, file_item in enumerate(file_items):
            new_name = self._executor.execute_preview(file_item, index, total)
            if new_name is None:
                new_name = file_item.name
            results.append((file_item.name, new_name))

        return results

    def execute(self, file_items: list[FileItem]) -> list[str]:
        """Execute graph to generate filenames.

        Args:
            file_items: Files to process

        Returns:
            List of generated filenames

        Raises:
            GraphExecutionError: If validation or execution fails
        """
        return self._executor.execute(file_items)

    def save_graph(self, file_path: str | Path) -> bool:
        """Save graph to JSON file.

        Args:
            file_path: Path to save file

        Returns:
            True if successful
        """
        import json

        try:
            path = Path(file_path)
            data = self._graph.serialize()

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            self._is_modified = False
            logger.info("[RenameGraphController] Saved graph to: %s", path)
            return True

        except Exception as e:
            logger.exception("[RenameGraphController] Failed to save graph: %s", e)
            return False

    def load_graph(self, file_path: str | Path) -> bool:
        """Load graph from JSON file.

        Args:
            file_path: Path to load file

        Returns:
            True if successful
        """
        import json

        try:
            path = Path(file_path)

            with open(path, encoding='utf-8') as f:
                data = json.load(f)

            self._graph = RenameGraph()
            success = self._graph.deserialize(data)

            if success:
                self._executor = RenameGraphExecutor(self._graph)
                self._is_modified = False
                logger.info("[RenameGraphController] Loaded graph from: %s", path)

            return success

        except Exception as e:
            logger.exception("[RenameGraphController] Failed to load graph: %s", e)
            return False

    def mark_modified(self) -> None:
        """Mark graph as having unsaved changes."""
        self._is_modified = True

    # =========================================
    # Module Conversion (Backward Compatibility)
    # =========================================

    def from_module_data(self, module_data: list[dict[str, Any]]) -> bool:
        """Convert linear module configuration to graph.

        Args:
            module_data: List of module configurations (from get_all_data())

        Returns:
            True if successful
        """
        # TODO: Implement module-to-graph conversion
        # 1. Create appropriate nodes for each module
        # 2. Connect nodes in sequence
        # 3. Add OutputNode at end
        logger.debug(
            "[RenameGraphController] from_module_data: %d modules",
            len(module_data)
        )
        return True

    def to_module_data(self) -> list[dict[str, Any]]:
        """Convert graph to linear module configuration.

        Returns:
            List of module configurations compatible with get_all_data()
        """
        # TODO: Implement graph-to-module conversion
        # 1. Traverse graph in order
        # 2. Convert each node to module config
        # 3. Return list compatible with existing system
        logger.debug("[RenameGraphController] to_module_data called")
        return []

    # =========================================
    # Graph Building Helpers
    # =========================================

    def add_node_by_type(self, node_type: str) -> Any | None:
        """Add node to graph by type name.

        Args:
            node_type: Type name (e.g., 'counter', 'original_name')

        Returns:
            Created node or None if type unknown
        """
        # TODO: Implement node factory
        # Use node_editor NodeRegistry to create appropriate node
        logger.debug("[RenameGraphController] add_node_by_type: %s", node_type)
        return None

    def connect_nodes(
        self,
        source_node: Any,
        source_output: int,
        target_node: Any,
        target_input: int,
    ) -> bool:
        """Connect two nodes.

        Args:
            source_node: Node with output
            source_output: Output socket index
            target_node: Node with input
            target_input: Input socket index

        Returns:
            True if connection successful
        """
        # TODO: Implement edge creation
        logger.debug("[RenameGraphController] connect_nodes called")
        return False
