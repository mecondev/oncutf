"""Selection management package.

Author: Michael Economou
Date: 2025-01-19

This package provides selection management and state storage
for the oncutf application.
"""

from __future__ import annotations

from .selection_manager import SelectionManager
from .selection_store import SelectionStore

__all__ = [
    "SelectionManager",
    "SelectionStore",
]
