"""
metadata_utils.py

Author: Michael Economou
Date: 2025-05-14

This module provides utility functions related to metadata handling
within the oncutf batch renaming application.

It includes logic for deciding whether to skip metadata scanning
based on user preferences, folder size, and modifier key overrides.

Functions:
----------
- resolve_skip_metadata: Determines whether metadata scanning should
  be skipped, incorporating default config, Ctrl override, and
  large folder confirmation dialog.

This utility centralizes metadata-related decision-making
to reduce duplication and improve maintainability.
"""
from PyQt5.QtWidgets import QWidget

def resolve_skip_metadata(
    ctrl_override: bool,
    total_files: int,
    folder_path: str,
    parent_window: QWidget,
    default_skip: bool = True,
    threshold: int = 150
) -> tuple[bool, bool]:

    raise NotImplementedError("Deprecated in favor of determine_metadata_mode()")

    """
    Returns:
        skip_metadata (bool): Whether to skip metadata
        user_wants_scan (bool): True if user explicitly chose 'Scan' in dialog
    """
    skip_metadata = default_skip ^ ctrl_override
    user_wants_scan = None  # unknown

    if not skip_metadata and total_files > threshold:
        from widgets.custom_msgdialog import CustomMessageDialog
        wants_scan = CustomMessageDialog.question(
            parent_window,
            "Large Folder",
            f"This folder contains {total_files} supported files.\n"
            "Metadata scan may take time. Scan metadata?",
            yes_text="Scan",
            no_text="Skip Metadata"
        )
        skip_metadata = not wants_scan
        user_wants_scan = wants_scan
    else:
        # infer what user "would want" if no dialog shown
        user_wants_scan = not skip_metadata

    return skip_metadata, user_wants_scan
