"""Module: qt_keyboard.py.

Author: Michael Economou
Date: 2026-02-03

Qt keyboard adapter - converts Qt keyboard types to domain types.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt5.QtCore import Qt

from oncutf.domain.keyboard import KeyboardModifier


def qt_modifiers_to_domain(qt_modifiers: Qt.KeyboardModifiers) -> KeyboardModifier:
    """Convert Qt keyboard modifiers to domain KeyboardModifier.

    Args:
        qt_modifiers: Qt.KeyboardModifiers from event

    Returns:
        Domain KeyboardModifier flags

    Example:
        >>> from PyQt5.QtCore import Qt
        >>> qt_mods = Qt.ControlModifier | Qt.ShiftModifier
        >>> domain_mods = qt_modifiers_to_domain(qt_mods)
        >>> bool(domain_mods & KeyboardModifier.CTRL)
        True

    """
    from PyQt5.QtCore import Qt

    result = KeyboardModifier.NONE

    if qt_modifiers & Qt.ControlModifier:
        result |= KeyboardModifier.CTRL
    if qt_modifiers & Qt.ShiftModifier:
        result |= KeyboardModifier.SHIFT
    if qt_modifiers & Qt.AltModifier:
        result |= KeyboardModifier.ALT
    if qt_modifiers & Qt.MetaModifier:
        result |= KeyboardModifier.META

    return result
