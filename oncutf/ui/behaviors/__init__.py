"""Behavior composition pattern for widget functionality.

Author: Michael Economou
Date: 2025-12-28

This module provides a composition-based alternative to mixins for adding
reusable behavior to Qt widgets. While existing mixins work well and should
not be replaced without careful consideration, NEW code paths should prefer
this pattern for better testability and explicit dependencies.

Why composition over mixins?
----------------------------
1. Explicit dependencies: Behaviors receive their dependencies via constructor
2. Better testability: Behaviors can be unit tested in isolation
3. No MRO complexity: No concerns about mixin initialization order
4. Clear contracts: TypedDict or Protocol defines the widget interface
5. Single responsibility: Each behavior handles one concern

Available Behaviors:
-------------------
- SelectionBehavior: Row selection with anchor handling
- DragDropBehavior: Drag-and-drop operations with visual feedback
- ColumnManagementBehavior: Column width/visibility management with delayed save
- MetadataScrollBehavior: Scroll position memory per file with expand/collapse state
- MetadataCacheBehavior: Metadata cache interaction with lazy loading and icon updates
- MetadataContextMenuBehavior: Context menu operations with column management

Usage Example:
--------------
```python
# Instead of:
class MyTableView(SelectionMixin, DragDropMixin, QTableView):
    pass

# Prefer for NEW widgets:
class MyTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selection_behavior = SelectionBehavior(self)
        self._drag_drop_behavior = DragDropBehavior(self)
        self._column_mgmt = ColumnManagementBehavior(self)
        self.drag_drop_behavior = DragDropBehavior(self)
```

Migration Strategy:
-------------------
- DO NOT rewrite existing mixins - they work and are well-tested
- USE this pattern for NEW widget functionality
- CONSIDER gradual migration when mixins become problematic
- DOCUMENT which approach is used in each widget

Naming Convention:
------------------
- *Behavior: Composition-based behavioral components
- *Mixin: Inheritance-based mixins (existing pattern)
"""

from __future__ import annotations

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


# =============================================================================
# Protocol Definitions (Widget Interface Contracts)
# =============================================================================
# Note: Protocols are now defined in their respective behavior modules
# Imported at the end of this file for backward compatibility


# =============================================================================
# Concrete Behavior Implementations
# =============================================================================
# Note: Concrete behaviors are now in separate modules:
# - selection_behavior.py: SelectionBehavior, SelectableWidget
# - drag_drop_behavior.py: DragDropBehavior, DraggableWidget
# - column_management_behavior.py: ColumnManagementBehavior, ColumnManageableWidget

# Import them at the end of this file for export


# =============================================================================
# Migration Notes
# =============================================================================

"""
MIGRATION GUIDELINES
====================

When to migrate from Mixin to Behavior:
---------------------------------------
1. Creating a NEW widget that needs selection/drag-drop/editing functionality
2. Mixin initialization order is causing bugs
3. Need to unit test behavior in isolation
4. Widget has too many mixins (> 3-4)

When NOT to migrate:
--------------------
1. Existing widget is stable and well-tested
2. Mixin approach is working without issues
3. No clear benefit from composition pattern
4. Risk of regression outweighs benefits

Step-by-step migration:
-----------------------
1. Create the Behavior instance in widget __init__
2. Delegate method calls to behavior
3. Update tests to test behavior in isolation
4. Remove mixin from inheritance chain
5. Clean up any leftover mixin attributes/methods

Example migration diff:
-----------------------
# Before:
class FileTableView(SelectionMixin, DragDropMixin, QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        # mixin init happens via super()

# After:
class FileTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selection = SelectionBehavior(self)
        self._drag_drop = DragDropBehavior(self)

    def get_selected_rows(self):
        return self._selection.get_selected_rows()
"""

# Export all public interfaces
from oncutf.ui.behaviors.column_management_behavior import (
    ColumnManageableWidget,
    ColumnManagementBehavior,
)
from oncutf.ui.behaviors.drag_drop_behavior import DragDropBehavior, DraggableWidget
from oncutf.ui.behaviors.metadata_cache_behavior import (
    CacheableWidget,
    MetadataCacheBehavior,
)
from oncutf.ui.behaviors.metadata_context_menu_behavior import (
    ContextMenuWidget,
    MetadataContextMenuBehavior,
)
from oncutf.ui.behaviors.metadata_scroll_behavior import (
    MetadataScrollBehavior,
    ScrollableTreeWidget,
)
from oncutf.ui.behaviors.selection_behavior import SelectableWidget, SelectionBehavior

__all__ = [
    # Protocols
    "SelectableWidget",
    "DraggableWidget",
    "ColumnManageableWidget",
    "ScrollableTreeWidget",
    "CacheableWidget",
    "ContextMenuWidget",
    # Concrete behaviors
    "SelectionBehavior",
    "DragDropBehavior",
    "ColumnManagementBehavior",
    "MetadataScrollBehavior",
    "MetadataCacheBehavior",
    "MetadataContextMenuBehavior",
]
