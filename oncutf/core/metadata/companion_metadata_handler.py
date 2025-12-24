"""
Module: companion_metadata_handler.py

Author: Michael Economou (refactored)
Date: 2025-12-20
Updated: 2025-12-21

Companion file metadata handler.
Extracted from unified_metadata_manager.py for better separation of concerns.

Responsibilities:
- Find companion files (XMP, sidecar) for a main file
- Extract and merge companion file metadata
- Enhance base metadata with companion data
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from oncutf.config import COMPANION_FILES_ENABLED, LOAD_COMPANION_METADATA
from oncutf.models.file_item import FileItem
from oncutf.utils.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.utils.companion_files_helper import CompanionFilesHelper

logger = get_cached_logger(__name__)


class CompanionMetadataHandler:
    """
    Handler for companion file metadata operations.

    Responsibilities:
    - Find companion files for a main file
    - Extract and merge companion file metadata
    - Enhance base metadata with companion data
    """

    def __init__(self) -> None:
        """Initialize companion metadata handler."""
        self._companion_helper: type[CompanionFilesHelper] | None = None

    @property
    def companion_helper(self) -> type[CompanionFilesHelper]:
        """Lazy-initialized CompanionFilesHelper."""
        if self._companion_helper is None:
            from oncutf.utils.companion_files_helper import CompanionFilesHelper

            self._companion_helper = CompanionFilesHelper
        return self._companion_helper

    def get_enhanced_metadata(
        self,
        file_item: FileItem,
        base_metadata: dict[str, Any] | None,
        folder_files: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """
        Get enhanced metadata that includes companion file metadata.

        Args:
            file_item: The main file item
            base_metadata: Base metadata from cache or None
            folder_files: List of all files in the same folder (for companion detection)

        Returns:
            Enhanced metadata dict including companion file data, or None if not available
        """
        if not COMPANION_FILES_ENABLED or not LOAD_COMPANION_METADATA:
            return base_metadata

        if not base_metadata:
            return None

        try:
            # If no folder files provided, get them from the file's directory
            if folder_files is None:
                folder_path = os.path.dirname(file_item.full_path)
                try:
                    folder_files = [
                        os.path.join(folder_path, f)
                        for f in os.listdir(folder_path)
                        if os.path.isfile(os.path.join(folder_path, f))
                    ]
                except OSError:
                    folder_files = []

            # Find companion files
            companions = self.companion_helper.find_companion_files(
                file_item.full_path, folder_files
            )

            if not companions:
                # No companions found, return base metadata
                return base_metadata

            # Create enhanced metadata by copying base metadata
            enhanced_metadata = base_metadata.copy()

            # Add companion metadata
            companion_metadata = {}
            for companion_path in companions:
                try:
                    companion_data = self.companion_helper.extract_companion_metadata(
                        companion_path
                    )
                    if companion_data:
                        # Prefix companion metadata to avoid conflicts
                        companion_name = os.path.basename(companion_path)
                        for key, value in companion_data.items():
                            if key != "source":  # Skip the source indicator
                                companion_key = f"Companion:{companion_name}:{key}"
                                companion_metadata[companion_key] = value

                        logger.debug(
                            "[CompanionMetadataHandler] Added companion metadata from %s with %d fields",
                            companion_name,
                            len(companion_data),
                        )
                except Exception:
                    logger.warning(
                        "[CompanionMetadataHandler] Failed to extract metadata from companion %s",
                        companion_path,
                        exc_info=True,
                    )

            # Merge companion metadata into enhanced metadata
            if companion_metadata:
                enhanced_metadata.update(companion_metadata)
                enhanced_metadata["__companion_files__"] = companions
                logger.debug(
                    "[CompanionMetadataHandler] Enhanced metadata for %s with %d companion fields",
                    file_item.filename,
                    len(companion_metadata),
                )

            return enhanced_metadata

        except Exception:
            logger.warning(
                "[CompanionMetadataHandler] Error getting enhanced metadata for %s",
                file_item.filename,
                exc_info=True,
            )
            return base_metadata

    def enhance_metadata_with_companions(
        self, file_item: FileItem, base_metadata: dict[str, Any], all_files: list[FileItem]
    ) -> dict[str, Any]:
        """
        Enhance metadata with companion file data during loading.

        Args:
            file_item: The main file being processed
            base_metadata: Base metadata from ExifTool
            all_files: All files being processed (for folder context)

        Returns:
            Enhanced metadata including companion data
        """
        if not COMPANION_FILES_ENABLED or not LOAD_COMPANION_METADATA:
            return base_metadata

        try:
            # Get folder files for companion detection
            folder_path = os.path.dirname(file_item.full_path)
            folder_files = []

            # First try to use the files being loaded (more efficient)
            if all_files:
                folder_files = [
                    f.full_path for f in all_files if os.path.dirname(f.full_path) == folder_path
                ]

            # If not enough context, scan the folder
            if len(folder_files) < 2:
                try:
                    folder_files = [
                        os.path.join(folder_path, f)
                        for f in os.listdir(folder_path)
                        if os.path.isfile(os.path.join(folder_path, f))
                    ]
                except OSError:
                    return base_metadata

            # Find companion files
            companions = self.companion_helper.find_companion_files(
                file_item.full_path, folder_files
            )

            if not companions:
                return base_metadata

            # Create enhanced metadata
            enhanced_metadata = base_metadata.copy()
            companion_metadata = {}

            # Extract metadata from companion files
            for companion_path in companions:
                try:
                    companion_data = self.companion_helper.extract_companion_metadata(
                        companion_path
                    )
                    if companion_data:
                        companion_name = os.path.basename(companion_path)
                        for key, value in companion_data.items():
                            if key != "source":
                                companion_key = f"Companion:{companion_name}:{key}"
                                companion_metadata[companion_key] = value

                        logger.debug(
                            "[CompanionMetadataHandler] Enhanced %s with companion %s",
                            file_item.filename,
                            companion_name,
                        )
                except Exception:
                    logger.warning(
                        "[CompanionMetadataHandler] Failed to extract companion metadata from %s",
                        companion_path,
                        exc_info=True,
                    )

            # Merge companion metadata
            if companion_metadata:
                enhanced_metadata.update(companion_metadata)
                enhanced_metadata["__companion_files__"] = companions
                logger.debug(
                    "[CompanionMetadataHandler] Added %d companion fields to %s",
                    len(companion_metadata),
                    file_item.filename,
                )

            return enhanced_metadata

        except Exception:
            logger.warning(
                "[CompanionMetadataHandler] Error enhancing metadata with companions for %s",
                file_item.filename,
                exc_info=True,
            )
            return base_metadata
