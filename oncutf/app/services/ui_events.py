"""UI event service facade.

Author: Michael Economou
Date: 2026-02-08
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from oncutf.app.ports.ui_events import UiEventsPort


_DEFAULT_ROLES: dict[str, Any] = {
    "DecorationRole": 1,
    "ToolTipRole": 3,
    "DisplayRole": 0,
    "EditRole": 2,
}


def _get_adapter() -> UiEventsPort | None:
    from oncutf.app.state.context import AppContext

    try:
        ctx = AppContext.get_instance()
    except RuntimeError:
        return None

    if not ctx.has_manager("ui_events"):
        return None

    return cast("UiEventsPort", ctx.get_manager("ui_events"))


def process_events() -> None:
    """Process pending UI events via registered adapter."""
    adapter = _get_adapter()
    if adapter is None:
        return
    adapter.process_events()


def get_item_data_roles() -> dict[str, Any]:
    """Return item data roles via adapter or fallback defaults."""
    adapter = _get_adapter()
    if adapter is None:
        return _DEFAULT_ROLES.copy()
    return adapter.get_item_data_roles()
