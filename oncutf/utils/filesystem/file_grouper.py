"""Module: file_grouper.py.

Author: Michael Economou
Date: 2025-12-17

FileGroup detection and management utilities.
Provides logic for grouping related files (companion files, folder groups).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

from oncutf.models.file_group import FileGroup
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


def group_files_by_folder(files: list[FileItem]) -> list[FileGroup]:
    """Group files by their parent folder.

    Args:
        files: List of FileItem objects

    Returns:
        List of FileGroup objects, one per unique folder

    """
    folder_groups: dict[Path, FileGroup] = {}

    for file_item in files:
        folder_path = Path(file_item.full_path).parent

        if folder_path not in folder_groups:
            folder_groups[folder_path] = FileGroup(
                source_path=folder_path, files=[], recursive=False
            )

        folder_groups[folder_path].add_file(file_item)

    logger.debug(
        "[FileGrouper] Grouped %d files into %d folder groups",
        len(files),
        len(folder_groups),
        extra={"dev_only": True},
    )

    return list(folder_groups.values())


def group_files_by_companion(
    files: list[FileItem], companion_patterns: dict[str, list[str]] | None = None
) -> list[FileGroup]:
    """Group files by companion relationships (e.g., RAW+JPG pairs).

    Companion files are identified by:
    1. Same base filename (without extension)
    2. Same folder
    3. Extensions match companion patterns

    Args:
        files: List of FileItem objects
        companion_patterns: Dict mapping primary extension to companion extensions
                           Default: {'.cr2': ['.jpg'], '.nef': ['.jpg'], '.arw': ['.jpg']}

    Returns:
        List of FileGroup objects, one per companion group or standalone file

    """
    if companion_patterns is None:
        # Default companion patterns: RAW formats + JPG
        companion_patterns = {
            ".cr2": [".jpg", ".jpeg"],  # Canon RAW
            ".nef": [".jpg", ".jpeg"],  # Nikon RAW
            ".arw": [".jpg", ".jpeg"],  # Sony RAW
            ".orf": [".jpg", ".jpeg"],  # Olympus RAW
            ".dng": [".jpg", ".jpeg"],  # Adobe DNG
            ".raw": [".jpg", ".jpeg"],  # Generic RAW
        }

    # Build base name index: {(folder, basename): [files]}
    basename_index: dict[tuple[Path, str], list[FileItem]] = {}

    for file_item in files:
        folder = Path(file_item.full_path).parent
        basename = os.path.splitext(file_item.filename)[0]
        key = (folder, basename)

        if key not in basename_index:
            basename_index[key] = []

        basename_index[key].append(file_item)

    # Create FileGroups
    groups: list[FileGroup] = []

    for (folder, basename), group_files in basename_index.items():
        if len(group_files) > 1:
            # Check if files are companions
            extensions = [os.path.splitext(f.filename)[1].lower() for f in group_files]

            # Look for primary + companion pattern
            is_companion_group = False
            for primary_ext, companion_exts in companion_patterns.items():
                if primary_ext in extensions:
                    for comp_ext in companion_exts:
                        if comp_ext in extensions:
                            is_companion_group = True
                            break
                if is_companion_group:
                    break

            if is_companion_group:
                # Create companion group
                group = FileGroup(
                    source_path=folder,
                    files=group_files,
                    recursive=False,
                    metadata={"group_type": "companion", "basename": basename},
                )
                groups.append(group)
                logger.debug(
                    "[FileGrouper] Created companion group: %s (%d files)",
                    basename,
                    len(group_files),
                    extra={"dev_only": True},
                )
            else:
                # Same basename but not companions - separate groups
                for file_item in group_files:
                    group = FileGroup(
                        source_path=folder,
                        files=[file_item],
                        recursive=False,
                        metadata={"group_type": "standalone"},
                    )
                    groups.append(group)
        else:
            # Single file - standalone group
            group = FileGroup(
                source_path=folder,
                files=group_files,
                recursive=False,
                metadata={"group_type": "standalone"},
            )
            groups.append(group)

    logger.debug(
        "[FileGrouper] Grouped %d files into %d companion/standalone groups",
        len(files),
        len(groups),
        extra={"dev_only": True},
    )

    return groups


def get_file_group_index(file_item: FileItem, groups: list[FileGroup]) -> tuple[int, int]:
    """Get the group index and index within group for a file.

    Args:
        file_item: File to find
        groups: List of FileGroup objects

    Returns:
        Tuple of (group_index, index_within_group)
        Returns (-1, -1) if file not found

    """
    for group_idx, group in enumerate(groups):
        for file_idx, f in enumerate(group.files):
            if f.full_path == file_item.full_path:
                return (group_idx, file_idx)

    logger.warning("[FileGrouper] File not found in any group: %s", file_item.filename)
    return (-1, -1)


def calculate_filegroup_counter_index(
    file_item: FileItem,
    all_files: list[FileItem],
    global_index: int,
    groups: list[FileGroup] | None = None,
) -> int:
    """Calculate counter index for PER_FILEGROUP scope.

    Args:
        file_item: Current file
        all_files: Full list of files
        global_index: Global file index
        groups: Pre-computed FileGroup list (if None, will group by folder)

    Returns:
        Index within the file's group

    """
    if groups is None:
        # Default: group by folder
        groups = group_files_by_folder(all_files)

    group_idx, index_within_group = get_file_group_index(file_item, groups)

    if group_idx == -1:
        logger.warning(
            "[FileGrouper] File not in any group, using global index: %s",
            file_item.filename,
        )
        return global_index

    logger.debug(
        "[FileGrouper] File '%s' is in group %d at index %d",
        file_item.filename,
        group_idx,
        index_within_group,
        extra={"dev_only": True},
    )

    return index_within_group
