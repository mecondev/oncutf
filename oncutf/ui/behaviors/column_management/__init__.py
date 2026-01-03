"""Column management behavior package.

Re-exports main classes for backward compatibility.

Author: Michael Economou
Date: 2026-01-05
"""
from oncutf.ui.behaviors.column_management.column_behavior import (
    ColumnManagementBehavior,
)
from oncutf.ui.behaviors.column_management.protocols import ColumnManageableWidget

__all__ = ["ColumnManagementBehavior", "ColumnManageableWidget"]
