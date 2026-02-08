"""UI scheduler port for Qt-free core operations.

Author: Michael Economou
Date: 2026-02-08
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable


class TimerPriority(Enum):
    """Priority levels for scheduled callbacks."""

    IMMEDIATE = "immediate"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"
    CLEANUP = "cleanup"
    DELAYED = "delayed"


class TimerType(Enum):
    """Timer operation categories."""

    UI_UPDATE = "ui_update"
    DRAG_CLEANUP = "drag_cleanup"
    SELECTION_UPDATE = "selection_update"
    METADATA_LOAD = "metadata_load"
    SCROLL_ADJUST = "scroll_adjust"
    RESIZE_ADJUST = "resize_adjust"
    PREVIEW_UPDATE = "preview_update"
    STATUS_UPDATE = "status_update"
    GENERIC = "generic"


class UiSchedulerPort(Protocol):
    """Protocol for scheduling callbacks without Qt dependencies."""

    def schedule(
        self,
        callback: Callable[[], None],
        delay: int,
        priority: TimerPriority,
        timer_type: TimerType,
        timer_id: str | None = None,
        consolidate: bool = True,
    ) -> str:
        """Schedule a callback and return a timer id."""
        ...

    def cancel(self, timer_id: str) -> bool:
        """Cancel a scheduled callback."""
        ...
