"""Module: rename_logic.py.

Author: Michael Economou
Date: 2025-05-12

rename_logic.py
This module provides the core logic for building, resolving, and executing
rename plans for batch file renaming operations. It separates rename logic
from the UI layer to allow better maintainability and reusability.
Functions:
- build_rename_plan: Generates a list of rename operations with conflict detection.
- resolve_rename_conflicts: Prompts user to resolve filename conflicts before rename.
- execute_rename_plan: Performs the actual renaming actions based on the plan.
- get_preview_pairs: Generates preview name pairs from checked files and renaming rules.
"""

import os
import platform
from collections.abc import Callable
from typing import Any

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


def is_case_only_change(old: str, new: str) -> bool:
    """Check if the only difference between old and new names is case."""
    return old.lower() == new.lower() and old != new


def safe_case_rename(src_path: str, dst_path: str) -> bool:
    """Safely rename a file when only the case changes, working around Windows limitations.

    On Windows, NTFS is case-insensitive, so os.rename(file.txt, FILE.TXT) fails.
    This function uses a two-step process: rename to temporary name, then to final name.

    Args:
        src_path: Source file path
        dst_path: Destination file path

    Returns:
        bool: True if rename was successful, False otherwise

    """
    try:
        # Get the directory and filenames
        src_dir = os.path.dirname(src_path)
        src_name = os.path.basename(src_path)
        dst_name = os.path.basename(dst_path)

        # Check if this is actually a case-only change
        if not is_case_only_change(src_name, dst_name):
            # Not a case-only change, use regular rename
            os.rename(src_path, dst_path)
            return True

        # For case-only changes, we need special handling on Windows
        if platform.system() == "Windows":
            # Step 1: Create a unique temporary name in the same directory
            temp_name = f"_temp_rename_{hash(dst_name)}.tmp"
            temp_path = os.path.join(src_dir, temp_name)

            # Make sure temp name doesn't exist
            counter = 0
            while os.path.exists(temp_path):
                counter += 1
                temp_name = f"_temp_rename_{hash(dst_name)}_{counter}.tmp"
                temp_path = os.path.join(src_dir, temp_name)
                if counter > 100:  # Safety valve
                    logger.error("Could not find unique temp name for case rename: %s", src_path)
                    return False

            # Step 2: Rename to temporary name
            os.rename(src_path, temp_path)
            logger.debug("Case rename step 1: %s -> %s", src_name, temp_name)

            # Step 3: Rename from temporary to final name
            os.rename(temp_path, dst_path)
            logger.debug("Case rename step 2: %s -> %s", temp_name, dst_name)

            logger.info("Successfully completed case-only rename: %s -> %s", src_name, dst_name)
            return True
        else:
            # On Unix-like systems, case-sensitive filesystems should work with direct rename
            os.rename(src_path, dst_path)
            return True

    except Exception as e:
        logger.error("Failed to perform case rename from %s to %s: %s", src_path, dst_path, e)

        # Cleanup: if we created a temp file but failed, try to restore original
        try:
            if (
                platform.system() == "Windows"
                and "temp_path" in locals()
                and os.path.exists(temp_path)
            ):
                if not os.path.exists(src_path):
                    os.rename(temp_path, src_path)
                    logger.info("Restored original file after failed case rename: %s", src_path)
        except Exception as cleanup_error:
            logger.error("Failed to cleanup after case rename failure: %s", cleanup_error)

        return False


def build_rename_plan(
    _file_items: list[Any], preview_pairs: list[tuple[str, str]], folder_path: str
) -> list[dict[str, Any]]:
    """Builds a plan of rename operations with conflict detection.

    Args:
        file_items (List[object]): List of file objects, each with .filename
        preview_pairs (List[Tuple[str, str]]): List of (old_name, new_name) preview tuples
        folder_path (str): Absolute path to the folder containing the files

    Returns:
        List[Dict]: A list of rename instructions with conflict info and undecided action

    """
    plan = []

    for old_name, new_name in preview_pairs:
        src_path = os.path.join(folder_path, old_name)
        dst_path = os.path.join(folder_path, new_name)

        # Mark case-only changes for special handling
        is_case_only = is_case_only_change(old_name, new_name)

        # Ignore conflict if the only change is in letter case
        conflict = (
            os.path.exists(dst_path)
            and not is_case_only
            and os.path.abspath(dst_path) != os.path.abspath(src_path)
        )

        plan.append(
            {
                "src": old_name,
                "dst": new_name,
                "src_path": src_path,
                "dst_path": dst_path,
                "conflict": conflict,
                "is_case_only": is_case_only,
                "action": "undecided",
            }
        )

    return plan


def resolve_rename_conflicts(
    plan: list[dict[str, Any]], ask_user_callback: Callable[[str, str], tuple[str, bool]]
) -> list[dict[str, Any]]:
    """Resolves rename conflicts by prompting the user.

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


def execute_rename_plan(plan: list[dict[str, Any]]) -> int:
    """Executes the rename plan based on resolved actions.

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
            # Use safe case rename for case-only changes
            if entry.get("is_case_only", False):
                if safe_case_rename(entry["src_path"], entry["dst_path"]):
                    success_count += 1
                    logger.info("Case-only rename successful: %s -> %s", entry["src"], entry["dst"])
                else:
                    logger.warning("Case-only rename failed: %s -> %s", entry["src"], entry["dst"])
            else:
                # Regular rename
                os.rename(entry["src_path"], entry["dst_path"])
                success_count += 1
        except Exception as e:
            logger.error("Failed to rename %s -> %s: %s", entry["src"], entry["dst"], e)

    return success_count


def get_preview_pairs(
    file_items: list[Any], rename_function: Callable[[Any], str]
) -> list[tuple[str, str]]:
    """Generates preview name pairs (old, new) for the selected files using rename logic.

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
