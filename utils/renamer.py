import os
from typing import List, Callable, Optional
from PyQt5.QtCore import QDir
from PyQt5.QtWidgets import QWidget

from models.file_item import FileItem
from utils.preview_generator import generate_preview_names
from utils.validation import is_valid_filename_text
from widgets.custom_msgdialog import CustomMessageDialog

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)


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
        parent: Optional[QWidget] = None,
        conflict_callback: Optional[Callable[[QWidget, str], str]] = None,
        validator: Optional[object] = None
    ) -> None:
        """
        Initializes the Renamer logic for actual renaming operations.

        Parameters
        ----------
        file_items : List[FileItem]
            The selected FileItem objects to rename.
        modules_data : List[dict]
            The active rename modules and their configurations.
        metadata cache : dict
            The metadata cache (full_path → metadata cache dict).
        parent : QWidget, optional
            Parent widget for dialogs.
        conflict_callback : Callable, optional
            Callback to resolve rename conflicts. Returns one of:
            'overwrite', 'skip', 'skip_all', 'cancel'.
        """
        self.files = files
        self.modules_data = modules_data
        self.metadata_cache = metadata_cache
        self.parent = parent
        self.conflict_callback = conflict_callback
        self.validator = validator

        if self.validator is None:
            raise ValueError("Filename validator is required for renaming.")

    def rename(self) -> list[RenameResult]:
        """
        Executes the renaming process for selected files using the current rename modules.
        Handles preview name generation, validation, conflict resolution, and file system renaming.

        Returns
        -------
        list[RenameResult]
            A list of results indicating the outcome for each file.
        """
        logger.info("Starting rename process for %d files...", len(self.files))

        # Generate preview names
        preview_pairs, has_error, tooltip = generate_preview_names(
            files = self.files,
            modules_data = self.modules_data,
            metadata_cache = self.metadata_cache
        )

        if has_error:
            logger.warning("Preview generation failed: %s", tooltip)
            return [RenameResult(f.full_path, "", success=False, error=tooltip) for f in self.files]

        # Build rename plan from file paths
        old_to_new = {f.full_path: new_name for f, (_, new_name) in zip(self.files, preview_pairs)}

        results = []
        skip_all = False

        for file in self.files:
            src = file.full_path
            dst = os.path.join(os.path.dirname(src), old_to_new[src])

            # Validate new filename
            new_filename = os.path.basename(dst)
            if not is_valid_filename_text(new_filename):
                logger.warning("Invalid filename: %s", new_filename)
                results.append(RenameResult(src, dst, success=False, error="Invalid filename"))
                continue

            # Check for conflict
            if os.path.exists(dst):
                if skip_all:
                    results.append(RenameResult(src, dst, success=False, skip_reason="conflict (skip all)"))
                    continue

                action = self.conflict_callback(self.parent, new_filename)
                if action == "overwrite":
                    pass  # proceed
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

            # Attempt rename
            try:
                os.rename(src, dst)
                results.append(RenameResult(src, dst, success=True))
            except Exception as e:
                logger.error("Rename failed for %s: %s", src, str(e))
                results.append(RenameResult(src, dst, success=False, error=str(e)))

            # Re-map metadata cache for renamed files
            for result in results:
                if result.success and result.old_path in self.metadata_cache:
                    self.metadata_cache[result.new_path] = self.metadata_cache.pop(result.old_path)


        return results
