"""
rename_logic.py

This module provides the core logic for building, resolving, and executing
rename plans for batch file renaming operations. It separates rename logic
from the UI layer to allow better maintainability and reusability.

Functions:
    - build_rename_plan: Generates a list of rename operations with conflict detection.
    - resolve_rename_conflicts: Prompts user to resolve filename conflicts before rename.
    - execute_rename_plan: Performs the actual renaming actions based on the plan.
    - get_preview_pairs: Generates preview name pairs from checked files and renaming rules.

Author: Michael Economou
Date: 2025-05-11
"""

import os
from typing import List, Tuple, Dict, Callable

def build_rename_plan(
    file_items: List[object],
    preview_pairs: List[Tuple[str, str]],
    folder_path: str
) -> List[Dict]:
    """
    Builds a plan of rename operations with conflict detection.

    Args:
        file_items (List[object]): List of file objects, each with .filename
        preview_pairs (List[Tuple[str, str]]): List of (old_name, new_name) preview tuples
        folder_path (str): Absolute path to the folder containing the files

    Returns:
        List[Dict]: A list of rename instructions with conflict info and undecided action
    """

    def is_case_only_change(old: str, new: str) -> bool:
        return old.lower() == new.lower() and old != new

    plan = []

    for (old_name, new_name) in preview_pairs:
        src_path = os.path.join(folder_path, old_name)
        dst_path = os.path.join(folder_path, new_name)

        # Ignore conflict if the only change is in letter case
        conflict = (
            os.path.exists(dst_path)
            and not is_case_only_change(old_name, new_name)
            and os.path.abspath(dst_path) != os.path.abspath(src_path)
        )

        plan.append({
            "src": old_name,
            "dst": new_name,
            "src_path": src_path,
            "dst_path": dst_path,
            "conflict": conflict,
            "action": "undecided"
        })

    return plan

def resolve_rename_conflicts(plan: List[Dict], ask_user_callback: Callable[[str, str], Tuple[str, bool]]) -> List[Dict]:
    """
    Resolves rename conflicts by prompting the user.

    Args:
        plan (List[Dict]): The rename plan with conflict flags.
        ask_user_callback (Callable): A callback that receives src, dst
                                      and returns (action, apply_to_all)

    Returns:
        List[Dict]: Updated plan with 'action' set per entry, or empty list if cancelled.
    """
    resolved_plan = []
    remembered_action = None

    for entry in plan:
        if not entry["conflict"]:
            entry["action"] = "rename"
            resolved_plan.append(entry)
            continue

        if remembered_action:
            entry["action"] = remembered_action
        else:
            response, apply_to_all = ask_user_callback(entry["src"], entry["dst"])

            if response == "cancel":
                return []

            entry["action"] = response
            if apply_to_all:
                remembered_action = response

        resolved_plan.append(entry)

    return resolved_plan

def execute_rename_plan(plan: List[Dict]) -> int:
    """
    Executes the rename plan based on resolved actions.

    Args:
        plan (List[Dict]): List of rename instructions with 'action' field defined

    Returns:
        int: Number of successful renames
    """
    success_count = 0

    for entry in plan:
        if entry["action"] not in ("rename", "overwrite"):
            continue

        try:
            os.rename(entry["src_path"], entry["dst_path"])
            success_count += 1
        except Exception as e:
            # print(f"Failed to rename {entry['src']} -> {entry['dst']}: {e}")
            pass  # Silent fail - could be logged in the future

    return success_count

def get_preview_pairs(file_items: List[object], rename_function: Callable[[object], str]) -> List[Tuple[str, str]]:
    """
    Generates preview name pairs (old, new) for the selected files using rename logic.

    Args:
        file_items (List[object]): List of checked FileItem-like objects
        rename_function (Callable): A function that returns the new name for a file object

    Returns:
        List[Tuple[str, str]]: List of (original_name, preview_name) pairs
    """
    pairs = []
    for file in file_items:
        old_name = file.filename
        new_name = rename_function(file)
        pairs.append((old_name, new_name))

    return pairs
