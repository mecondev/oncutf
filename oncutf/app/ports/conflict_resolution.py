"""Conflict resolution port for handling file naming conflicts.

This port decouples core file operations from UI dialog implementations.

Author: Michael Economou
Date: 2026-01-26
"""

from __future__ import annotations

from typing import Any, Protocol


class ConflictResolutionPort(Protocol):
    """Protocol for resolving file naming conflicts with user interaction."""

    def show_conflict(
        self,
        old_filename: str,
        new_filename: str,
        parent: Any,
    ) -> tuple[str, bool]:
        """Show conflict resolution dialog and get user decision.

        Args:
            old_filename: Original filename
            new_filename: Conflicting new filename
            parent: Parent window for the dialog

        Returns:
            Tuple of (action, apply_to_all) where:
                - action: One of "skip", "overwrite", "rename", or "cancel"
                - apply_to_all: Whether to apply this action to all conflicts

        """
        ...
