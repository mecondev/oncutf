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
from oncutf.ui.widgets.metadata_tree.model import (
    MetadataDisplayState,
    TreeNodeData,
)

# TODO Phase 2: Service
# from oncutf.ui.widgets.metadata_tree.service import MetadataTreeService
# TODO Phase 3: Controller
# from oncutf.ui.widgets.metadata_tree.controller import MetadataTreeController
# TODO Phase 4: View (re-export from refactored location)
# For now, import from legacy location for backwards compatibility
from oncutf.ui.widgets.metadata_tree_view import MetadataTreeView

__all__ = [
    # Data structures
    "TreeNodeData",
    "MetadataDisplayState",
    # Main widget (legacy location, will move in Phase 4)
    "MetadataTreeView",
]
