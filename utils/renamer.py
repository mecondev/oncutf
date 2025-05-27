import os
from typing import List, Callable, Optional
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
        Initializes the Renamer with required inputs for batch renaming.

        Parameters:
            files (List[FileItem]): List of FileItem objects selected for rename.
            modules_data (List[dict]): Serialized rename module data.
            metadata_cache (dict): Metadata dictionary (full_path → metadata dict).
            parent (QWidget, optional): Parent UI component.
            conflict_callback (Callable, optional): Function to handle filename conflicts.
            validator (object): Object to validate filename text.
        """
        self.files = files
        self.modules_data = modules_data
        self.metadata_cache = metadata_cache
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
        old_to_new = {
            f.full_path: new_name
            for f, (_, new_name) in zip(self.files, preview_pairs)
        }

        results = []
        skip_all = False

        # Step 3: Apply rename for each file
        for file in self.files:
            src = file.full_path
            dst = os.path.join(os.path.dirname(src), old_to_new[src])
            new_filename = os.path.basename(dst)

            # Validation
            if not is_valid_filename_text(new_filename):
                logger.warning(f"Invalid filename: {new_filename}")
                results.append(RenameResult(src, dst, success=False, error="Invalid filename"))
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
