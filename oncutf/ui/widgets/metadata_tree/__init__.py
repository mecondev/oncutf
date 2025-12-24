"""Package: metadata_tree

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

from __future__ import annotations

from typing import TYPE_CHECKING

# Phase 1: Data model only
# Phase 3: Controller layer
from oncutf.ui.widgets.metadata_tree.controller import (
    MetadataTreeController,
    create_metadata_tree_controller,
)

# Drag handler - import directly to avoid circular import
from oncutf.ui.widgets.metadata_tree.drag_handler import MetadataTreeDragHandler
from oncutf.ui.widgets.metadata_tree.model import (
    EXTENDED_ONLY_PATTERNS,
    METADATA_GROUPS,
    READ_ONLY_FIELDS,
    FieldStatus,
    MetadataDisplayState,
    NodeType,
    TreeNodeData,
)

# Modifications handler
from oncutf.ui.widgets.metadata_tree.modifications_handler import MetadataTreeModificationsHandler

# Search handler
from oncutf.ui.widgets.metadata_tree.search_handler import MetadataTreeSearchHandler

# Selection handler
from oncutf.ui.widgets.metadata_tree.selection_handler import MetadataTreeSelectionHandler

# Phase 2: Service layer
from oncutf.ui.widgets.metadata_tree.service import (
    MetadataTreeService,
    create_metadata_tree_service,
)

# View configuration handler
from oncutf.ui.widgets.metadata_tree.view_config import MetadataTreeViewConfig

# MetadataTreeView is imported lazily to avoid circular imports
# (metadata_tree_view.py imports from this package)
if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_tree_view import MetadataTreeView


def __getattr__(name: str):
    """Lazy import for MetadataTreeView to avoid circular imports."""
    if name == "MetadataTreeView":
        from oncutf.ui.widgets.metadata_tree_view import MetadataTreeView

        return MetadataTreeView
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
    # Handlers
    "MetadataTreeDragHandler",
    "MetadataTreeViewConfig",
    "MetadataTreeSearchHandler",
    "MetadataTreeSelectionHandler",
    "MetadataTreeModificationsHandler",
    "MetadataTreeCacheHandler",
    # Main widget
    "MetadataTreeView",
]
