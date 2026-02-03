"""Module: keyboard.py.

Author: Michael Economou
Date: 2026-02-03

Domain types for keyboard input handling.

Pure domain layer - no UI dependencies.
"""

from __future__ import annotations

from enum import Flag, auto


class KeyboardModifier(Flag):
    """Keyboard modifier keys (Ctrl, Shift, Alt).

    Uses Flag enum for bitwise operations (multiple modifiers can be active).

    Example:
        >>> mods = KeyboardModifier.CTRL | KeyboardModifier.SHIFT
        >>> bool(mods & KeyboardModifier.CTRL)
        True
        >>> bool(mods & KeyboardModifier.ALT)
        False

    """

    NONE = 0
    CTRL = auto()
    SHIFT = auto()
    ALT = auto()
    META = auto()  # Windows key / Command key
