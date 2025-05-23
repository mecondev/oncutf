"""
Module: metadata_reader.py

Author: Michael Economou
Date: 2025-05-22 (refactored with ExifToolWrapper support)

This module defines the MetadataReader class, responsible for extracting metadata
from media files using the external tool `exiftool`.

Key Features:
- Uses a persistent `-stay_open True` exiftool process for fast metadata extraction.
- Supports optional extended scan using `-ee` via subprocess.
- Integrates with threaded environments (e.g. PyQt5) and supports cancellation.
- Provides unified metadata interface with automatic JSON parsing.

This module assumes `exiftool` is installed and available in the system PATH.
"""

import subprocess
import json
import threading
import time
from typing import Optional, Dict
from models.file_item import FileItem
from utils.metadata_cache import MetadataCache
from utils.exiftool_wrapper import ExifToolWrapper

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)


class MetadataLoader:
    """
    Provides a unified interface for reading file metadata using ExifTool.

    It uses a persistent `ExifToolWrapper` for fast repeated access to media file metadata.
    For complex cases requiring embedded stream analysis, it can fall back to a subprocess
    using `-ee`.

    Attributes:
        exiftool_path (str): Path to the exiftool executable.
        exiftool (ExifToolWrapper): Persistent interface to exiftool.
    """

    def __init__(self, exiftool_path: str = "exiftool") -> None:
        """
        Initializes the metadata reader and persistent exiftool interface.

        Args:
            exiftool_path (str): Optional path to the exiftool binary (default: "exiftool").
        """
        self.exiftool_path = exiftool_path
        self._active_proc: Optional[subprocess.Popen] = None
        self._cancel_requested = threading.Event()
        self._lock = threading.Lock()
        self.exiftool = ExifToolWrapper()

    def load(
        self,
        files: list[FileItem],
        force: bool = False,
        use_extended: bool = False,
        cache: Optional[MetadataCache] = None
    ) -> None:
        """
        Loads metadata for a list of FileItems and updates their .metadata attribute.

        Smart loading rules:
        - If metadata is already extended, skip.
        - If metadata is fast and user requests extended, reload.
        - If metadata is fast and user requests fast:
            - Skip if force=False
            - Reload if force=True
        - If no metadata exists, always load.

        Args:
            files (list[FileItem]): Files to process.
            force (bool): If True, always reload unless already extended.
            use_extended (bool): If True, request extended metadata via `-ee`.
            cache (MetadataCache): Optional cache to update with loaded results.
        """
        updated_count = 0

        for file in files:
            already_has_metadata = bool(file.metadata)
            already_extended = file.metadata.get("__extended__") if already_has_metadata else False

            if use_extended and already_extended:
                logger.debug(f"[MetadataLoader] Skipping (already extended): {file.filename}")
                continue

            if not use_extended and already_has_metadata and not force:
                logger.debug(f"[MetadataLoader] Skipping (already fast): {file.filename}")
                continue

            # Load metadata now (upgrade or forced or new)
            data = self.read(file.full_path, use_extended=use_extended)
            file.metadata = data

            # Ensure flag is preserved in file object
            if use_extended and isinstance(file.metadata, dict):
                file.metadata["__extended__"] = True

            updated_count += 1

            if cache is not None:
                cache.set(file.full_path, data)

            logger.debug(f"[MetadataLoader] Metadata loaded for: {file.filename} | extended={use_extended}")

        logger.info(
            f"[MetadataLoader] Loaded metadata for {updated_count} out of {len(files)} file(s), extended={use_extended}, force={force}"
        )

    def read_metadata(
        self,
        filepath: str,
        timeout: int = 10,
        use_extended: bool = False
    ) -> Optional[Dict[str, str]]:
        """
        Reads metadata from a file using either the persistent wrapper or subprocess.

        Args:
            filepath (str): Full path to the file.
            timeout (int): Timeout in seconds (used only for subprocess fallback).
            use_extended (bool): If True, performs a deep scan using `-ee`.

        Returns:
            dict or None: Parsed metadata dictionary, or None on error.
        """
        if use_extended:
            logger.warning(f"[Reader] Extended metadata requested for: {filepath}")

            result = self.exiftool.get_metadata(filepath, use_extended=True)
            if result is not None and isinstance(result, dict):
                result["__extended__"] = True

            return result

        logger.debug(f"[Reader] Fast metadata read for: {filepath}")
        return self.exiftool.get_metadata(filepath)

    def read(self, filepath: str, use_extended: bool = False) -> Dict[str, str]:
        """
        Simple wrapper for metadata reading. Returns empty dict on failure.

        Args:
            filepath (str): Path to file.
            use_extended (bool): Use extended mode (slow `-ee` scan).

        Returns:
            dict: Metadata dictionary or empty if failed.
        """
        return self.read_metadata(filepath, use_extended=use_extended) or {}

    def cancel_active(self) -> None:
        """
        Cancels the currently running extended subprocess (if any).

        This does not affect the persistent ExifToolWrapper reads,
        which are fast and atomic.
        """
        logger.warning("[MetadataReader] cancel_active() CALLED")
        self._cancel_requested.set()
        with self._lock:
            if self._active_proc and self._active_proc.poll() is None:
                try:
                    self._active_proc.terminate()
                    logger.warning("[MetadataReader] Terminated active subprocess.")
                except Exception as e:
                    logger.warning(f"[MetadataReader] Failed to terminate: {e}")

    def close(self) -> None:
        """
        Cleanly shuts down the persistent ExifToolWrapper process.

        Should be called when the application exits.
        """
        if self.exiftool:
            self.exiftool.close()
            logger.info("[MetadataReader] ExifToolWrapper closed.")
