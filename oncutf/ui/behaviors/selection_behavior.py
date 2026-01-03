"""Backward compatibility delegator for selection_behavior.

DEPRECATED: This module re-exports from the new package location.
Use `oncutf.ui.behaviors.selection` instead.
Scheduled for removal in v2.0.

Author: Michael Economou
Date: 2025-12-28 (original), 2026-01-05 (converted to delegator)
"""
import warnings

warnings.warn(
    "oncutf.ui.behaviors.selection_behavior is deprecated. "
    "Use oncutf.ui.behaviors.selection instead. "
    "This module will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2,
)

from oncutf.ui.behaviors.selection import SelectableWidget, SelectionBehavior

__all__ = ["SelectionBehavior", "SelectableWidget"]
