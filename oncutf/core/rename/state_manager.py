"""oncutf.core.rename.state_manager.

State management for the unified rename engine.

This module provides the RenameStateManager class that manages RenameState
instances and detects changes between updates.

Author: Michael Economou
Date: 2026-01-01
"""

from oncutf.core.rename.data_classes import RenameState


class RenameStateManager:
    """Manage a `RenameState` instance and detect changes between updates.

    The manager stores the prior state and sets boolean flags on the new
    state object when preview/validation/execution results change.
    """

    def __init__(self) -> None:
        """Initialize the state manager with a new empty state."""
        self.current_state = RenameState()
        self._previous_state: RenameState | None = None

    def update_state(self, new_state: RenameState) -> None:
        """Replace the current state with `new_state` and compute change flags."""
        self._previous_state = self.current_state
        self.current_state = new_state

        # Detect changes
        self._detect_state_changes()

    def _detect_state_changes(self) -> None:
        """Detect changes between previous and current state."""
        if not self._previous_state:
            return

        # Check preview changes
        if self._previous_state.preview_result != self.current_state.preview_result:
            self.current_state.preview_changed = True

        # Check validation changes
        if self._previous_state.validation_result != self.current_state.validation_result:
            self.current_state.validation_changed = True

        # Check execution changes
        if self._previous_state.execution_result != self.current_state.execution_result:
            self.current_state.execution_changed = True

    def get_state(self) -> RenameState:
        """Get current state."""
        return self.current_state

    def reset_changes(self) -> None:
        """Reset change flags."""
        self.current_state.preview_changed = False
        self.current_state.validation_changed = False
        self.current_state.execution_changed = False
