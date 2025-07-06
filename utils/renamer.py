"""
Module: renamer.py

Author: Michael Economou
Date: 2025-06-01

Initializes the Renamer with required inputs for batch renaming.
Parameters:
files (List[FileItem]): List of FileItem objects selected for rename.
modules_data (List[dict]): Serialized rename module data.
metadata_cache (dict): Metadata dictionary (full_path → metadata dict).
post_transform (dict, optional): Transformation options (case, separator).
parent (QWidget, optional): Parent UI component.
conflict_callback (Callable, optional): Function to handle filename conflicts.
validator (object): Object to validate filename text.
"""
import os
from typing import Callable, List, Optional

from core.qt_imports import QWidget

from models.file_item import FileItem
from modules.name_transform_module import NameTransformModule

# Initialize Logger
from utils.logger_factory import get_cached_logger
from utils.preview_generator import generate_preview_names

logger = get_cached_logger(__name__)


class RenameResult:
    def __init__(self, old_path: str, new_path: str, success: bool,
                 skip_reason: Optional[str] = None, error: Optional[str] = None):
        self.old_path = old_path
        self.new_path = new_path
        self.success = success
        self.skip_reason = skip_reason
        self.error = error


class Renamer:
    def __init__(
        self,
        files: List[FileItem],
        modules_data: List[dict],
        metadata_cache: dict,
        post_transform: Optional[dict] = None,
        parent: Optional[QWidget] = None,
        conflict_callback: Optional[Callable[[QWidget, str], str]] = None,
        validator: Optional[object] = None
    ) -> None:
        """
        Initializes the Renamer with required inputs for batch renaming.

        Parameters:
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

    def rename(self) -> List[RenameResult]:
        """
        Executes the renaming process for the selected files.

        Returns:
            List[RenameResult]: Outcome of each rename attempt.
        """
        logger.debug(f"Starting rename process for {len(self.files)} files...", extra={"dev_only": True})

        # Step 1: Generate preview names from modules
        preview_pairs, has_error, tooltip = generate_preview_names(
            files=self.files,
            modules_data=self.modules_data,
            metadata_cache=self.metadata_cache
        )

        if has_error:
            logger.warning(f"Preview generation failed: {tooltip}")
            return [RenameResult(f.full_path, "", success=False, error=tooltip) for f in self.files]

        # Step 2: Map old path to new name
        old_to_new = {}
        for f, (_, new_name) in zip(self.files, preview_pairs):
            # Remove extension if already present (work with basename only)
            basename, extension = os.path.splitext(f.filename)
            if extension and new_name.lower().endswith(extension.lower()):
                new_basename = new_name[:-(len(extension))]
            else:
                new_basename = new_name

            # Apply name transform (case, separator) to basename only - same logic as preview
            if NameTransformModule.is_effective(self.post_transform):
                new_basename = NameTransformModule.apply_from_data(self.post_transform, new_basename)
                logger.debug(f"Transform applied: {new_basename}")

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
            if src is None:
                logger.error(f"File {file.filename} has no full_path")
                results.append(RenameResult("", "", success=False, error="No full path"))
                continue

            dst = os.path.join(os.path.dirname(src), old_to_new[src])
            new_filename = os.path.basename(dst)

            # Validation
            is_valid, error_msg = self.validator(new_filename)
            if not is_valid:
                logger.warning(f"Invalid filename: {new_filename} - {error_msg}")
                results.append(RenameResult(src, dst, success=False, error=error_msg))
                continue

            # Conflict resolution
            if os.path.exists(dst):
                if skip_all:
                    results.append(RenameResult(src, dst, success=False, skip_reason="conflict (skip all)"))
                    continue

                action = self.conflict_callback(self.parent, new_filename)

                if action == "overwrite":
                    pass  # Proceed
                elif action == "skip":
                    results.append(RenameResult(src, dst, success=False, skip_reason="conflict (skipped)"))
                    continue
                elif action == "skip_all":
                    skip_all = True
                    results.append(RenameResult(src, dst, success=False, skip_reason="conflict (skip all)"))
                    continue
                else:
                    logger.info("Rename cancelled by user.")
                    break

            # File rename
            try:
                os.rename(src, dst)
                results.append(RenameResult(src, dst, success=True))
            except Exception as e:
                logger.error(f"Rename failed for {src}: {str(e)}")
                results.append(RenameResult(src, dst, success=False, error=str(e)))

        for result in results:
            if result.success and result.old_path in self.metadata_cache._cache:
                metadata = self.metadata_cache.get(result.old_path)
                if isinstance(metadata, dict):
                    clean_meta = filter_metadata_safe(metadata)
                    clean_meta["FileName"] = os.path.basename(result.new_path)
                    self.metadata_cache.set(result.new_path, clean_meta)

        return results

def filter_metadata_safe(metadata: dict) -> dict:
    """
    Returns a shallow copy of metadata with only JSON-safe primitive fields.
    Excludes objects like preview_map, Qt instances, and recursive structures.

    Parameters:
        metadata (dict): Original metadata dict.

    Returns:
        dict: Filtered dictionary with only str, int, float, bool, or None values.
    """
    return {
        k: v for k, v in metadata.items()
        if isinstance(v, (str, int, float, bool, type(None)))
    }
