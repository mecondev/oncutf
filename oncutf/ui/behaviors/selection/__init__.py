"""Selection behavior package.

Re-exports main classes for backward compatibility.

Author: Michael Economou
Date: 2026-01-05
"""

from oncutf.ui.behaviors.selection.protocols import SelectableWidget
from oncutf.ui.behaviors.selection.selection_behavior import SelectionBehavior

__all__ = ["SelectableWidget", "SelectionBehavior"]
