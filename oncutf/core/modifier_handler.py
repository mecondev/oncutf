"""
Module: modifier_handler.py

Author: Michael Economou
Date: 2025-05-31

modifier_handler.py
Centralized handling of keyboard modifier combinations for file operations.
Provides consistent logic across all file loading contexts (import, browse, drag & drop).
"""

from enum import Enum

from oncutf.core.pyqt_imports import Qt


class ModifierAction(Enum):
    """Enumeration of available modifier actions for file operations."""

    REPLACE_SHALLOW = "replace_shallow"
    REPLACE_RECURSIVE = "replace_recursive"
    MERGE_SHALLOW = "merge_shallow"
    MERGE_RECURSIVE = "merge_recursive"


def decode_modifiers(modifiers: Qt.KeyboardModifiers) -> tuple[ModifierAction, str]:
    """
    Decode keyboard modifiers into a ModifierAction and description.

    Modifier logic:
    - Normal: Replace + shallow
    - Shift: Merge + shallow
    - Ctrl: Replace + recursive
    - Ctrl+Shift: Merge + recursive

    Args:
        modifiers: Qt keyboard modifiers from event or QApplication.keyboardModifiers()

    Returns:
        Tuple of (ModifierAction, human-readable description)
    """
    is_ctrl = bool(modifiers & Qt.ControlModifier)
    is_shift = bool(modifiers & Qt.ShiftModifier)

    if is_ctrl and is_shift:
        return ModifierAction.MERGE_RECURSIVE, "Merge + Recursive"
    elif is_ctrl:
        return ModifierAction.REPLACE_RECURSIVE, "Replace + Recursive"
    elif is_shift:
        return ModifierAction.MERGE_SHALLOW, "Merge + Shallow"
    else:
        return ModifierAction.REPLACE_SHALLOW, "Replace + Shallow"


def get_action_flags(action: ModifierAction) -> tuple[bool, bool]:
    """
    Get merge_mode and recursive flags from a ModifierAction.

    Args:
        action: The ModifierAction to decode

    Returns:
        Tuple of (merge_mode, recursive)
    """
    if action == ModifierAction.MERGE_RECURSIVE:
        return True, True  # merge=True, recursive=True
    elif action == ModifierAction.REPLACE_RECURSIVE:
        return False, True  # merge=False, recursive=True
    elif action == ModifierAction.MERGE_SHALLOW:
        return True, False  # merge=True, recursive=False
    else:  # REPLACE_SHALLOW
        return False, False  # merge=False, recursive=False


def decode_modifiers_to_flags(modifiers: Qt.KeyboardModifiers) -> tuple[bool, bool, str]:
    """
    Convenience function to decode modifiers directly to flags and description.

    Args:
        modifiers: Qt keyboard modifiers

    Returns:
        Tuple of (merge_mode, recursive, description)
    """
    action, description = decode_modifiers(modifiers)
    merge_mode, recursive = get_action_flags(action)
    return merge_mode, recursive, description


def get_action_description(action: ModifierAction) -> str:
    """
    Get human-readable description for a ModifierAction.

    Args:
        action: The ModifierAction to describe

    Returns:
        Human-readable description string
    """
    descriptions = {
        ModifierAction.REPLACE_SHALLOW: "Replace + Shallow",
        ModifierAction.REPLACE_RECURSIVE: "Replace + Recursive",
        ModifierAction.MERGE_SHALLOW: "Merge + Shallow",
        ModifierAction.MERGE_RECURSIVE: "Merge + Recursive",
    }
    return descriptions.get(action, "Unknown")


def is_merge_mode(action: ModifierAction) -> bool:
    """Check if action uses merge mode (vs replace mode)."""
    return action in (ModifierAction.MERGE_SHALLOW, ModifierAction.MERGE_RECURSIVE)


def is_recursive_mode(action: ModifierAction) -> bool:
    """Check if action uses recursive mode (vs shallow mode)."""
    return action in (ModifierAction.REPLACE_RECURSIVE, ModifierAction.MERGE_RECURSIVE)
