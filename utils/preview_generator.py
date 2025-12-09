"""Preview name generation functions for file renaming.

This module provides functions to generate preview names for file renaming
based on user-defined modules. It supports modular rename logic and allows
integration with metadata.

Author: Michael Economou
Date: 2025-05-06
"""

from typing import Any

from models.file_item import FileItem
from modules.metadata_module import MetadataModule
from modules.original_name_module import OriginalNameModule
from utils.logger_factory import get_cached_logger
from utils.validate_filename_text import is_valid_filename_text

logger = get_cached_logger(__name__)


def generate_preview_names(
    files: list[FileItem],
    modules_data: list[dict[str, Any]],
    metadata_cache: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[tuple[str, str]], bool, str]:
    """
    Generate new filenames based on rename modules for a list of files.

    Args:
        files: The list of files to rename.
        modules_data: The list of rename modules in serialized form.
        metadata_cache: Cached metadata for the files (optional).

    Returns:
        A tuple containing:
        - List of (old_name, new_name) preview pairs
        - Bool indicating if any error occurred
        - Tooltip message if an error occurred
    """
    preview_pairs = []
    has_error = False
    tooltip = ""

    for index, file in enumerate(files):
        name_parts = []
        logger.debug(
            f"[PreviewGen] Start: file='{file.filename}', extension='{file.extension}'",
            extra={"dev_only": True},
        )
        for module in modules_data:
            module_type = module.get("type")
            logger.debug(
                f"[PreviewGen] Module: {module_type} | data={module}", extra={"dev_only": True}
            )

            if module_type == "specified_text":
                text = module.get("text", "")
                logger.debug(f"[PreviewGen] SpecifiedText: '{text}'", extra={"dev_only": True})
                name_parts.append(text)

            elif module_type == "counter":
                start = module.get("start", 1)
                padding = module.get("padding", 4)
                step = module.get("step", 1)
                value = start + (index * step)
                logger.debug(
                    f"[PreviewGen] Counter: value={value}, padding={padding}",
                    extra={"dev_only": True},
                )
                name_parts.append(str(value).zfill(padding))

            elif module_type == "original_name":
                try:
                    result = OriginalNameModule.apply_from_data(module, file, index)
                    logger.debug(
                        f"[PreviewGen] OriginalName result: '{result}'", extra={"dev_only": True}
                    )
                    name_parts.append(result)
                except Exception as e:
                    logger.warning(
                        f"[PreviewGen] Exception in OriginalNameModule for {file.filename}: {e}"
                    )
                    name_parts.append("invalid")

            elif module_type == "metadata":
                # Use MetadataModule for consistency with preview engine
                try:
                    result = MetadataModule.apply_from_data(module, file, index, metadata_cache)
                    logger.debug(
                        f"[PreviewGen] Metadata result: '{result}'", extra={"dev_only": True}
                    )
                    name_parts.append(result)
                except Exception as e:
                    logger.warning(
                        f"[PreviewGen] Exception in MetadataModule for {file.filename}: {e}"
                    )
                    name_parts.append("unknown")

            elif module_type == "remove_text_from_original_name":
                # Use TextRemovalModule for text removal
                try:
                    from modules.text_removal_module import TextRemovalModule

                    result_filename = TextRemovalModule.apply_from_data(
                        module, file, index, metadata_cache
                    )
                    # Extract just the base name without extension
                    import os

                    result_basename, _ = os.path.splitext(result_filename)
                    logger.debug(
                        f"[PreviewGen] TextRemoval result: '{result_basename}'",
                        extra={"dev_only": True},
                    )
                    name_parts.append(result_basename)
                except Exception as e:
                    logger.warning(
                        f"[PreviewGen] Exception in TextRemovalModule for {file.filename}: {e}"
                    )
                    name_parts.append("error")

            else:
                logger.debug(
                    f"[PreviewGen] Invalid module type: {module_type}", extra={"dev_only": True}
                )
                name_parts.append("invalid")

        logger.debug(f"[PreviewGen] All parts before join: {name_parts}", extra={"dev_only": True})
        new_basename = "".join(name_parts)
        logger.debug(
            f"[PreviewGen] Basename before extension: '{new_basename}'", extra={"dev_only": True}
        )
        extension = file.extension or ""
        if extension and not extension.startswith("."):
            extension = "." + extension
        logger.debug(f"[PreviewGen] Extension to use: '{extension}'", extra={"dev_only": True})

        # Note: Separator transformations are handled by NameTransformModule in main_window.py
        # This preview generator only creates the base name from modules

        if extension:
            if not extension.startswith("."):
                extension = "." + extension
            new_name = f"{new_basename}{extension}"
        else:
            new_name = new_basename
        logger.debug(f"[PreviewGen] Final name: '{new_name}'", extra={"dev_only": True})

        if not is_valid_filename_text(new_name):
            logger.warning(f"[Preview] Invalid name generated: {new_name}")
            has_error = True
            tooltip = f"Invalid filename: {new_name}"
            break

        preview_pairs.append((file.filename, new_name))

    return preview_pairs, has_error, tooltip
