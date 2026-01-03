"""Backward compatibility delegator for column_management_behavior.

DEPRECATED: This module re-exports from the new package location.
Use `oncutf.ui.behaviors.column_management` instead.

Author: Michael Economou
Date: 2025-12-28 (original), 2026-01-05 (converted to delegator)
"""
from oncutf.ui.behaviors.column_management import (
    ColumnManageableWidget,
    ColumnManagementBehavior,
)

__all__ = ["ColumnManagementBehavior", "ColumnManageableWidget"]

