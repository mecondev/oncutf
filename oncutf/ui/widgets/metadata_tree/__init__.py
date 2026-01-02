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

Public API:
    - MetadataTreeView: The main widget (only public export)

Internal modules (import directly if needed):
    - model: TreeNodeData, MetadataDisplayState, NodeType, FieldStatus
    - service: MetadataTreeService
    - controller: MetadataTreeController
    - handlers: render_handler, ui_state_handler, search_handler, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# MetadataTreeView is imported lazily to avoid circular imports
# (view.py imports from this package)
if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_tree.view import MetadataTreeView


def __getattr__(name: str):
    """Lazy import for MetadataTreeView to avoid circular imports."""
    if name == "MetadataTreeView":
        from oncutf.ui.widgets.metadata_tree.view import MetadataTreeView

        return MetadataTreeView
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "MetadataTreeView",
]
