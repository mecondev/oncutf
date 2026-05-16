"""Module: exiftool_wrapper.py.

Author: Michael Economou
Date: 2025-05-23

exiftool_wrapper.py
This module provides a lightweight ExifTool-compatible wrapper using the
Exopsis Python package for metadata extraction. It preserves the existing
wrapper API while migrating actual metadata loading to Exopsis.
"""

from __future__ import annotations

import contextlib
import threading
import time
from pathlib import Path
from typing import Any, cast

from oncutf.utils.filesystem.path_normalizer import normalize_path
from oncutf.utils.logging.logger_factory import get_cached_logger

MetadataDict = dict[str, Any]

logger = get_cached_logger(__name__)


class ExifToolWrapper:
    """ExifTool-compatible wrapper using Exopsis for metadata extraction.

    This wrapper preserves the existing public API used by the application,
    while delegating metadata extraction to the Exopsis package.

    Attributes:
        lock: Thread lock for safe concurrent access.
        counter: Unique tag counter for operations.

    """

    def __init__(self) -> None:
        """Initialize the wrapper."""
        self.process = None
        self.lock = threading.Lock()
        self.counter = 0
        self._last_error: str | None = None
        self._last_health_check: float | None = None
        self._consecutive_errors: int = 0

    def __del__(self) -> None:
        """Destructor to ensure any resources are cleaned up."""
        with contextlib.suppress(Exception):
            self.close()

    @staticmethod
    def is_available() -> bool:
        """Check if Exopsis is available for metadata extraction."""
        import importlib.util

        try:
            if importlib.util.find_spec("exopsis") is None:
                logger.warning("Exopsis package not available")
                return False
        except Exception as e:
            logger.warning("Error checking Exopsis availability: %s", e)
            return False

        logger.debug("Exopsis version detected")
        return True

    def get_metadata(
        self,
        file_path: str,
        use_extended: bool = False,
        cancellation_check: Any | None = None,
    ) -> dict[str, Any]:
        """Get metadata for a single file using Exopsis."""
        try:
            return self._get_metadata_with_exiftool(file_path, use_extended, cancellation_check)
        except Exception:
            logger.exception("[ExifToolWrapper] Error getting metadata for %s", file_path)
            return {}

    def _get_metadata_with_exiftool(
        self,
        file_path: str,
        use_extended: bool = False,
        cancellation_check: Any | None = None,
    ) -> dict[str, Any]:
        """Extract metadata from a file using Exopsis."""
        logger.info(
            "[ExifToolWrapper] _get_metadata_with_exiftool: use_extended=%s for %s",
            use_extended,
            Path(file_path).name,
        )

        return self._get_metadata_fast(file_path, cancellation_check, use_extended)

    def _get_metadata_fast(
        self,
        file_path: str,
        cancellation_check: Any | None = None,
        use_extended: bool = False,
    ) -> dict[str, Any]:
        """Extract metadata from a single file via Exopsis."""
        from exopsis import extract

        file_path = normalize_path(file_path)
        if not Path(file_path).is_file():
            logger.warning("[ExifToolWrapper] File not found: %s", file_path)
            return {}

        try:
            if cancellation_check and cancellation_check():
                logger.info(
                    "[ExifToolWrapper] Metadata extraction cancelled before start: %s", file_path
                )
                return {}

            result = extract(file_path)
            metadata = cast("dict[str, Any]", result.to_dict())
            if use_extended:
                metadata["__extended__"] = True
            self._consecutive_errors = 0
        except Exception as e:
            logger.exception(
                "[ExifToolWrapper] Error extracting metadata via Exopsis for %s", file_path
            )
            self._last_error = str(e)
            self._consecutive_errors += 1
            return {}
        else:
            return metadata

    def get_metadata_batch(
        self,
        file_paths: list[str],
        use_extended: bool = False,
        cancellation_check: Any | None = None,
    ) -> list[dict[str, Any]]:
        """Load metadata for multiple files using Exopsis."""
        if not file_paths:
            return []

        results: list[dict[str, Any]] = []
        for file_path in file_paths:
            if cancellation_check and cancellation_check():
                logger.info("[ExifToolWrapper] Batch metadata extraction cancelled")
                results.extend([{} for _ in file_paths[len(results) :]])
                break
            metadata = self._get_metadata_fast(file_path, cancellation_check, use_extended)
            results.append(metadata or {})
        return results

    def _get_metadata_extended(
        self,
        file_path: str,
        cancellation_check: Any | None = None,
    ) -> dict[str, Any] | None:
        """Extract extended metadata. Exopsis handles metadata extraction directly."""
        metadata = self._get_metadata_fast(file_path, cancellation_check, use_extended=True)
        if metadata is not None:
            metadata["__extended__"] = True
        return metadata

    def write_metadata(self, file_path: str, metadata_changes: dict[str, Any]) -> bool:
        """Write metadata changes to disk.

        Writing via Exopsis is not supported by the current wrapper implementation.
        """
        logger.warning("[ExifToolWrapper] Metadata writing is not implemented for Exopsis wrapper")
        return False

    def close(
        self,
        *,
        try_graceful: bool = False,
        graceful_wait_s: float = 0.2,
        terminate_wait_s: float = 0.2,
        kill_wait_s: float = 0.1,
    ) -> None:
        """Shut down the wrapper. No-op for Exopsis."""
        del try_graceful, graceful_wait_s, terminate_wait_s, kill_wait_s
        self.process = None

    @staticmethod
    def force_cleanup_all_exiftool_processes(*args: Any, **kwargs: Any) -> int:
        """No-op cleanup for Exopsis as no external ExifTool process is spawned."""
        del args, kwargs
        logger.debug(
            "[ExifToolWrapper] force_cleanup_all_exiftool_processes called for Exopsis wrapper",
            extra={"dev_only": True},
        )
        return 0

    def is_healthy(self) -> bool:
        """Check whether the wrapper is healthy."""
        return self._consecutive_errors <= 5

    def last_error(self) -> str | None:
        """Get the last error message."""
        return self._last_error

    def health_check(self) -> dict[str, Any]:
        """Perform a lightweight health check."""
        self._last_health_check = time.time()
        return {
            "healthy": self.is_healthy(),
            "process_alive": False,
            "process_status": "exopsis-python",
            "last_error": self._last_error,
            "consecutive_errors": self._consecutive_errors,
            "last_check": self._last_health_check,
        }

    @staticmethod
    def cleanup_orphaned_processes() -> None:
        """No-op cleanup for Exopsis."""
        logger.debug(
            "[ExifToolWrapper] cleanup_orphaned_processes called for Exopsis wrapper",
            extra={"dev_only": True},
        )
