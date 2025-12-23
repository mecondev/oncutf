"""
Package: metadata_tree

Author: Michael Economou
Date: 2025-12-23

Metadata tree widget package with layered architecture.

This package provides a clean separation of concerns for the metadata tree:
- model: Pure data structures (no Qt dependencies)
- service: Business logic and data transformation
- controller: Orchestration between UI and services
- view: Qt widget (UI only)

Usage:
    from oncutf.ui.widgets.metadata_tree import MetadataTreeView

For advanced usage:
    from oncutf.ui.widgets.metadata_tree.model import TreeNodeData, MetadataDisplayState
    from oncutf.ui.widgets.metadata_tree.service import MetadataTreeService
    from oncutf.ui.widgets.metadata_tree.controller import MetadataTreeController
"""

# Phase 1: Data model only
# Phase 3: Controller layer
from oncutf.ui.widgets.metadata_tree.controller import (
    MetadataTreeController,
    create_metadata_tree_controller,
)
from oncutf.ui.widgets.metadata_tree.model import (
    EXTENDED_ONLY_PATTERNS,
    METADATA_GROUPS,
    READ_ONLY_FIELDS,
    FieldStatus,
    MetadataDisplayState,
    NodeType,
    TreeNodeData,
)

# Phase 2: Service layer
from oncutf.ui.widgets.metadata_tree.service import (
    MetadataTreeService,
    create_metadata_tree_service,
)

# TODO Phase 4: View (re-export from refactored location)
# For now, import from legacy location for backwards compatibility
from oncutf.ui.widgets.metadata_tree_view import MetadataTreeView

__all__ = [
    # Data structures
    "TreeNodeData",
    "MetadataDisplayState",
    "NodeType",
    "FieldStatus",
    "METADATA_GROUPS",
    "READ_ONLY_FIELDS",
    "EXTENDED_ONLY_PATTERNS",
    # Service layer
    "MetadataTreeService",
    "create_metadata_tree_service",
    # Controller layer
    "MetadataTreeController",
    "create_metadata_tree_controller",
    # Main widget (legacy location, will move in Phase 4)
    "MetadataTreeView",
]
