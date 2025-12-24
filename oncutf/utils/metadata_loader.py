"""Module: metadata_loader.py

Author: Michael Economou
Date: 2025-05-22

Updated: 2025-05-23
This module defines the MetadataLoader class, responsible for loading media metadata
via ExifTool in the oncutf application. It supports both fast and extended scanning modes
and integrates with the application's metadata caching infrastructure.
Features:
- Uses persistent ExifTool (-stay_open True) for fast metadata extraction
- Supports extended scanning with -ee for embedded streams
- Can skip previously loaded metadata intelligently
- Thread-safe cancellation for subprocess calls
- Interoperable with MetadataEntry-based cache
"""

import subprocess
import threading

from oncutf.core.pyqt_imports import Qt
from oncutf.models.file_item import FileItem
from oncutf.utils.exiftool_wrapper import ExifToolWrapper
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataLoader:
    """Provides a unified interface for loading metadata using ExifTool.
    Supports both fast and extended scanning, with smart caching and reuse.
    """

    def __init__(self, exiftool_path: str = "exiftool") -> None:
        self.exiftool_path = exiftool_path
        self._active_proc: subprocess.Popen | None = None
        self._cancel_requested = threading.Event()
        self._lock = threading.Lock()
        self.exiftool = ExifToolWrapper()
        self.model = None

    def load(
        self, files: list[FileItem], force: bool = False, use_extended: bool = False, cache=None
    ) -> None:
        logger.debug(
            "[Loader] load() final params: use_extended=%s, force=%s",
            use_extended,
            force,
            extra={"dev_only": True},
        )
        updated_count = 0

        for file in files:
            entry = cache.get_entry(file.full_path) if cache else None
            already_has_metadata = bool(file.metadata)
            already_extended = entry.is_extended if entry else False

            logger.debug(
                "[Loader] Loading %s - already_extended=%s, already_has_metadata=%s",
                file.filename,
                already_extended,
                already_has_metadata,
                extra={"dev_only": True},
            )

            if use_extended and already_extended:
                logger.debug(
                    "[Loader] Skipping (already extended): %s",
                    file.filename,
                    extra={"dev_only": True},
                )
                continue

            if not use_extended and already_has_metadata and not force:
                logger.debug(
                    "[Loader] Skipping (already cached): %s",
                    file.filename,
                    extra={"dev_only": True},
                )
                continue

            metadata = self.read(file.full_path, use_extended=use_extended)

            # Check if metadata has the extended flag
            metadata_has_extended = (
                isinstance(metadata, dict) and metadata.get("__extended__") is True
            )

            # Determine effective extended status
            effective_extended = use_extended or metadata_has_extended

            logger.debug("[Loader] Metadata for %s:", file.filename, extra={"dev_only": True})
            logger.debug(
                "[Loader] - use_extended parameter: %s",
                use_extended,
                extra={"dev_only": True},
            )
            logger.debug(
                "[Loader] - metadata has __extended__ flag: %s",
                metadata_has_extended,
                extra={"dev_only": True},
            )
            logger.debug(
                "[Loader] - effective extended status: %s",
                effective_extended,
                extra={"dev_only": True},
            )

            file.metadata = metadata
            updated_count += 1
            if self.model:
                try:
                    row = self.model.files.index(file)
                    index = self.model.index(row, 0)
                    self.model.dataChanged.emit(index, index, [Qt.DecorationRole])  # type: ignore
                except Exception as e:
                    logger.warning(
                        "[Loader] Failed to emit dataChanged for %s: %s",
                        file.filename,
                        e,
                    )

            if cache:
                cache.set(file.full_path, metadata, is_extended=effective_extended)

            logger.debug(
                "[Loader] Read metadata for: %s | extended=%s",
                file.filename,
                effective_extended,
                extra={"dev_only": True},
            )

        logger.debug(
            "[Loader] Total updated: %d / %d",
            updated_count,
            len(files),
            extra={"dev_only": True},
        )

    def read_metadata(
        self, filepath: str, _timeout: int = 10, use_extended: bool = False
    ) -> dict[str, str] | None:
        """Reads metadata using ExifToolWrapper. Falls back to subprocess if needed.

        Args:
            filepath (str): Target file.
            timeout (int): Subprocess timeout.
            use_extended (bool): Request extended data via -ee.

        Returns:
            dict or None: Raw metadata dictionary or None on failure.

        """
        # Normalize path for Windows compatibility
        from oncutf.utils.path_normalizer import normalize_path

        filepath = normalize_path(filepath)

        logger.debug(
            "[Loader] read_metadata() called: use_extended=%s, filepath=%s",
            use_extended,
            filepath,
            extra={"dev_only": True},
        )

        if use_extended:
            logger.debug(
                "[Loader] Extended scan requested for: %s",
                filepath,
                extra={"dev_only": True},
            )
            result = self.exiftool.get_metadata(filepath, use_extended=True)
        else:
            logger.debug(
                "[Loader] Fast scan requested for: %s",
                filepath,
                extra={"dev_only": True},
            )
            result = self.exiftool.get_metadata(filepath, use_extended=False)

        if isinstance(result, dict):
            logger.debug(
                "[Loader] Result keys for %s: %s",
                filepath,
                list(result.keys())[:10],
                extra={"dev_only": True},
            )

            # Log date/time fields specifically for debugging
            date_keys = [k for k in result if "date" in k.lower() or "time" in k.lower()]
            if date_keys:
                logger.debug(
                    "[Loader] Date/Time fields found: %s",
                    date_keys,
                    extra={"dev_only": True},
                )
                for key in date_keys[:5]:  # Log first 5 date fields
                    logger.debug(
                        "[Loader] %s = %s",
                        key,
                        result[key],
                        extra={"dev_only": True},
                    )

            logger.debug(
                "[Loader] '__extended__' in result? %s",
                "__extended__" in result,
                extra={"dev_only": True},
            )

            # Annotate explicitly if this was an extended scan
            if use_extended:
                result["__extended__"] = True

            return result

        logger.warning(
            "[Loader] Read failed or returned non-dict for: %s -> type=%s",
            filepath,
            type(result),
        )
        return {}

    def read(self, filepath: str, use_extended: bool = False) -> dict[str, str]:
        return self.read_metadata(filepath, use_extended=use_extended) or {}

    def has_extended(self, file_path: str, cache) -> bool:
        entry = cache.get_entry(file_path)
        return entry.is_extended if entry else False

    def cancel_active(self) -> None:
        logger.info("[Loader] Cancel requested.")
        self._cancel_requested.set()
        with self._lock:
            if self._active_proc and self._active_proc.poll() is None:
                try:
                    self._active_proc.terminate()
                    logger.info("[Loader] Subprocess terminated.")
                except Exception as e:
                    logger.error("[Loader] Termination failed: %s", e)

    def close(self) -> None:
        if self.exiftool:
            self.exiftool.close()
            logger.info("[Loader] ExifTool closed.")
