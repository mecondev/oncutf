"""Results display port for showing hash calculation results.

This port decouples core hash logic from UI dialog implementations.

Author: Michael Economou
Date: 2026-01-26
"""

from __future__ import annotations

from typing import Any, Protocol


class ResultsDisplayPort(Protocol):
    """Protocol for displaying hash calculation results to the user."""

    def show_hash_results(
        self,
        parent: Any,
        hash_results: dict[str, dict[str, str]],
        was_cancelled: bool = False,
    ) -> None:
        """Show hash calculation results in a dialog.

        Args:
            parent: Parent window for the dialog
            hash_results: Dictionary with filename as key and hash data as value
            was_cancelled: Whether the operation was cancelled (partial results)

        """
        ...
