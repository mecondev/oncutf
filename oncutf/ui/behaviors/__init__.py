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
        self.selection_behavior = SelectionBehavior(self)
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

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.core.pyqt_imports import QPoint, QWidget

logger = get_cached_logger(__name__)


# =============================================================================
# Protocol Definitions (Widget Interface Contracts)
# =============================================================================


@runtime_checkable
class SelectableWidget(Protocol):
    """Protocol defining interface for widgets that support selection.

    Any widget implementing this protocol can use SelectionBehavior.
    This makes the dependency explicit and testable.
    """

    def selectionModel(self) -> Any:
        """Return the selection model."""
        ...

    def model(self) -> Any:
        """Return the data model."""
        ...

    def blockSignals(self, block: bool) -> bool:
        """Block/unblock signals."""
        ...

    def viewport(self) -> QWidget:
        """Return the viewport widget."""
        ...


@runtime_checkable
class DraggableWidget(Protocol):
    """Protocol defining interface for widgets that support drag & drop.

    Any widget implementing this protocol can use DragDropBehavior.
    """

    def model(self) -> Any:
        """Return the data model."""
        ...

    def viewport(self) -> QWidget:
        """Return the viewport widget."""
        ...

    def rect(self) -> Any:
        """Return widget rectangle."""
        ...

    def mapFromGlobal(self, pos: QPoint) -> QPoint:
        """Map global position to local."""
        ...


# =============================================================================
# Base Behavior Class
# =============================================================================


class BaseBehavior(ABC):
    """Abstract base class for all widget behaviors.

    Provides common infrastructure for composition-based behaviors:
    - Widget reference management
    - Initialization state tracking
    - Cleanup lifecycle
    """

    def __init__(self, widget: Any) -> None:
        """Initialize behavior with widget reference.

        Args:
            widget: The widget this behavior is attached to

        """
        self._widget = widget
        self._initialized = False
        self._setup()
        self._initialized = True
        logger.debug(
            "[%s] Initialized for widget %s",
            self.__class__.__name__,
            widget.__class__.__name__,
            extra={"dev_only": True},
        )

    @property
    def widget(self) -> Any:
        """Get the associated widget."""
        return self._widget

    @property
    def is_initialized(self) -> bool:
        """Check if behavior is fully initialized."""
        return self._initialized

    @abstractmethod
    def _setup(self) -> None:
        """Setup behavior - override in subclasses.

        Called during __init__ to perform any necessary setup.
        Widget reference is available via self._widget.
        """

    def cleanup(self) -> None:
        """Cleanup behavior resources.

        Override in subclasses to disconnect signals, release resources, etc.
        Called when behavior should be deactivated.
        """
        self._initialized = False
        logger.debug(
            "[%s] Cleaned up",
            self.__class__.__name__,
            extra={"dev_only": True},
        )


# =============================================================================
# Concrete Behavior Implementations (Examples/Scaffolding)
# =============================================================================


class SelectionBehavior(BaseBehavior):
    """Behavior providing selection management for table-like widgets.

    This is a composition-based alternative to SelectionMixin.
    For new widgets, prefer this pattern. Existing widgets using
    SelectionMixin should NOT be migrated without careful testing.

    Example usage:
        class MyNewTableView(QTableView):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.selection = SelectionBehavior(self)

            def get_selected_rows(self) -> set[int]:
                return self.selection.get_selected_rows()
    """

    def __init__(self, widget: SelectableWidget) -> None:
        """Initialize selection behavior.

        Args:
            widget: Widget implementing SelectableWidget protocol

        """
        # State tracking
        self._selected_rows: set[int] = set()
        self._anchor_row: int | None = None
        self._processing_change: bool = False

        super().__init__(widget)

    def _setup(self) -> None:
        """Setup selection tracking."""
        # Could connect to selection model signals here if needed

    def get_selected_rows(self) -> set[int]:
        """Get currently selected row indices.

        Returns:
            Set of selected row indices

        """
        return self._selected_rows.copy()

    def set_selected_rows(self, rows: set[int], emit_signal: bool = True) -> None:
        """Set selection to specific rows.

        Args:
            rows: Set of row indices to select
            emit_signal: Whether to emit selection changed signal

        """
        if self._processing_change:
            return

        self._processing_change = True
        try:
            self._selected_rows = rows.copy()
            if emit_signal:
                self._sync_to_widget()
        finally:
            self._processing_change = False

    def _sync_to_widget(self) -> None:
        """Sync internal state to widget's selection model."""
        widget = self._widget
        if not hasattr(widget, "selectionModel") or not widget.selectionModel():
            return

        # Implementation would sync to Qt selection model
        # Keeping simple for scaffolding example

    def clear_selection(self) -> None:
        """Clear all selections."""
        self.set_selected_rows(set())
        self._anchor_row = None


class DragDropBehavior(BaseBehavior):
    """Behavior providing drag & drop functionality for widgets.

    This is a composition-based alternative to DragDropMixin.
    For new widgets, prefer this pattern.

    Example usage:
        class MyNewTableView(QTableView):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.drag_drop = DragDropBehavior(self)

            def mousePressEvent(self, event):
                self.drag_drop.handle_mouse_press(event)
                super().mousePressEvent(event)
    """

    def __init__(self, widget: DraggableWidget) -> None:
        """Initialize drag & drop behavior.

        Args:
            widget: Widget implementing DraggableWidget protocol

        """
        # State tracking
        self._is_dragging: bool = False
        self._drag_data: list[str] | None = None
        self._drag_start_pos: QPoint | None = None

        super().__init__(widget)

    def _setup(self) -> None:
        """Setup drag & drop infrastructure."""
        # Could setup event filters or signal connections here

    @property
    def is_dragging(self) -> bool:
        """Check if drag operation is in progress."""
        return self._is_dragging

    def start_drag(self, file_paths: list[str]) -> None:
        """Start a drag operation with given files.

        Args:
            file_paths: List of file paths to drag

        """
        if self._is_dragging:
            logger.warning("[DragDropBehavior] Drag already in progress")
            return

        self._is_dragging = True
        self._drag_data = file_paths
        logger.debug(
            "[DragDropBehavior] Started drag with %d files",
            len(file_paths),
            extra={"dev_only": True},
        )

    def end_drag(self) -> None:
        """End current drag operation."""
        self._is_dragging = False
        self._drag_data = None
        self._drag_start_pos = None
        logger.debug("[DragDropBehavior] Drag ended", extra={"dev_only": True})

    def handle_mouse_press(self, event: Any) -> bool:
        """Handle mouse press for potential drag start.

        Args:
            event: Mouse event

        Returns:
            True if event was handled, False otherwise

        """
        # Store potential drag start position
        self._drag_start_pos = event.pos() if hasattr(event, "pos") else None
        return False  # Don't consume the event

    def cleanup(self) -> None:
        """Cleanup drag state."""
        self.end_drag()
        super().cleanup()


class MetadataEditBehavior(BaseBehavior):
    """Behavior providing metadata editing functionality.

    This is a composition-based alternative to MetadataEditMixin.
    Handles staging, validation, and committing of metadata changes.

    Example usage:
        class MyMetadataWidget(QTreeView):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.metadata_edit = MetadataEditBehavior(self)

            def on_edit_complete(self, key, value):
                self.metadata_edit.stage_change(self.current_file, key, value)
    """

    def __init__(self, widget: Any) -> None:
        """Initialize metadata edit behavior.

        Args:
            widget: Parent widget

        """
        self._pending_changes: dict[str, dict[str, str]] = {}
        super().__init__(widget)

    def _setup(self) -> None:
        """Setup metadata editing infrastructure."""

    def stage_change(self, file_path: str, key: str, value: str) -> None:
        """Stage a metadata change for later commit.

        Args:
            file_path: Path to the file being edited
            key: Metadata key
            value: New value

        """
        if file_path not in self._pending_changes:
            self._pending_changes[file_path] = {}

        self._pending_changes[file_path][key] = value
        logger.debug(
            "[MetadataEditBehavior] Staged: %s[%s] = %s",
            file_path,
            key,
            value[:50] if len(value) > 50 else value,
            extra={"dev_only": True},
        )

    def get_pending_changes(self, file_path: str | None = None) -> dict:
        """Get pending changes for file or all files.

        Args:
            file_path: Specific file path, or None for all

        Returns:
            Dict of pending changes

        """
        if file_path:
            return self._pending_changes.get(file_path, {}).copy()
        return {k: v.copy() for k, v in self._pending_changes.items()}

    def has_pending_changes(self) -> bool:
        """Check if there are any pending changes."""
        return bool(self._pending_changes)

    def clear_changes(self, file_path: str | None = None) -> None:
        """Clear pending changes.

        Args:
            file_path: Specific file to clear, or None for all

        """
        if file_path:
            self._pending_changes.pop(file_path, None)
        else:
            self._pending_changes.clear()


# =============================================================================
# Factory Functions (Optional convenience)
# =============================================================================


def create_selection_behavior(widget: SelectableWidget) -> SelectionBehavior:
    """Create a SelectionBehavior for a widget.

    Args:
        widget: Widget implementing SelectableWidget protocol

    Returns:
        Configured SelectionBehavior instance

    """
    return SelectionBehavior(widget)


def create_drag_drop_behavior(widget: DraggableWidget) -> DragDropBehavior:
    """Create a DragDropBehavior for a widget.

    Args:
        widget: Widget implementing DraggableWidget protocol

    Returns:
        Configured DragDropBehavior instance

    """
    return DragDropBehavior(widget)


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
