"""Module: conflict_resolver.py.

Author: Michael Economou
Date: 2025-05-01

Conflict Resolver - Simple but reliable conflict resolution for rename operations.
"""

import os
import shutil
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@dataclass
class ConflictOperation:
    """Single conflict operation."""

    old_path: str
    new_path: str
    operation_type: str  # "rename", "move", "copy"
    timestamp: float
    success: bool
    error_message: str = ""
    backup_path: str = ""


@dataclass
class ConflictResolution:
    """Conflict resolution result."""

    original_path: str
    resolved_path: str
    resolution_type: str  # "timestamp", "number", "skip", "overwrite"
    backup_created: bool
    success: bool
    error_message: str = ""


class UndoStack:
    """Simple undo stack for operations."""

    def __init__(self, max_size: int = 100):
        """Initialize undo stack with maximum size."""
        self.stack: deque[ConflictOperation] = deque(maxlen=max_size)
        self.redo_stack: deque[ConflictOperation] = deque(maxlen=max_size)

    def push(self, operation: ConflictOperation) -> None:
        """Push operation to undo stack."""
        self.stack.append(operation)
        # Clear redo stack when new operation is pushed
        self.redo_stack.clear()

    def pop(self) -> ConflictOperation | None:
        """Pop operation from undo stack."""
        if self.stack:
            operation = self.stack.pop()
            self.redo_stack.append(operation)
            return operation
        return None

    def can_undo(self) -> bool:
        """Check if undo is possible."""
        return len(self.stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is possible."""
        return len(self.redo_stack) > 0

    def clear(self) -> None:
        """Clear both stacks."""
        self.stack.clear()
        self.redo_stack.clear()


class ConflictResolver:
    """Simple but reliable conflict resolver."""

    def __init__(self, backup_dir: str | None = None):
        """Initialize conflict resolver with backup directory and strategies."""
        if backup_dir is None:
            backup_dir = os.path.join(os.path.expanduser("~"), ".oncutf", "backups")

        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)

        self.undo_stack = UndoStack()
        self.conflict_log: list[Any] = []
        self.resolution_strategies = {
            "timestamp": self._resolve_with_timestamp,
            "number": self._resolve_with_number,
            "skip": self._resolve_skip,
            "overwrite": self._resolve_overwrite,
        }

    def resolve_conflict(
        self, old_path: str, new_path: str, strategy: str = "timestamp"
    ) -> ConflictResolution:
        """Resolve file conflict with specified strategy."""
        if not os.path.exists(old_path):
            return ConflictResolution(
                original_path=old_path,
                resolved_path=new_path,
                resolution_type="error",
                backup_created=False,
                success=False,
                error_message="Source file does not exist",
            )

        # Check if conflict exists
        if not os.path.exists(new_path):
            # No conflict, proceed normally
            return self._execute_operation(old_path, new_path, "rename")

        # Conflict exists, resolve using strategy
        if strategy in self.resolution_strategies:
            resolved_path = self.resolution_strategies[strategy](new_path)
        else:
            # Default to timestamp strategy
            resolved_path = self._resolve_with_timestamp(new_path)

        # Execute operation with resolved path
        return self._execute_operation(old_path, resolved_path, "rename")

    def _resolve_with_timestamp(self, path: str) -> str:
        """Resolve conflict with timestamp suffix."""
        base, ext = os.path.splitext(path)
        timestamp = int(time.time())
        return f"{base}_{timestamp}{ext}"

    def _resolve_with_number(self, path: str) -> str:
        """Resolve conflict with number suffix."""
        base, ext = os.path.splitext(path)
        counter = 1

        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1

        return f"{base}_{counter}{ext}"

    def _resolve_skip(self, path: str) -> str:
        """Resolve conflict with skip (return original path)."""
        return path  # This will cause the operation to be skipped

    def _resolve_overwrite(self, path: str) -> str:
        """Resolve conflict with overwrite."""
        # Create backup before overwriting
        if os.path.exists(path):
            backup_path = self._create_backup(path)
            logger.debug("[ConflictResolver] Created backup: %s", backup_path)

        return path

    def _create_backup(self, path: str) -> str:
        """Create backup of file."""
        timestamp = int(time.time())
        filename = os.path.basename(path)
        backup_filename = f"{timestamp}_{filename}"
        backup_path = os.path.join(self.backup_dir, backup_filename)

        try:
            shutil.copy2(path, backup_path)
            return backup_path
        except Exception as e:
            logger.error("[ConflictResolver] Failed to create backup: %s", e)
            return ""

    def _execute_operation(
        self, old_path: str, new_path: str, operation_type: str
    ) -> ConflictResolution:
        """Execute file operation."""
        start_time = time.time()

        try:
            # Create operation record
            operation = ConflictOperation(
                old_path=old_path,
                new_path=new_path,
                operation_type=operation_type,
                timestamp=start_time,
                success=False,
            )

            # Execute operation
            if operation_type == "rename":
                os.rename(old_path, new_path)
            elif operation_type == "copy":
                shutil.copy2(old_path, new_path)
            elif operation_type == "move":
                shutil.move(old_path, new_path)

            # Mark as successful
            operation.success = True

            # Add to undo stack
            self.undo_stack.push(operation)

            return ConflictResolution(
                original_path=old_path,
                resolved_path=new_path,
                resolution_type="success",
                backup_created=False,
                success=True,
            )

        except Exception as e:
            error_msg = str(e)
            operation.error_message = error_msg

            logger.error("[ConflictResolver] Operation failed: %s", error_msg)

            return ConflictResolution(
                original_path=old_path,
                resolved_path=new_path,
                resolution_type="error",
                backup_created=False,
                success=False,
                error_message=error_msg,
            )

    def undo_last_operation(self) -> ConflictResolution | None:
        """Undo last operation."""
        if not self.undo_stack.can_undo():
            return None

        operation = self.undo_stack.pop()

        try:
            # Reverse the operation
            if operation and operation.operation_type == "rename":
                if os.path.exists(operation.new_path):
                    os.rename(operation.new_path, operation.old_path)
                elif operation.backup_path and os.path.exists(operation.backup_path):
                    # Restore from backup
                    shutil.copy2(operation.backup_path, operation.old_path)

            if (
                operation
            ):  # Added check for operation before accessing its attributes for the return value
                return ConflictResolution(
                    original_path=operation.new_path,
                    resolved_path=operation.old_path,
                    resolution_type="undo",
                    backup_created=False,
                    success=True,
                )
            else:
                # Should not happen if can_undo() was true, but for safety
                return ConflictResolution(
                    original_path="",
                    resolved_path="",
                    resolution_type="undo_error",
                    backup_created=False,
                    success=False,
                    error_message="No operation to undo or operation was None",
                )

        except Exception as e:
            logger.error("[ConflictResolver] Undo failed: %s", e)
            return ConflictResolution(
                original_path=operation.new_path if operation else "",
                resolved_path=operation.old_path if operation else "",
                resolution_type="undo_error",
                backup_created=False,
                success=False,
                error_message=str(e),
            )

    def batch_resolve_conflicts(
        self, operations: list[tuple[str, str]], strategy: str = "timestamp"
    ) -> list[ConflictResolution]:
        """Resolve multiple conflicts in batch."""
        results = []

        for old_path, new_path in operations:
            result = self.resolve_conflict(old_path, new_path, strategy)
            results.append(result)

            # Log conflict resolution
            if result.success:
                logger.debug(
                    "[ConflictResolver] Resolved: %s -> %s",
                    old_path,
                    result.resolved_path,
                )
            else:
                logger.error(
                    "[ConflictResolver] Failed: %s -> %s",
                    old_path,
                    result.error_message,
                )

        return results

    def get_stats(self) -> dict[str, Any]:
        """Get conflict resolution statistics."""
        total_operations = len(self.undo_stack.stack) + len(self.undo_stack.redo_stack)
        successful_operations = sum(1 for op in self.undo_stack.stack if op.success)

        return {
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "success_rate": (
                (successful_operations / total_operations * 100) if total_operations > 0 else 100
            ),
            "can_undo": self.undo_stack.can_undo(),
            "can_redo": self.undo_stack.can_redo(),
            "backup_dir": self.backup_dir,
        }

    def clear_history(self) -> None:
        """Clear operation history."""
        self.undo_stack.clear()
        self.conflict_log.clear()
        logger.debug("[ConflictResolver] History cleared")
