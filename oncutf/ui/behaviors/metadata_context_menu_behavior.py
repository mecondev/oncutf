"""Backward compatibility delegator for metadata_context_menu_behavior.

DEPRECATED: This module re-exports from the new package location.
Use `oncutf.ui.behaviors.metadata_context_menu` instead.

Author: Michael Economou
Date: December 28, 2025 (original), 2026-01-05 (converted to delegator)
"""
from oncutf.ui.behaviors.metadata_context_menu import (
    ContextMenuWidget,
    MetadataContextMenuBehavior,
)

__all__ = ["MetadataContextMenuBehavior", "ContextMenuWidget"]
