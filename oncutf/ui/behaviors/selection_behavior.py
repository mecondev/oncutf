"""Backward compatibility delegator for selection_behavior.

DEPRECATED: This module re-exports from the new package location.
Use `oncutf.ui.behaviors.selection` instead.

Author: Michael Economou
Date: 2025-12-28 (original), 2026-01-05 (converted to delegator)
"""
from oncutf.ui.behaviors.selection import SelectableWidget, SelectionBehavior

__all__ = ["SelectionBehavior", "SelectableWidget"]
