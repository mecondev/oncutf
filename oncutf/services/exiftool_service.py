"""ExifTool-based metadata service implementation.

Author: Michael Economou
Date: December 18, 2025

This module provides a concrete implementation of MetadataServiceProtocol
using ExifTool for metadata extraction. It wraps the existing ExifToolWrapper
and provides a clean service interface.

Usage:
    from oncutf.services.exiftool_service import ExifToolService

    service = ExifToolService()
    metadata = service.load_metadata(Path("/path/to/image.jpg"))
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from oncutf.services.interfaces import MetadataServiceProtocol
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ExifToolService:
    """Metadata extraction service using ExifTool.

    Implements MetadataServiceProtocol for dependency injection.
    Uses ExifToolWrapper internally for actual ExifTool communication.

    This is a Qt-free service that can be tested in isolation.
    """

    def __init__(self, use_extended: bool = False) -> None:
        """Initialize the ExifTool service.

        Args:
            use_extended: Whether to use extended metadata extraction (-ee flag).
                          Extended mode is slower but extracts embedded metadata.

        """
        self._use_extended = use_extended
        self._wrapper: Any = None  # Lazy initialization
        self._available: bool | None = None

    def _ensure_wrapper(self) -> Any:
        """Lazy initialization of ExifToolWrapper."""
        if self._wrapper is None:
            try:
                from oncutf.utils.shared.exiftool_wrapper import ExifToolWrapper

                self._wrapper = ExifToolWrapper()
                logger.debug("ExifToolWrapper initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize ExifToolWrapper: %s", e)
                raise RuntimeError("ExifTool not available") from e
        return self._wrapper

    def is_available(self) -> bool:
        """Check if ExifTool is available on the system.

        Returns:
            True if ExifTool is installed and accessible.

        """
        if self._available is not None:
            return self._available

        try:
            import subprocess

            result = subprocess.run(
                ["exiftool", "-ver"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            self._available = result.returncode == 0
            if self._available:
                logger.debug("ExifTool version: %s", result.stdout.strip())
            else:
                logger.warning("ExifTool not available (returncode=%d)", result.returncode)
        except FileNotFoundError:
            logger.warning("ExifTool not found in PATH")
            self._available = False
        except Exception as e:
            logger.warning("Error checking ExifTool availability: %s", e)
            self._available = False

        return self._available

    def load_metadata(self, path: Path) -> dict[str, Any]:
        """Load metadata from a single file using ExifTool.

        Args:
            path: Path to the file to extract metadata from.

        Returns:
            Dictionary with metadata key-value pairs.
            Returns empty dict if file cannot be read or ExifTool fails.

        """
        if not self.is_available():
            logger.warning("ExifTool not available, returning empty metadata")
            return {}

        if not path.exists():
            logger.warning("File not found: %s", path)
            return {}

        if not path.is_file():
            logger.warning("Path is not a file: %s", path)
            return {}

        try:
            wrapper = self._ensure_wrapper()
            result = wrapper.get_metadata(str(path), use_extended=self._use_extended)
            return result if result else {}
        except Exception as e:
            logger.error("Error loading metadata for %s: %s", path, e)
            return {}

    def load_metadata_batch(self, paths: list[Path]) -> dict[Path, dict[str, Any]]:
        """Load metadata from multiple files efficiently.

        Args:
            paths: List of file paths to extract metadata from.

        Returns:
            Dictionary mapping paths to their metadata dicts.

        """
        if not self.is_available():
            logger.warning("ExifTool not available, returning empty batch result")
            return {path: {} for path in paths}

        results: dict[Path, dict[str, Any]] = {}

        for path in paths:
            results[path] = self.load_metadata(path)

        return results

    def close(self) -> None:
        """Close the ExifTool wrapper and release resources."""
        if self._wrapper is not None:
            try:
                self._wrapper.close()
                logger.debug("ExifToolWrapper closed")
            except Exception as e:
                logger.warning("Error closing ExifToolWrapper: %s", e)
            finally:
                self._wrapper = None


# Type assertion to verify protocol compliance
def _verify_protocol_compliance() -> None:
    """Verify that ExifToolService implements MetadataServiceProtocol."""
    service: MetadataServiceProtocol = ExifToolService()
    _ = service  # Unused, just for type checking
