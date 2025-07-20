"""
Module: metadata_commands.py

Author: Michael Economou
Date: 2025-07-08

Command pattern implementation for metadata operations.
Provides undo/redo functionality for metadata edits, resets, and saves.

Features:
- Command pattern for metadata operations
- Undo/redo support for all metadata changes
- Batch command grouping
- Integration with existing metadata system
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import COMMAND_TYPES
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataCommand(ABC):
    """
    Abstract base class for all metadata commands.

    Implements the Command pattern for metadata operations,
    providing execute, undo, and redo functionality.
    """

    def __init__(self, file_path: str, timestamp: Optional[datetime] = None):
        """
        Initialize metadata command.

        Args:
            file_path: Path to the file being modified
            timestamp: When the command was created
        """
        self.file_path = file_path
        self.timestamp = timestamp or datetime.now()
        self.command_id = f"{self.timestamp.isoformat()}_{id(self)}"
        self.executed = False
        self.undone = False

    @abstractmethod
    def execute(self) -> bool:
        """
        Execute the command.

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    def undo(self) -> bool:
        """
        Undo the command.

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    def get_description(self) -> str:
        """
        Get human-readable description of the command.

        Returns:
            Description string for UI display
        """

    @abstractmethod
    def get_command_type(self) -> str:
        """
        Get the type of command.

        Returns:
            Command type string
        """

    def can_execute(self) -> bool:
        """Check if command can be executed."""
        return not self.executed

    def can_undo(self) -> bool:
        """Check if command can be undone."""
        return self.executed and not self.undone

    def can_redo(self) -> bool:
        """Check if command can be redone."""
        return self.executed and self.undone

    def get_file_basename(self) -> str:
        """Get the basename of the file for display."""
        import os

        return os.path.basename(self.file_path)


class EditMetadataFieldCommand(MetadataCommand):
    """
    Command for editing a single metadata field.
    """

    def __init__(
        self,
        file_path: str,
        field_path: str,
        new_value: Any,
        old_value: Any,
        metadata_tree_view=None,
    ):
        """
        Initialize edit metadata field command.

        Args:
            file_path: Path to the file
            field_path: Path to the metadata field (e.g., "EXIF/Rotation")
            new_value: New value to set
            old_value: Previous value (for undo)
            metadata_tree_view: Reference to the metadata tree view
        """
        super().__init__(file_path)
        self.field_path = field_path
        self.new_value = new_value
        self.old_value = old_value
        self.metadata_tree_view = metadata_tree_view

    def execute(self) -> bool:
        """Execute the metadata field edit."""
        try:
            if self.executed:
                return True

            # Update metadata in cache and UI
            success = self._update_metadata_field(self.field_path, self.new_value)

            if success:
                self.executed = True
                self.undone = False
                logger.debug(
                    f"[EditMetadataFieldCommand] Executed: {self.field_path} = {self.new_value}"
                )
                return True
            else:
                logger.warning(f"[EditMetadataFieldCommand] Failed to execute: {self.field_path}")
                return False

        except Exception as e:
            logger.error(f"[EditMetadataFieldCommand] Error executing: {e}")
            return False

    def undo(self) -> bool:
        """Undo the metadata field edit."""
        try:
            if not self.can_undo():
                return False

            # Restore old value
            success = self._update_metadata_field(self.field_path, self.old_value)

            if success:
                self.undone = True
                logger.debug(
                    f"[EditMetadataFieldCommand] Undone: {self.field_path} = {self.old_value}"
                )
                return True
            else:
                logger.warning(f"[EditMetadataFieldCommand] Failed to undo: {self.field_path}")
                return False

        except Exception as e:
            logger.error(f"[EditMetadataFieldCommand] Error undoing: {e}")
            return False

    def _update_metadata_field(self, field_path: str, value: Any) -> bool:
        """
        Update metadata field in cache and UI.

        Args:
            field_path: Path to the metadata field
            value: Value to set

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use the passed metadata tree view reference
            if not self.metadata_tree_view:
                logger.warning(
                    "[EditMetadataFieldCommand] No metadata tree view reference available"
                )
                return False

            # Update metadata in cache
            self.metadata_tree_view._update_metadata_in_cache(field_path, str(value))

            # Update tree view display
            self.metadata_tree_view._update_tree_item_value(field_path, str(value))

            # Mark as modified
            self.metadata_tree_view.mark_as_modified(field_path)

            # Update file icon status
            self.metadata_tree_view._update_file_icon_status()

            return True

        except Exception as e:
            logger.error(f"[EditMetadataFieldCommand] Error updating metadata field: {e}")
            return False

    def get_description(self) -> str:
        """Get description of the edit command."""
        return f"Edit {self.field_path}: {self.old_value} → {self.new_value}"

    def get_command_type(self) -> str:
        """Get command type."""
        return COMMAND_TYPES["METADATA_EDIT"]


class ResetMetadataFieldCommand(MetadataCommand):
    """
    Command for resetting a metadata field to its original value.
    """

    def __init__(
        self,
        file_path: str,
        field_path: str,
        current_value: Any,
        original_value: Any,
        metadata_tree_view=None,
    ):
        """
        Initialize reset metadata field command.

        Args:
            file_path: Path to the file
            field_path: Path to the metadata field
            current_value: Current modified value
            original_value: Original value from file
            metadata_tree_view: Reference to the metadata tree view
        """
        super().__init__(file_path)
        self.field_path = field_path
        self.current_value = current_value
        self.original_value = original_value
        self.metadata_tree_view = metadata_tree_view

    def execute(self) -> bool:
        """Execute the metadata field reset."""
        try:
            if self.executed:
                return True

            # Reset to original value
            success = self._reset_metadata_field(self.field_path, self.original_value)

            if success:
                self.executed = True
                self.undone = False
                logger.debug(
                    f"[ResetMetadataFieldCommand] Executed: {self.field_path} reset to {self.original_value}"
                )
                return True
            else:
                logger.warning(f"[ResetMetadataFieldCommand] Failed to execute: {self.field_path}")
                return False

        except Exception as e:
            logger.error(f"[ResetMetadataFieldCommand] Error executing: {e}")
            return False

    def undo(self) -> bool:
        """Undo the metadata field reset."""
        try:
            if not self.can_undo():
                return False

            # Restore current value
            success = self._reset_metadata_field(self.field_path, self.current_value)

            if success:
                self.undone = True
                logger.debug(
                    f"[ResetMetadataFieldCommand] Undone: {self.field_path} = {self.current_value}"
                )
                return True
            else:
                logger.warning(f"[ResetMetadataFieldCommand] Failed to undo: {self.field_path}")
                return False

        except Exception as e:
            logger.error(f"[ResetMetadataFieldCommand] Error undoing: {e}")
            return False

    def _reset_metadata_field(self, field_path: str, value: Any) -> bool:
        """
        Reset metadata field in cache and UI.

        Args:
            field_path: Path to the metadata field
            value: Value to set

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use the passed metadata tree view reference
            if not self.metadata_tree_view:
                logger.warning(
                    "[ResetMetadataFieldCommand] No metadata tree view reference available"
                )
                return False

            # Reset metadata in cache
            self.metadata_tree_view._reset_metadata_in_cache(field_path)

            # Update tree view display
            self.metadata_tree_view._update_tree_item_value(field_path, str(value))

            # Clear modification mark if resetting to original
            if value == self.original_value:
                self.metadata_tree_view.modified_items.discard(field_path)
            else:
                self.metadata_tree_view.mark_as_modified(field_path)

            # Update file icon status
            self.metadata_tree_view._update_file_icon_status()

            return True

        except Exception as e:
            logger.error(f"[ResetMetadataFieldCommand] Error resetting metadata field: {e}")
            return False

    def get_description(self) -> str:
        """Get description of the reset command."""
        return f"Reset {self.field_path}: {self.current_value} → {self.original_value}"

    def get_command_type(self) -> str:
        """Get command type."""
        return COMMAND_TYPES["METADATA_RESET"]


class SaveMetadataCommand(MetadataCommand):
    """
    Command for saving metadata changes to files.
    """

    def __init__(self, file_paths: List[str], saved_metadata: Dict[str, Dict[str, Any]]):
        """
        Initialize save metadata command.

        Args:
            file_paths: List of file paths that were saved
            saved_metadata: Dictionary of file_path -> {field_path: value} that was saved
        """
        # Use first file path as primary file for command
        super().__init__(file_paths[0] if file_paths else "")
        self.file_paths = file_paths
        self.saved_metadata = saved_metadata

    def execute(self) -> bool:
        """Execute the metadata save."""
        try:
            if self.executed:
                return True

            # Save metadata is already done when this command is created
            # This is just for tracking purposes
            self.executed = True
            self.undone = False
            logger.debug(f"[SaveMetadataCommand] Executed: saved {len(self.file_paths)} files")
            return True

        except Exception as e:
            logger.error(f"[SaveMetadataCommand] Error executing: {e}")
            return False

    def undo(self) -> bool:
        """Undo the metadata save."""
        try:
            if not self.can_undo():
                return False

            # Note: Undoing a save operation is complex because it involves
            # reverting file changes. For now, we'll just mark as undone
            # but not actually revert the files.
            logger.warning(
                "[SaveMetadataCommand] Save undo not implemented - files remain modified"
            )

            self.undone = True
            return True

        except Exception as e:
            logger.error(f"[SaveMetadataCommand] Error undoing: {e}")
            return False

    def get_description(self) -> str:
        """Get description of the save command."""
        count = len(self.file_paths)
        if count == 1:
            return f"Save metadata: {self.get_file_basename()}"
        else:
            return f"Save metadata: {count} files"

    def get_command_type(self) -> str:
        """Get command type."""
        return COMMAND_TYPES["METADATA_SAVE"]


class BatchMetadataCommand(MetadataCommand):
    """
    Command for grouping multiple metadata commands together.
    """

    def __init__(self, commands: List[MetadataCommand], description: str = ""):
        """
        Initialize batch metadata command.

        Args:
            commands: List of commands to group together
            description: Custom description for the batch
        """
        # Use first command's file path as primary
        file_path = commands[0].file_path if commands else ""
        super().__init__(file_path)
        self.commands = commands
        self.batch_description = description

    def execute(self) -> bool:
        """Execute all commands in the batch."""
        try:
            if self.executed:
                return True

            success_count = 0
            for command in self.commands:
                if command.execute():
                    success_count += 1
                else:
                    logger.warning(
                        f"[BatchMetadataCommand] Failed to execute: {command.get_description()}"
                    )

            if success_count > 0:
                self.executed = True
                self.undone = False
                logger.debug(
                    f"[BatchMetadataCommand] Executed: {success_count}/{len(self.commands)} commands"
                )
                return True
            else:
                logger.warning("[BatchMetadataCommand] No commands executed successfully")
                return False

        except Exception as e:
            logger.error(f"[BatchMetadataCommand] Error executing batch: {e}")
            return False

    def undo(self) -> bool:
        """Undo all commands in the batch (in reverse order)."""
        try:
            if not self.can_undo():
                return False

            success_count = 0
            # Undo in reverse order
            for command in reversed(self.commands):
                if command.undo():
                    success_count += 1
                else:
                    logger.warning(
                        f"[BatchMetadataCommand] Failed to undo: {command.get_description()}"
                    )

            if success_count > 0:
                self.undone = True
                logger.debug(
                    f"[BatchMetadataCommand] Undone: {success_count}/{len(self.commands)} commands"
                )
                return True
            else:
                logger.warning("[BatchMetadataCommand] No commands undone successfully")
                return False

        except Exception as e:
            logger.error(f"[BatchMetadataCommand] Error undoing batch: {e}")
            return False

    def get_description(self) -> str:
        """Get description of the batch command."""
        if self.batch_description:
            return self.batch_description

        count = len(self.commands)
        if count == 1:
            return self.commands[0].get_description()
        else:
            return f"Batch operation: {count} commands"

    def get_command_type(self) -> str:
        """Get command type."""
        return COMMAND_TYPES["BATCH_OPERATION"]
