"""Qt adapter for ConflictResolutionPort - shows conflict resolution dialog.

Author: Michael Economou
Date: 2026-01-26
"""

from __future__ import annotations

from typing import Any


class QtConflictResolutionAdapter:
    """Qt implementation of ConflictResolutionPort using ConflictResolutionDialog."""

    @staticmethod
    def show_conflict(
        old_filename: str,
        new_filename: str,
        parent: Any,
    ) -> tuple[str, bool]:
        """Show conflict resolution dialog.

        Args:
            old_filename: Original filename
            new_filename: Conflicting new filename
            parent: Parent window for the dialog

        Returns:
            Tuple of (action, apply_to_all)

        """
        from oncutf.ui.dialogs.conflict_resolution_dialog import (
            ConflictResolutionDialog,
        )

        return ConflictResolutionDialog.show_conflict(
            old_filename=old_filename,
            new_filename=new_filename,
            parent=parent,
        )
