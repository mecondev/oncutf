"""Module: metadata_command_manager.py.

Author: Michael Economou
Date: 2025-07-08

Command manager for metadata operations with undo/redo functionality.
Manages command execution, undo/redo stacks, and command grouping.

Features:
- Command execution with undo/redo support
- Command history management
- Keyboard shortcuts integration
- Batch command grouping
- Signal-based UI updates
"""

from datetime import datetime, timedelta
from typing import Any, cast

from PyQt5.QtCore import QObject, pyqtSignal

from oncutf.config import UNDO_REDO_SETTINGS
from oncutf.core.metadata.commands import BatchMetadataCommand, MetadataCommand
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataCommandManager(QObject):
    """Manages metadata commands with undo/redo functionality.

    Provides command execution, undo/redo operations, and maintains
    command history for metadata operations.
    """

    # Signals for UI updates
    can_undo_changed = pyqtSignal(bool)
    can_redo_changed = pyqtSignal(bool)
    command_executed = pyqtSignal(str)  # description
    command_undone = pyqtSignal(str)  # description
    command_redone = pyqtSignal(str)  # description
    history_changed = pyqtSignal()  # general history change

    def __init__(self, max_history: int | None = None):
        """Initialize metadata command manager.

        Args:
            max_history: Maximum number of commands to keep in history

        """
        super().__init__()
        config_max_history: Any = UNDO_REDO_SETTINGS["MAX_UNDO_STEPS"]
        config_grouping_timeout: Any = UNDO_REDO_SETTINGS["COMMAND_GROUPING_TIMEOUT"]

        self.max_history = (
            int(max_history) if max_history is not None else int(cast("int", config_max_history))
        )
        self.grouping_timeout = float(cast("float", config_grouping_timeout))

        # Command stacks
        self._undo_stack: list[MetadataCommand] = []
        self._redo_stack: list[MetadataCommand] = []

        # Command grouping
        self._pending_commands: list[MetadataCommand] = []
        self._last_command_time: datetime | None = None

        logger.info("[MetadataCommandManager] Initialized with max_history=%d", self.max_history)

    def execute_command(self, command: MetadataCommand, group_with_previous: bool = False) -> bool:
        """Execute a metadata command and add it to the undo stack.

        Args:
            command: Command to execute
            group_with_previous: Whether to group with previous commands

        Returns:
            True if successful, False otherwise

        """
        try:
            # Execute the command
            if not command.execute():
                logger.warning(
                    "[MetadataCommandManager] Failed to execute command: %s",
                    command.get_description(),
                )
                return False

            # Handle command grouping
            if group_with_previous and self._can_group_with_previous(command):
                self._add_to_pending_group(command)
            else:
                # Finalize any pending group first
                self._finalize_pending_group()

                # Add command to undo stack
                self._add_to_undo_stack(command)

            # Update last command time
            self._last_command_time = datetime.now()

            # Emit signals
            self.command_executed.emit(command.get_description())
            self._emit_state_signals()

            logger.debug("[MetadataCommandManager] Executed: %s", command.get_description())
        except Exception:
            logger.exception("[MetadataCommandManager] Error executing command")
            return False
        else:
            return True

    def undo(self) -> bool:
        """Undo the last command.

        Returns:
            True if successful, False otherwise

        """
        try:
            # Finalize any pending group first
            self._finalize_pending_group()

            if not self._undo_stack:
                logger.debug("[MetadataCommandManager] No commands to undo")
                return False

            command = self._undo_stack.pop()

            if command.undo():
                # Move to redo stack
                self._redo_stack.append(command)

                # Emit signals
                self.command_undone.emit(command.get_description())
                self._emit_state_signals()

                logger.debug("[MetadataCommandManager] Undone: %s", command.get_description())
                return True
            # If undo failed, put command back
            self._undo_stack.append(command)
            logger.warning(
                "[MetadataCommandManager] Failed to undo: %s",
                command.get_description(),
            )
        except Exception:
            logger.exception("[MetadataCommandManager] Error undoing command")
            return False
        else:
            return False

    def redo(self) -> bool:
        """Redo the last undone command.

        Returns:
            True if successful, False otherwise

        """
        try:
            if not self._redo_stack:
                logger.debug("[MetadataCommandManager] No commands to redo")
                return False

            command = self._redo_stack.pop()

            if command.execute():
                # Move back to undo stack
                self._undo_stack.append(command)

                # Emit signals
                self.command_redone.emit(command.get_description())
                self._emit_state_signals()

                logger.debug("[MetadataCommandManager] Redone: %s", command.get_description())
                return True
            # If redo failed, put command back
            self._redo_stack.append(command)
            logger.warning(
                "[MetadataCommandManager] Failed to redo: %s",
                command.get_description(),
            )
        except Exception:
            logger.exception("[MetadataCommandManager] Error redoing command")
            return False
        else:
            return False

    def can_undo(self) -> bool:
        """Check if undo is available."""
        self._finalize_pending_group()
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0

    def get_undo_description(self) -> str | None:
        """Get description of the command that would be undone."""
        self._finalize_pending_group()
        if self._undo_stack:
            return f"Undo: {self._undo_stack[-1].get_description()}"
        return None

    def get_redo_description(self) -> str | None:
        """Get description of the command that would be redone."""
        if self._redo_stack:
            return f"Redo: {self._redo_stack[-1].get_description()}"
        return None

    def get_command_history(self, limit: int | None = None) -> list[dict[str, object]]:
        """Get command history for UI display.

        Args:
            limit: Maximum number of commands to return

        Returns:
            List of command information dictionaries

        """
        self._finalize_pending_group()

        history = []

        # Add undo stack (most recent first)
        for i, command in enumerate(reversed(self._undo_stack)):
            history.append(
                {
                    "command_id": command.command_id,
                    "description": command.get_description(),
                    "timestamp": command.timestamp,
                    "file_path": command.file_path,
                    "command_type": command.get_command_type(),
                    "can_undo": True,
                    "can_redo": False,
                    "stack_position": i,
                }
            )

        # Add redo stack
        for i, command in enumerate(self._redo_stack):
            history.append(
                {
                    "command_id": command.command_id,
                    "description": command.get_description(),
                    "timestamp": command.timestamp,
                    "file_path": command.file_path,
                    "command_type": command.get_command_type(),
                    "can_undo": False,
                    "can_redo": True,
                    "stack_position": i,
                }
            )

        # Apply limit if specified
        if limit:
            history = history[:limit]

        return history

    def clear_history(self) -> None:
        """Clear all command history."""
        self._pending_commands.clear()
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._last_command_time = None

        self._emit_state_signals()
        logger.info("[MetadataCommandManager] Command history cleared")

    def _can_group_with_previous(self, command: MetadataCommand) -> bool:
        """Check if command can be grouped with previous commands.

        Args:
            command: Command to check

        Returns:
            True if can be grouped, False otherwise

        """
        if not self._last_command_time:
            return False

        # Check time window
        time_diff = datetime.now() - self._last_command_time
        if time_diff > timedelta(milliseconds=float(self.grouping_timeout)):
            return False

        # Check if there are pending commands or recent commands
        if self._pending_commands:
            # Check if same file and similar operation
            last_command = self._pending_commands[-1]
            return (
                command.file_path == last_command.file_path
                and command.get_command_type() == last_command.get_command_type()
            )

        if self._undo_stack:
            # Check if same file and similar operation
            last_command = self._undo_stack[-1]
            return (
                command.file_path == last_command.file_path
                and command.get_command_type() == last_command.get_command_type()
            )

        return False

    def _add_to_pending_group(self, command: MetadataCommand) -> None:
        """Add command to pending group."""
        self._pending_commands.append(command)
        logger.debug(
            "[MetadataCommandManager] Added to pending group: %s",
            command.get_description(),
        )

    def _finalize_pending_group(self) -> None:
        """Finalize any pending command group."""
        if not self._pending_commands:
            return

        if len(self._pending_commands) == 1:
            # Single command, add directly
            self._add_to_undo_stack(self._pending_commands[0])
        else:
            # Multiple commands, create batch
            batch_command = BatchMetadataCommand(
                self._pending_commands,
                f"Batch edit: {len(self._pending_commands)} operations",
            )
            self._add_to_undo_stack(batch_command)

        self._pending_commands.clear()
        logger.debug("[MetadataCommandManager] Finalized pending command group")

    def _add_to_undo_stack(self, command: MetadataCommand) -> None:
        """Add command to undo stack."""
        self._undo_stack.append(command)

        # Clear redo stack (new command invalidates redo)
        self._redo_stack.clear()

        # Limit stack size
        if len(self._undo_stack) > int(self.max_history):
            self._undo_stack.pop(0)

        logger.debug(
            "[MetadataCommandManager] Added to undo stack: %s",
            command.get_description(),
        )

    def _emit_state_signals(self) -> None:
        """Emit signals for UI state updates."""
        self.can_undo_changed.emit(self.can_undo())
        self.can_redo_changed.emit(self.can_redo())
        self.history_changed.emit()


# Global instance
_metadata_command_manager: MetadataCommandManager | None = None


def get_metadata_command_manager() -> MetadataCommandManager:
    """Get or create the global metadata command manager."""
    global _metadata_command_manager
    if _metadata_command_manager is None:
        _metadata_command_manager = MetadataCommandManager()
    return _metadata_command_manager


def cleanup_metadata_command_manager() -> None:
    """Clean up the global metadata command manager."""
    global _metadata_command_manager
    if _metadata_command_manager:
        _metadata_command_manager.clear_history()
        _metadata_command_manager = None
