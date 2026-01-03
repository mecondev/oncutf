"""Undo/redo history system for scene operations.

This module implements the SceneHistory class which provides undo/redo
functionality by storing serialized snapshots of the scene state. Each
snapshot includes the complete scene graph and current selection state.

The history system supports:
    - Configurable stack depth (default 32 steps)
    - Selection state preservation across undo/redo
    - Event callbacks for history changes
    - Automatic truncation of future history on new edits

Author:
    Michael Economou

Date:
    2025-12-11
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oncutf.ui.widgets.node_editor.core.scene import Scene

logger = logging.getLogger(__name__)


@dataclass
class HistoryStamp:
    """Snapshot of scene state for undo/redo.

    Attributes:
        desc: Human-readable description of this snapshot.
        snapshot: Serialized scene data (nodes, edges, etc.).
        selection: Dict with 'nodes' and 'edges' lists of selected IDs.
    """

    desc: str
    snapshot: dict
    selection: dict


class SceneHistory:
    """Undo/redo stack manager for scene state.

    Maintains a stack of serialized scene snapshots that can be navigated
    with undo/redo operations. Each snapshot captures the complete scene
    graph and current selection, allowing restoration to any previous state.

    The stack has a configurable limit (default 32). When the limit is
    reached, oldest entries are removed. Performing an edit after undo
    truncates the future history.

    Attributes:
        scene: Parent Scene being tracked.
        history_limit: Maximum snapshots to retain (default: 32).
        history_stack: List of history stamp dictionaries.
        history_current_step: Index of current position in stack.
        undo_selection_has_changed: True if last undo/redo changed selection.
    """

    def __init__(self, scene: Scene) -> None:
        """Initialize history tracker for a scene.

        Args:
            scene: Scene instance to track.
        """
        self.scene = scene

        self.history_stack: list[HistoryStamp] = []
        self.history_current_step: int = -1
        self.history_limit: int = 32

        self.undo_selection_has_changed: bool = False

        self._history_modified_listeners: list[Callable] = []
        self._history_stored_listeners: list[Callable] = []
        self._history_restored_listeners: list[Callable] = []

    def clear(self) -> None:
        """Clear all history and reset to initial state."""
        self.history_stack = []
        self.history_current_step = -1

    def store_initial_history_stamp(self) -> None:
        """Create baseline history entry for new or loaded file.

        Call after creating or loading a scene to establish the initial
        state for undo operations.
        """
        self.store_history("Initial History Stamp")

    # Event listener management

    def add_history_modified_listener(self, callback: Callable) -> None:
        """Register callback for any history stack change.

        Called on store, undo, or redo operations.

        Args:
            callback: Function to call on history modification.
        """
        self._history_modified_listeners.append(callback)

    def add_history_stored_listener(self, callback: Callable) -> None:
        """Register callback for new history entries.

        Args:
            callback: Function to call when history is stored.
        """
        self._history_stored_listeners.append(callback)

    def add_history_restored_listener(self, callback: Callable) -> None:
        """Register callback for undo/redo operations.

        Args:
            callback: Function to call when history is restored.
        """
        self._history_restored_listeners.append(callback)

    def remove_history_stored_listener(self, callback: Callable) -> None:
        """Unregister history stored callback.

        Args:
            callback: Previously registered function to remove.
        """
        if callback in self._history_stored_listeners:
            self._history_stored_listeners.remove(callback)

    def remove_history_restored_listener(self, callback: Callable) -> None:
        """Unregister history restored callback.

        Args:
            callback: Previously registered function to remove.
        """
        if callback in self._history_restored_listeners:
            self._history_restored_listeners.remove(callback)

    # Undo/Redo capabilities

    def can_undo(self) -> bool:
        """Check if undo operation is available.

        Returns:
            True if there is history to undo.
        """
        return self.history_current_step > 0

    def can_redo(self) -> bool:
        """Check if redo operation is available.

        Returns:
            True if there is forward history to restore.
        """
        return self.history_current_step + 1 < len(self.history_stack)

    # Undo/Redo operations

    def undo(self) -> None:
        """Revert to previous history state.

        Moves back one step in history and restores that snapshot.
        Marks scene as modified.
        """
        if self.can_undo():
            self.history_current_step -= 1
            self.restore_history()
            self.scene.has_been_modified = True

    def redo(self) -> None:
        """Advance to next history state.

        Moves forward one step in history and restores that snapshot.
        Marks scene as modified.
        """
        if self.can_redo():
            self.history_current_step += 1
            self.restore_history()
            self.scene.has_been_modified = True

    # History management

    def store_history(self, desc: str, set_modified: bool = False) -> None:
        """Save current scene state to history stack.

        Creates a snapshot of the scene including all nodes, edges, and
        current selection. Truncates any forward history if current
        position is not at the end. Removes oldest entry if stack limit
        is reached.

        Args:
            desc: Human-readable description of this history entry.
            set_modified: If True, mark scene as having unsaved changes.
        """
        if set_modified:
            self.scene.has_been_modified = True

        if self.history_current_step + 1 < len(self.history_stack):
            self.history_stack = self.history_stack[0 : self.history_current_step + 1]

        if self.history_current_step + 1 >= self.history_limit:
            self.history_stack = self.history_stack[1:]
            self.history_current_step -= 1

        hs = self.create_history_stamp(desc)
        self.history_stack.append(hs)
        self.history_current_step += 1

        for callback in self._history_modified_listeners:
            callback()
        for callback in self._history_stored_listeners:
            callback()

    def restore_history(self) -> None:
        """Apply history snapshot at current position.

        Deserializes the scene from the current history stamp and
        restores selection state. Triggers history modified and
        restored callbacks.
        """
        self.restore_history_stamp(self.history_stack[self.history_current_step])

        for callback in self._history_modified_listeners:
            callback()
        for callback in self._history_restored_listeners:
            callback()

    # History stamp creation and restoration

    def capture_current_selection(self) -> dict:
        """Record currently selected nodes and edges.

        Returns:
            Dict with 'nodes' and 'edges' lists containing object IDs.
        """
        sel_obj = {
            "nodes": [],
            "edges": [],
        }

        for item in self.scene.graphics_scene.selectedItems():
            if hasattr(item, "node"):
                sel_obj["nodes"].append(item.node.sid)
            elif hasattr(item, "edge"):
                sel_obj["edges"].append(item.edge.sid)

        return sel_obj

    def create_history_stamp(self, desc: str) -> HistoryStamp:
        """Create complete history snapshot.

        Serializes entire scene state and current selection into a
        HistoryStamp dataclass that can later be restored.

        Args:
            desc: Human-readable label for this snapshot.

        Returns:
            HistoryStamp containing description, scene snapshot, and selection.
        """
        return HistoryStamp(
            desc=desc,
            snapshot=self.scene.serialize_snapshot(),
            selection=self.capture_current_selection(),
        )

    def restore_history_stamp(self, history_stamp: HistoryStamp) -> None:
        """Apply a history snapshot to the scene.

        Deserializes the scene graph and restores selection state.
        Sets undo_selection_has_changed if selection differs from
        previous state.

        Args:
            history_stamp: Previously created history snapshot.
        """
        try:
            self.undo_selection_has_changed = False
            previous_selection = self.capture_current_selection()

            self.scene.deserialize_snapshot(history_stamp.snapshot)

            for edge in self.scene.edges:
                edge.graphics_edge.setSelected(False)

            for edge_id in history_stamp.selection["edges"]:
                for edge in self.scene.edges:
                    if edge.sid == edge_id:
                        edge.graphics_edge.setSelected(True)
                        break

            for node in self.scene.nodes:
                node.graphics_node.setSelected(False)

            for node_id in history_stamp.selection["nodes"]:
                for node in self.scene.nodes:
                    if node.sid == node_id:
                        node.graphics_node.setSelected(True)
                        break

            current_selection = self.capture_current_selection()

            self.scene._last_selected_items = self.scene.get_selected_items()

            if (
                current_selection["nodes"] != previous_selection["nodes"]
                or current_selection["edges"] != previous_selection["edges"]
            ):
                self.undo_selection_has_changed = True

        except Exception as e:
            from oncutf.ui.widgets.node_editor.utils.helpers import dump_exception

            dump_exception(e)
