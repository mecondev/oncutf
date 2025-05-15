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
) -> bool:
    """
    Determines whether to skip metadata scan.

    Rules:
    - skip = default_skip XOR ctrl_override
    - if skip → never ask
    - if not skip (i.e. we will scan), then ask only if folder is large
    """
    # Λογικό XOR — αν ctrl αλλάζει τη συμπεριφορά του default
    skip_metadata = default_skip ^ ctrl_override

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

    return skip_metadata
