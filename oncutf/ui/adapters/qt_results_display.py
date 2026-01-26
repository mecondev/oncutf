"""Qt adapter for ResultsDisplayPort - shows hash results dialog.

Author: Michael Economou
Date: 2026-01-26
"""

from __future__ import annotations

from typing import Any


class QtResultsDisplayAdapter:
    """Qt implementation of ResultsDisplayPort using ResultsTableDialog."""

    @staticmethod
    def show_hash_results(
        parent: Any,
        hash_results: dict[str, dict[str, str]],
        was_cancelled: bool = False,
    ) -> None:
        """Show hash calculation results in ResultsTableDialog.

        Args:
            parent: Parent window for the dialog
            hash_results: Dictionary with filename as key and hash data as value
            was_cancelled: Whether the operation was cancelled (partial results)

        """
        from oncutf.ui.dialogs.results_table_dialog import ResultsTableDialog

        ResultsTableDialog.show_hash_results(
            parent=parent,
            hash_results=hash_results,
            was_cancelled=was_cancelled,
        )
