"""Module: renamer.py

Author: Michael Economou
Date: 2025-05-15

Initializes the Renamer with required inputs for batch renaming.

Parameters
----------
files (List[FileItem]): List of FileItem objects selected for rename.
modules_data (List[dict]): Serialized rename module data.
metadata_cache (dict): Metadata dictionary (full_path → metadata dict).
post_transform (dict, optional): Transformation options (case, separator).
parent (QWidget, optional): Parent UI component.
conflict_callback (Callable, optional): Function to handle filename conflicts.
validator (object): Object to validate filename text.

"""

import os
from collections.abc import Callable
from typing import Any

from oncutf.core.pyqt_imports import QWidget
from oncutf.core.type_aliases import MetadataCacheProtocol, MetadataDict
from oncutf.models.file_item import FileItem
from oncutf.modules.name_transform_module import NameTransformModule

# Initialize Logger
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.naming.preview_generator import generate_preview_names

logger = get_cached_logger(__name__)


class RenameResult:
    """Result of a single file rename operation.

    Attributes:
        old_path: Original file path
        new_path: New file path (if successful)
        success: True if rename succeeded
        skip_reason: Reason for skipping (if applicable)
        error: Error message (if failed)
    """

    def __init__(
        self,
        old_path: str,
        new_path: str,
        success: bool,
        skip_reason: str | None = None,
        error: str | None = None,
    ):
        self.old_path = old_path
        self.new_path = new_path
        self.success = success
        self.skip_reason = skip_reason
        self.error = error


class Renamer:
    """Batch file renaming engine with preview, validation, and conflict resolution.

    Orchestrates the complete rename workflow:
    1. Generate preview names from modules
    2. Apply post-transformations (case, separators)
    3. Validate filenames
    4. Handle conflicts
    5. Execute filesystem renames

    Attributes:
        files: List of FileItem objects to rename
        modules_data: Serialized rename module configurations
        metadata_cache: Metadata lookup cache
        post_transform: Case and separator transformations
        parent: Parent widget for dialogs
        conflict_callback: Function to resolve filename conflicts
        validator: Filename validation function
    """

    def __init__(
        self,
        files: list[FileItem],
        modules_data: list[dict[str, Any]],
        metadata_cache: MetadataCacheProtocol,
        post_transform: dict[str, Any] | None = None,
        parent: QWidget | None = None,
        conflict_callback: Callable[[QWidget | None, str], str] | None = None,
        validator: Callable[[str], tuple[bool, str | None]] | None = None,
    ) -> None:
        """Initializes the Renamer with required inputs for batch renaming.

        Parameters
        ----------
            files (List[FileItem]): List of FileItem objects selected for rename.
            modules_data (List[dict]): Serialized rename module data.
            metadata_cache (dict): Metadata dictionary (full_path → metadata dict).
            post_transform (dict, optional): Transformation options (case, separator).
            parent (QWidget, optional): Parent UI component.
            conflict_callback (Callable, optional): Function to handle filename conflicts.
            validator (object): Object to validate filename text.

        """
        self.files = files
        self.modules_data = modules_data
        self.metadata_cache = metadata_cache
        self.post_transform = post_transform or {}
        self.parent = parent
        self.conflict_callback = conflict_callback
        self.validator = validator

        if self.validator is None:
            raise ValueError("Filename validator is required for renaming.")

    def rename(self) -> list[RenameResult]:
        """Executes the renaming process for the selected files.

        Returns:
            List[RenameResult]: Outcome of each rename attempt.

        """
        logger.debug(
            "Starting rename process for %d files...", len(self.files), extra={"dev_only": True}
        )

        # Step 1: Generate preview names from modules
        preview_pairs, has_error, tooltip = generate_preview_names(
            files=self.files, modules_data=self.modules_data, metadata_cache=self.metadata_cache
        )

        if has_error:
            logger.warning("Preview generation failed: %s", tooltip)
            return [RenameResult(f.full_path, "", success=False, error=tooltip) for f in self.files]

        # Step 2: Map old path to new name
        old_to_new = {}
        for f, (_, new_name) in zip(self.files, preview_pairs, strict=False):
            # Remove extension if already present (work with basename only)
            basename, extension = os.path.splitext(f.filename)
            if extension and new_name.lower().endswith(extension.lower()):
                new_basename = new_name[: -(len(extension))]
            else:
                new_basename = new_name

            # Apply name transform (case, separator) to basename only - same logic as preview
            if NameTransformModule.is_effective_data(self.post_transform):
                new_basename = NameTransformModule.apply_from_data(
                    self.post_transform, new_basename
                )
                logger.debug("Transform applied: %s", new_basename)

            # Final cleanup: strip any remaining leading/trailing spaces from basename
            new_basename = new_basename.strip()

            # Combine with extension
            final_name = f"{new_basename}{extension}" if extension else new_basename
            old_to_new[f.full_path] = final_name

        results = []
        skip_all = False

        # Step 3: Apply rename for each file
        for file in self.files:
            src = file.full_path
            # full_path is non-optional, no need for None check

            dst = os.path.join(os.path.dirname(src), old_to_new[src])
            new_filename = os.path.basename(dst)

            # Validation
            if self.validator is None:
                results.append(RenameResult(src, dst, success=False, error="Validator missing"))
                continue

            is_valid, error_msg = self.validator(new_filename)
            if not is_valid:
                logger.warning("Invalid filename: %s - %s", new_filename, error_msg)
                results.append(RenameResult(src, dst, success=False, error=error_msg))
                continue

            # Conflict resolution
            if os.path.exists(dst):
                if skip_all:
                    results.append(
                        RenameResult(src, dst, success=False, skip_reason="conflict (skip all)")
                    )
                    continue

                if self.conflict_callback is None:
                    # Default behavior if no callback: skip
                    results.append(
                        RenameResult(src, dst, success=False, skip_reason="conflict (no callback)")
                    )
                    continue

                action = self.conflict_callback(self.parent, new_filename)

                if action == "overwrite":
                    pass  # Proceed
                elif action == "skip":
                    results.append(
                        RenameResult(src, dst, success=False, skip_reason="conflict (skipped)")
                    )
                    continue
                elif action == "skip_all":
                    skip_all = True
                    results.append(
                        RenameResult(src, dst, success=False, skip_reason="conflict (skip all)")
                    )
                    continue
                else:
                    logger.info("Rename cancelled by user.")
                    break

            # File rename - ensure paths are absolute and normalized for cross-platform support
            try:
                # Import utilities
                from oncutf.utils.filesystem.path_normalizer import normalize_path
                from oncutf.utils.naming.rename_logic import is_case_only_change, safe_case_rename

                # Normalize paths to absolute for cross-platform compatibility
                # This is critical for Windows where relative paths can cause issues
                src_normalized = normalize_path(src)
                dst_normalized = normalize_path(dst)

                # Verify source file exists before attempting rename
                if not os.path.exists(src_normalized):
                    error_msg = f"Source file not found: {src_normalized}"
                    logger.error("[Rename] %s", error_msg)
                    results.append(RenameResult(src, dst, success=False, error=error_msg))
                    continue

                src_name = os.path.basename(src_normalized)
                dst_name = os.path.basename(dst_normalized)

                # Use safe case rename for case-only changes
                if is_case_only_change(src_name, dst_name):
                    if safe_case_rename(src_normalized, dst_normalized):
                        results.append(RenameResult(src, dst, success=True))
                        logger.info("Case-only rename successful: %s -> %s", src_name, dst_name)
                    else:
                        results.append(
                            RenameResult(src, dst, success=False, error="Case-only rename failed")
                        )
                        logger.error("Case-only rename failed: %s -> %s", src_name, dst_name)
                else:
                    # Regular rename with normalized paths
                    os.rename(src_normalized, dst_normalized)
                    results.append(RenameResult(src, dst, success=True))
                    logger.debug(
                        "[Rename] Success: %s -> %s", src_name, dst_name, extra={"dev_only": True}
                    )
            except PermissionError as e:
                error_msg = f"Permission denied (file may be in use): {str(e)}"
                logger.error("[Rename] %s for %s", error_msg, src)
                results.append(RenameResult(src, dst, success=False, error=error_msg))
            except OSError as e:
                error_msg = f"OS error during rename: {str(e)}"
                logger.error("[Rename] %s for %s", error_msg, src)
                results.append(RenameResult(src, dst, success=False, error=error_msg))
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                logger.error("[Rename] %s for %s", error_msg, src)
                results.append(RenameResult(src, dst, success=False, error=error_msg))

        # Update metadata cache for renamed files
        try:
            for result in results:
                if result.success:
                    # Check if metadata exists for the old path
                    metadata = self.metadata_cache.get(result.old_path)
                    if metadata:
                        clean_meta = filter_metadata_safe(metadata)
                        clean_meta["FileName"] = os.path.basename(result.new_path)
                        self.metadata_cache.set(result.new_path, clean_meta)
        except Exception as e:
            logger.error("[Renamer] Error updating metadata cache: %s", e)

        # Update database file_paths table for renamed files
        # This preserves all associated data (metadata, hashes, color_tag, etc.)
        try:
            from oncutf.core.database.database_manager import get_database_manager

            db_manager = get_database_manager()
            for result in results:
                if result.success:
                    db_manager.update_file_path(result.old_path, result.new_path)
        except Exception as e:
            logger.error("[Renamer] Error updating database paths: %s", e)

        return results


def filter_metadata_safe(metadata: MetadataDict) -> MetadataDict:
    """Returns a shallow copy of metadata with only JSON-safe primitive fields.
    Excludes objects like preview_map, Qt instances, and recursive structures.

    Parameters
    ----------
        metadata (dict): Original metadata dict.

    Returns
    -------
        dict: Filtered dictionary with only str, int, float, bool, or None values.

    """
    return {
        k: v for k, v in metadata.items() if isinstance(v, str | int | float | bool | type(None))
    }
