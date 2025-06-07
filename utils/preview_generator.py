"""
preview_generator.py

This module provides functions to generate preview names for file renaming
based on user-defined modules. It supports modular rename logic and allows
integration with metadata.

Author: Michael Economou
Date: 2025-05-13
"""

from typing import Any, Dict, List, Optional, Tuple

from models.file_item import FileItem
from modules.metadata_module import MetadataModule
from utils.logger_helper import get_logger
from utils.validation import is_valid_filename_text

logger = get_logger(__name__)


def generate_preview_names(
    files: List[FileItem],
    modules_data: List[Dict[str, Any]],
    metadata_cache: Optional[Dict[str, Dict[str, Any]]] = None
) -> Tuple[List[Tuple[str, str]], bool, str]:
    """
    Generate new filenames based on rename modules for a list of files.

    Parameters
    ----------
    files : List[FileItem]
        The list of files to rename.
    modules_data : List[Dict[str, Any]]
        The list of rename modules in serialized form.
    metadata : Optional[Dict[str, Dict[str, Any]]]
        Cached metadata for the files (optional).

    Returns
    -------
    Tuple[List[Tuple[str, str]], bool, str]
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
        logger.debug(f"[PreviewGen] Start: file='{file.filename}', extension='{file.extension}'")
        for module in modules_data:
            module_type = module.get("type")
            logger.debug(f"[PreviewGen] Module: {module_type} | data={module}")

            if module_type == "specified_text":
                text = module.get("text", "")
                logger.debug(f"[PreviewGen] SpecifiedText: '{text}'")
                name_parts.append(text)

            elif module_type == "counter":
                start = module.get("start", 1)
                padding = module.get("padding", 4)
                step = module.get("step", 1)
                value = start + (index * step)
                logger.debug(f"[PreviewGen] Counter: value={value}, padding={padding}")
                name_parts.append(str(value).zfill(padding))

            elif module_type == "metadata":
                # Use MetadataModule for consistency with preview engine
                try:
                    result = MetadataModule.apply_from_data(module, file, index, metadata_cache)
                    logger.debug(f"[PreviewGen] Metadata result: '{result}'")
                    name_parts.append(result)
                except Exception as e:
                    logger.warning(f"[PreviewGen] Exception in MetadataModule for {file.filename}: {e}")
                    name_parts.append("unknown")

            else:
                logger.debug(f"[PreviewGen] Invalid module type: {module_type}")
                name_parts.append("invalid")

        logger.debug(f"[PreviewGen] All parts before join: {name_parts}")
        new_basename = "".join(name_parts)
        logger.debug(f"[PreviewGen] Basename before extension: '{new_basename}'")
        extension = file.extension or ""
        if extension and not extension.startswith("."):
            extension = "." + extension
        logger.debug(f"[PreviewGen] Extension to use: '{extension}'")

        # Note: Separator transformations are handled by NameTransformModule in main_window.py
        # This preview generator only creates the base name from modules

        if extension:
            if not extension.startswith("."):
                extension = "." + extension
            new_name = f"{new_basename}{extension}"
        else:
            new_name = new_basename
        logger.debug(f"[PreviewGen] Final name: '{new_name}'")

        if not is_valid_filename_text(new_name):
            logger.warning(f"[Preview] Invalid name generated: {new_name}")
            has_error = True
            tooltip = f"Invalid filename: {new_name}"
            break

        preview_pairs.append((file.filename, new_name))

    return preview_pairs, has_error, tooltip
