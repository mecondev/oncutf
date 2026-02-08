"""Qt UI scheduler adapter.

Author: Michael Economou
Date: 2026-02-08
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from oncutf.utils.shared.timer_manager import (
    TimerPriority as QtTimerPriority,
    TimerType as QtTimerType,
    get_timer_manager,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from oncutf.app.ports.ui_scheduler import TimerPriority, TimerType


class QtUiSchedulerAdapter:
    """Qt-backed scheduler implementation using TimerManager."""

    def schedule(
        self,
        callback: Callable[[], None],
        delay: int,
        priority: TimerPriority,
        timer_type: TimerType,
        timer_id: str | None = None,
        consolidate: bool = True,
    ) -> str:
        qt_priority = self._map_priority(priority)
        qt_timer_type = self._map_timer_type(timer_type)

        return get_timer_manager().schedule(
            callback,
            delay,
            qt_priority,
            qt_timer_type,
            timer_id,
            consolidate,
        )

    def cancel(self, timer_id: str) -> bool:
        return bool(get_timer_manager().cancel(timer_id))

    def _map_priority(self, priority: TimerPriority) -> QtTimerPriority:
        try:
            return QtTimerPriority[priority.name]
        except KeyError:
            return QtTimerPriority.NORMAL

    def _map_timer_type(self, timer_type: TimerType) -> QtTimerType:
        try:
            return QtTimerType[timer_type.name]
        except KeyError:
            return QtTimerType.GENERIC
