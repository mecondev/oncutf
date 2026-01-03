"""Backward compatibility delegator for column_management_behavior.

DEPRECATED: This module re-exports from the new package location.
Use `oncutf.ui.behaviors.column_management` instead.
Scheduled for removal in v2.0.

Author: Michael Economou
Date: 2025-12-28 (original), 2026-01-05 (converted to delegator)
"""
import warnings

warnings.warn(
    "oncutf.ui.behaviors.column_management_behavior is deprecated. "
    "Use oncutf.ui.behaviors.column_management instead. "
    "This module will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2,
)

from oncutf.ui.behaviors.column_management import (
    ColumnManageableWidget,
    ColumnManagementBehavior,
)

__all__ = ["ColumnManagementBehavior", "ColumnManageableWidget"]

