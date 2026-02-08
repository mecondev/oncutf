"""UI scheduler service facade.

Author: Michael Economou
Date: 2026-02-08
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, cast

from oncutf.app.ports.ui_scheduler import TimerPriority, TimerType

if TYPE_CHECKING:
    from collections.abc import Callable

    from oncutf.app.ports.ui_scheduler import UiSchedulerPort


_fallback_lock = threading.RLock()
_fallback_counter = 0
_fallback_timers: dict[str, threading.Timer] = {}

__all__ = [
    "TimerPriority",
    "TimerType",
    "cancel_timer",
    "schedule_timer",
]


def _get_adapter() -> UiSchedulerPort | None:
    from oncutf.app.state.context import AppContext

    try:
        ctx = AppContext.get_instance()
    except RuntimeError:
        return None

    if not ctx.has_manager("ui_scheduler"):
        return None

    return cast("UiSchedulerPort", ctx.get_manager("ui_scheduler"))


def schedule_timer(
    callback: Callable[[], None],
    *,
    delay: int = 15,
    priority: TimerPriority = TimerPriority.NORMAL,
    timer_type: TimerType = TimerType.GENERIC,
    timer_id: str | None = None,
    consolidate: bool = True,
) -> str:
    """Schedule a callback using the registered UI scheduler.

    Falls back to a threading.Timer when no adapter is available.
    """
    adapter = _get_adapter()
    if adapter is not None:
        return adapter.schedule(
            callback,
            delay,
            priority,
            timer_type,
            timer_id=timer_id,
            consolidate=consolidate,
        )

    global _fallback_counter
    with _fallback_lock:
        if timer_id is None:
            timer_id = f"fallback_{_fallback_counter}"
            _fallback_counter += 1

        existing = _fallback_timers.get(timer_id)
        if existing is not None:
            existing.cancel()
            _fallback_timers.pop(timer_id, None)

        def _run() -> None:
            try:
                callback()
            finally:
                with _fallback_lock:
                    _fallback_timers.pop(timer_id, None)

        timer = threading.Timer(delay / 1000.0, _run)
        _fallback_timers[timer_id] = timer
        timer.start()

    return timer_id


def cancel_timer(timer_id: str) -> bool:
    """Cancel a scheduled callback."""
    adapter = _get_adapter()
    if adapter is not None:
        return bool(adapter.cancel(timer_id))

    with _fallback_lock:
        timer = _fallback_timers.pop(timer_id, None)
        if timer is None:
            return False
        timer.cancel()
        return True
