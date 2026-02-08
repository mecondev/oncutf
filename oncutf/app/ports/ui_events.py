"""UI event port for Qt-free core operations.

Author: Michael Economou
Date: 2026-02-08
"""

from __future__ import annotations

from typing import Any, Protocol


class UiEventsPort(Protocol):
    """Protocol for UI event helpers without Qt dependencies."""

    def process_events(self) -> None:
        """Process pending UI events if available."""
        ...

    def get_item_data_roles(self) -> dict[str, Any]:
        """Return item data role constants for UI updates."""
        ...
