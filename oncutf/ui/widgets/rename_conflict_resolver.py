"""
Module: rename_conflict_resolver.py

Author: Michael Economou
Date: 2025-06-15

This module provides a conflict resolution system for file rename operations.
It handles cases where target files already exist and provides strategies
for resolving conflicts without blocking the main application thread.

Classes:
    RenameConflictResolver: Main class for handling rename conflicts
    ConflictResolutionStrategy: Enum for different resolution strategies
"""

import logging
from collections.abc import Callable
from enum import Enum
from pathlib import Path

from oncutf.core.pyqt_imports import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving file rename conflicts."""

    SKIP = "skip"
    OVERWRITE = "overwrite"
    RENAME_WITH_SUFFIX = "rename_with_suffix"
    ASK_USER = "ask_user"


class RenameConflictResolver(QObject):
    """
    Handles file rename conflicts without blocking the main application.

    This class provides various strategies for resolving conflicts when
    a target file already exists during a rename operation.
    """

    # Signals
    conflict_resolved = pyqtSignal(str, str, str)  # original_path, target_path, resolution

    def __init__(self, parent: QObject | None = None):
        """
        Initialize the conflict resolver.

        Args:
            parent: Parent QObject for proper cleanup
        """
        super().__init__(parent)
        self.default_strategy = ConflictResolutionStrategy.SKIP
        self.resolution_callbacks: dict[str, Callable] = {}

    def set_default_strategy(self, strategy: ConflictResolutionStrategy) -> None:
        """
        Set the default strategy for conflict resolution.

        Args:
            strategy: The default strategy to use
        """
        self.default_strategy = strategy
        logger.debug("Default conflict resolution strategy set to: %s", strategy.value)

    def resolve_conflict(
        self,
        original_path: str,
        target_path: str,
        strategy: ConflictResolutionStrategy | None = None,
    ) -> str:
        """
        Resolve a file rename conflict using the specified strategy.

        Args:
            original_path: Path to the original file
            target_path: Path to the target file (that already exists)
            strategy: Strategy to use (defaults to default_strategy)

        Returns:
            The resolved target path or empty string if skipped
        """
        if strategy is None:
            strategy = self.default_strategy

        logger.debug(
            "Resolving conflict for %s -> %s using %s",
            original_path,
            target_path,
            strategy.value,
        )

        try:
            if strategy == ConflictResolutionStrategy.SKIP:
                return self._skip_conflict(original_path, target_path)
            elif strategy == ConflictResolutionStrategy.OVERWRITE:
                return self._overwrite_conflict(original_path, target_path)
            elif strategy == ConflictResolutionStrategy.RENAME_WITH_SUFFIX:
                return self._rename_with_suffix(original_path, target_path)
            elif strategy == ConflictResolutionStrategy.ASK_USER:
                return self._ask_user_for_resolution(original_path, target_path)
            else:
                logger.warning("Unknown conflict resolution strategy: %s", strategy)
                return self._skip_conflict(original_path, target_path)

        except Exception as e:
            logger.error("Error resolving conflict: %s", e)
            return self._skip_conflict(original_path, target_path)

    def _skip_conflict(self, original_path: str, target_path: str) -> str:
        """Skip the conflicting rename operation."""
        logger.info("Skipping rename due to conflict: %s -> %s", original_path, target_path)
        self.conflict_resolved.emit(original_path, target_path, "skipped")
        return ""

    def _overwrite_conflict(self, original_path: str, target_path: str) -> str:
        """Overwrite the existing target file."""
        logger.info("Overwriting existing file: %s", target_path)
        self.conflict_resolved.emit(original_path, target_path, "overwritten")
        return target_path

    def _rename_with_suffix(self, original_path: str, target_path: str) -> str:
        """Generate a new target path with a numeric suffix."""
        target_path_obj = Path(target_path)
        base_name = target_path_obj.stem
        extension = target_path_obj.suffix
        parent_dir = target_path_obj.parent

        counter = 1
        while True:
            new_name = f"{base_name}_{counter}{extension}"
            new_path = parent_dir / new_name

            if not new_path.exists():
                new_target = str(new_path)
                logger.info("Resolving conflict with suffix: %s -> %s", original_path, new_target)
                self.conflict_resolved.emit(original_path, target_path, f"renamed_to_{new_target}")
                return new_target

            counter += 1
            if counter > 1000:  # Safety limit
                logger.error("Too many conflict resolution attempts")
                return self._skip_conflict(original_path, target_path)

    def _ask_user_for_resolution(self, original_path: str, target_path: str) -> str:
        """
        Ask user for conflict resolution (placeholder for future implementation).

        Currently defaults to skip strategy.
        """
        logger.info("User interaction for conflict resolution not yet implemented, skipping")
        return self._skip_conflict(original_path, target_path)

    def register_resolution_callback(self, conflict_id: str, callback: Callable) -> None:
        """
        Register a callback for specific conflict resolution.

        Args:
            conflict_id: Unique identifier for the conflict
            callback: Function to call when resolution is needed
        """
        self.resolution_callbacks[conflict_id] = callback
        logger.debug("Registered resolution callback for conflict: %s", conflict_id)
