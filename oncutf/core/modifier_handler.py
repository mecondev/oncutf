"""Module: modifier_handler.py.

Author: Michael Economou
Date: 2025-05-31

modifier_handler.py
Centralized handling of keyboard modifier combinations for file operations.
Provides consistent logic across all file loading contexts (import, browse, drag & drop).

NOTE: Refactored 2026-02-03 to remove Qt dependency.
Keyboard modifiers are passed as int flags instead of Qt.KeyboardModifiers.
"""

from enum import Enum

# Qt modifier constants (copied to avoid Qt dependency)
CONTROL_MODIFIER = 0x04000000
SHIFT_MODIFIER = 0x02000000


class ModifierAction(Enum):
    """Enumeration of available modifier actions for file operations."""

    REPLACE_SHALLOW = "replace_shallow"
    REPLACE_RECURSIVE = "replace_recursive"
    MERGE_SHALLOW = "merge_shallow"
    MERGE_RECURSIVE = "merge_recursive"


def decode_modifiers(modifiers: int) -> tuple[ModifierAction, str]:
    """Decode keyboard modifiers into a ModifierAction and description.

    Modifier logic:
    - Normal: Replace + shallow
    - Shift: Merge + shallow
    - Ctrl: Replace + recursive
    - Ctrl+Shift: Merge + recursive

    Args:
        modifiers: Keyboard modifier flags (int). Use QApplication.keyboardModifiers()
                  and pass int(modifiers) to this function.

    Returns:
        Tuple of (ModifierAction, human-readable description)

    """
    is_ctrl = bool(modifiers & CONTROL_MODIFIER)
    is_shift = bool(modifiers & SHIFT_MODIFIER)

    if is_ctrl and is_shift:
        return ModifierAction.MERGE_RECURSIVE, "Merge + Recursive"
    if is_ctrl:
        return ModifierAction.REPLACE_RECURSIVE, "Replace + Recursive"
    if is_shift:
        return ModifierAction.MERGE_SHALLOW, "Merge + Shallow"
    return ModifierAction.REPLACE_SHALLOW, "Replace + Shallow"


def get_action_flags(action: ModifierAction) -> tuple[bool, bool]:
    """Get merge_mode and recursive flags from a ModifierAction.

    Args:
        action: The ModifierAction to decode

    Returns:
        Tuple of (merge_mode, recursive)

    """
    if action == ModifierAction.MERGE_RECURSIVE:
        return True, True  # merge=True, recursive=True
    if action == ModifierAction.REPLACE_RECURSIVE:
        return False, True  # merge=False, recursive=True
    if action == ModifierAction.MERGE_SHALLOW:
        return True, False  # merge=True, recursive=False
    # REPLACE_SHALLOW
    return False, False  # merge=False, recursive=False


def decode_modifiers_to_flags(
    modifiers: int,
) -> tuple[bool, bool, str]:
    """Convenience function to decode modifiers directly to flags and description.

    Args:
        modifiers: Keyboard modifier flags (int)

    Returns:
        Tuple of (merge_mode, recursive, description)

    """
    action, description = decode_modifiers(modifiers)
    merge_mode, recursive = get_action_flags(action)
    return merge_mode, recursive, description


def get_action_description(action: ModifierAction) -> str:
    """Get human-readable description for a ModifierAction.

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
