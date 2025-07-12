"""
Module: rename_history_manager.py

Author: Michael Economou
Date: 2025-06-10

rename_history_manager.py
Rename history management system for undo/redo functionality.
Tracks rename operations and provides rollback capabilities.
Features:
- Persistent storage of rename operations
- Undo/redo functionality for batch renames
- Operation grouping and rollback validation
- Integration with existing rename workflow
"""

import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from core.database_manager import get_database_manager
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class RenameOperation:
    """
    Represents a single rename operation within a batch.
    """

    def __init__(self, old_path: str, new_path: str, old_filename: str, new_filename: str):
        self.old_path = old_path
        self.new_path = new_path
        self.old_filename = old_filename
        self.new_filename = new_filename

    def __repr__(self):
        return f"<RenameOperation({self.old_filename} -> {self.new_filename})>"


class RenameBatch:
    """
    Represents a batch of rename operations that can be undone as a unit.
    """

    def __init__(self, operation_id: str, operations: List[RenameOperation],
                 modules_data: Optional[List[Dict]] = None,
                 post_transform_data: Optional[Dict] = None,
                 timestamp: Optional[str] = None):
        self.operation_id = operation_id
        self.operations = operations
        self.modules_data = modules_data
        self.post_transform_data = post_transform_data
        self.timestamp = timestamp or datetime.now().isoformat()

    @property
    def file_count(self) -> int:
        return len(self.operations)

    def __repr__(self):
        return f"<RenameBatch(id={self.operation_id[:8]}..., files={self.file_count})>"


class RenameHistoryManager:
    """
    Manages rename history for undo/redo functionality.

    Provides persistent storage of rename operations and rollback capabilities.
    """

    def __init__(self):
        """Initialize rename history manager with database backend."""
        self._db_manager = get_database_manager()
        logger.info("[RenameHistoryManager] Initialized with database backend")

    def record_rename_batch(self, renames: List[Tuple[str, str]],
                           modules_data: Optional[List[Dict]] = None,
                           post_transform_data: Optional[Dict] = None) -> str:
        """
        Record a batch rename operation for future undo.

        Args:
            renames: List of (old_path, new_path) tuples
            modules_data: Modules configuration used for this rename
            post_transform_data: Post-transform settings used

        Returns:
            Operation ID for the recorded batch
        """
        operation_id = str(uuid.uuid4())

        try:
            # Record in database
            success = self._db_manager.record_rename_operation(
                operation_id=operation_id,
                renames=renames,
                modules_data=modules_data,
                post_transform_data=post_transform_data
            )

            if success:
                logger.info(f"[RenameHistoryManager] Recorded rename batch {operation_id[:8]}... with {len(renames)} files")
                return operation_id
            else:
                logger.error("[RenameHistoryManager] Failed to record rename batch")
                return ""

        except Exception as e:
            logger.error(f"[RenameHistoryManager] Error recording rename batch: {e}")
            return ""

    def get_recent_operations(self, limit: int = 20) -> List[Dict]:
        """
        Get recent rename operations for undo menu.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of operation summaries
        """
        try:
            operations = self._db_manager.get_rename_history(limit)

            # Format for UI display
            formatted_operations = []
            for op in operations:
                formatted_operations.append({
                    'operation_id': op['operation_id'],
                    'timestamp': op['operation_time'],
                    'file_count': op['file_count'],
                    'operation_type': op['operation_type'],
                    'display_text': f"Renamed {op['file_count']} file(s) - {op['operation_time'][:19].replace('T', ' ')}"
                })

            return formatted_operations

        except Exception as e:
            logger.error(f"[RenameHistoryManager] Error retrieving recent operations: {e}")
            return []

    def get_operation_details(self, operation_id: str) -> Optional[RenameBatch]:
        """
        Get detailed information about a specific operation.

        Args:
            operation_id: ID of the operation

        Returns:
            RenameBatch object or None if not found
        """
        try:
            details = self._db_manager.get_operation_details(operation_id)
            if not details:
                return None

            # Convert to RenameOperation objects
            operations = []
            modules_data = None
            post_transform_data = None
            timestamp = None

            for detail in details:
                operations.append(RenameOperation(
                    old_path=detail['old_path'],
                    new_path=detail['new_path'],
                    old_filename=detail['old_filename'],
                    new_filename=detail['new_filename']
                ))

                # Get metadata from first record (same for all in batch)
                if modules_data is None:
                    modules_data = detail['modules_data']
                    post_transform_data = detail['post_transform_data']
                    timestamp = detail['created_at']

            return RenameBatch(
                operation_id=operation_id,
                operations=operations,
                modules_data=modules_data,
                post_transform_data=post_transform_data,
                timestamp=timestamp
            )

        except Exception as e:
            logger.error(f"[RenameHistoryManager] Error retrieving operation details: {e}")
            return None

    def can_undo_operation(self, operation_id: str) -> Tuple[bool, str]:
        """
        Check if an operation can be undone.

        Args:
            operation_id: ID of the operation to check

        Returns:
            Tuple of (can_undo, reason_if_not)
        """
        try:
            batch = self.get_operation_details(operation_id)
            if not batch:
                return False, "Operation not found"

            # Check if all current files exist and match expected names
            missing_files = []
            wrong_names = []

            for operation in batch.operations:
                current_path = operation.new_path

                if not os.path.exists(current_path):
                    missing_files.append(operation.new_filename)
                else:
                    current_filename = os.path.basename(current_path)
                    if current_filename != operation.new_filename:
                        wrong_names.append(f"{current_filename} (expected {operation.new_filename})")

            if missing_files:
                return False, f"Missing files: {', '.join(missing_files[:3])}{'...' if len(missing_files) > 3 else ''}"

            if wrong_names:
                return False, f"Files have been renamed again: {', '.join(wrong_names[:2])}{'...' if len(wrong_names) > 2 else ''}"

            return True, ""

        except Exception as e:
            logger.error(f"[RenameHistoryManager] Error checking undo capability: {e}")
            return False, f"Error checking operation: {str(e)}"

    def undo_operation(self, operation_id: str) -> Tuple[bool, str, int]:
        """
        Undo a rename operation by reverting all files to their original names.

        Args:
            operation_id: ID of the operation to undo

        Returns:
            Tuple of (success, message, files_processed)
        """
        try:
            # Check if operation can be undone
            can_undo, reason = self.can_undo_operation(operation_id)
            if not can_undo:
                return False, f"Cannot undo operation: {reason}", 0

            batch = self.get_operation_details(operation_id)
            if not batch:
                return False, "Operation not found", 0

            # Perform the undo operation
            successful_reverts = []
            failed_reverts = []

            for operation in batch.operations:
                try:
                    current_path = operation.new_path
                    target_path = operation.old_path

                    # Perform the rename (revert)
                    # Use safe case rename for case-only changes
                    from utils.rename_logic import safe_case_rename, is_case_only_change

                    current_name = os.path.basename(current_path)
                    target_name = os.path.basename(target_path)

                    if is_case_only_change(current_name, target_name):
                        if not safe_case_rename(current_path, target_path):
                            raise Exception(f"Case-only rename failed: {current_name} -> {target_name}")
                    else:
                        os.rename(current_path, target_path)
                    successful_reverts.append(operation)

                    logger.debug(f"[RenameHistoryManager] Reverted: {operation.new_filename} -> {operation.old_filename}")

                except OSError as e:
                    failed_reverts.append((operation, str(e)))
                    logger.error(f"[RenameHistoryManager] Failed to revert {operation.new_filename}: {e}")

            # Record the undo operation
            if successful_reverts:
                undo_renames = [(op.new_path, op.old_path) for op in successful_reverts]
                undo_operation_id = str(uuid.uuid4())

                self._db_manager.record_rename_operation(
                    operation_id=undo_operation_id,
                    renames=undo_renames,
                    modules_data=None,  # Undo operations don't have module data
                    post_transform_data=None
                )

            # Prepare result message
            total_files = len(batch.operations)
            success_count = len(successful_reverts)

            if failed_reverts:
                failed_names = [op.new_filename for op, _ in failed_reverts[:3]]
                message = f"Undid {success_count}/{total_files} files. Failed: {', '.join(failed_names)}{'...' if len(failed_reverts) > 3 else ''}"
                return success_count > 0, message, success_count
            else:
                message = f"Successfully undid rename operation for {success_count} files"
                return True, message, success_count

        except Exception as e:
            logger.error(f"[RenameHistoryManager] Error during undo operation: {e}")
            return False, f"Undo failed: {str(e)}", 0

    def cleanup_old_history(self, days_to_keep: int = 30) -> int:
        """
        Clean up old rename history records.

        Args:
            days_to_keep: Number of days of history to keep

        Returns:
            Number of records cleaned up
        """
        try:
            # This would require additional database methods
            # For now, we rely on the general cleanup
            return self._db_manager.cleanup_orphaned_records()

        except Exception as e:
            logger.error(f"[RenameHistoryManager] Error during history cleanup: {e}")
            return 0

    def get_history_stats(self) -> Dict:
        """
        Get statistics about rename history.

        Returns:
            Dictionary with history statistics
        """
        try:
            db_stats = self._db_manager.get_database_stats()
            recent_operations = self.get_recent_operations(100)  # Get more for stats

            return {
                'total_operations': db_stats.get('rename_history', 0),
                'recent_operations': len(recent_operations),
                'database_stats': db_stats
            }

        except Exception as e:
            logger.error(f"[RenameHistoryManager] Error getting history stats: {e}")
            return {}


# Global instance for easy access
_rename_history_manager: Optional[RenameHistoryManager] = None


def get_rename_history_manager() -> RenameHistoryManager:
    """Get global RenameHistoryManager instance."""
    global _rename_history_manager
    if _rename_history_manager is None:
        _rename_history_manager = RenameHistoryManager()
    return _rename_history_manager
