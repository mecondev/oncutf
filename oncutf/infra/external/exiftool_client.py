"""ExifTool client - canonical ExifTool interaction.

This module consolidates all ExifTool interactions into a single location.
It wraps the ExifToolWrapper and provides a clean interface for the rest
of the application.

Replaces:
- oncutf/utils/metadata/exiftool_adapter.py
- oncutf/services/exiftool_service.py (partially)
- Direct ExifToolWrapper usage

Author: Michael Economou
Date: 2026-01-22
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ExifToolClient:
    """Canonical ExifTool client for metadata operations.

    This is the SINGLE SOURCE OF TRUTH for ExifTool interactions.
    All metadata extraction/writing should go through this class.

    Features:
    - Persistent process via ExifToolWrapper
    - Thread-safe operations
    - Batch metadata extraction
    - Metadata writing
    - Health monitoring

    Usage:
        client = ExifToolClient()
        if client.is_available():
            metadata = client.extract_metadata(Path("image.jpg"))
    """

    def __init__(self, use_extended: bool = False) -> None:
        """Initialize ExifTool client.

        Args:
            use_extended: Use extended metadata extraction (-ee flag).
                         Slower but extracts embedded metadata.

        """
        self._use_extended = use_extended
        self._wrapper: Any = None  # Lazy init
        self._available: bool | None = None

    def _ensure_wrapper(self) -> Any:
        """Lazy initialization of ExifToolWrapper."""
        if self._wrapper is None:
            try:
                from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper

                self._wrapper = ExifToolWrapper()
                logger.debug("ExifToolWrapper initialized")
            except Exception as e:
                logger.exception("Failed to initialize ExifToolWrapper")
                raise RuntimeError("ExifTool not available") from e
        return self._wrapper

    def is_available(self) -> bool:
        """Check if ExifTool is available on the system.

        Returns:
            True if ExifTool is installed and accessible

        """
        if self._available is not None:
            return self._available

        try:
            from oncutf.infra.external.exiftool_wrapper import ExifToolWrapper

            self._available = ExifToolWrapper.is_available()
        except Exception as e:
            logger.warning("Error checking ExifTool availability: %s", e)
            self._available = False

        return self._available

    def extract_metadata(self, path: Path) -> dict[str, Any]:
        """Extract metadata from a single file.

        Args:
            path: Path to file

        Returns:
            Dictionary with metadata. Empty dict on error.

        """
        if not self.is_available():
            logger.warning("ExifTool not available, cannot extract metadata")
            return {}

        try:
            wrapper = self._ensure_wrapper()
            result = wrapper.get_metadata(str(path), use_extended=self._use_extended)
        except Exception as e:
            logger.exception("Error extracting metadata from %s", path)
            return {}
        else:
            return result if result else {}

    def extract_batch(self, paths: list[Path]) -> dict[str, dict[str, Any]]:
        """Extract metadata from multiple files (batch operation).

        Args:
            paths: List of file paths

        Returns:
            Dict mapping path -> metadata dict

        """
        if not self.is_available():
            logger.warning("ExifTool not available, cannot extract batch metadata")
            return {}

        if not paths:
            return {}

        try:
            wrapper = self._ensure_wrapper()

            # Convert Path objects to strings
            path_strings = [str(p) for p in paths]

            # Use batch extraction
            results = wrapper.get_metadata_batch(path_strings, use_extended=self._use_extended)

            # Convert back to Path keys
            return {str(path): results.get(str(path), {}) for path in paths}

        except Exception as e:
            logger.exception("Error in batch metadata extraction")
            return {}

    def load_metadata(self, path: Path) -> dict[str, Any]:
        """Load metadata from a single file (MetadataServiceProtocol adapter).

        Adapter method for MetadataServiceProtocol compatibility.
        Delegates to extract_metadata().

        Args:
            path: Path to file

        Returns:
            Dictionary with metadata. Empty dict on error.

        """
        return self.extract_metadata(path)

    def load_metadata_batch(self, paths: list[Path]) -> dict[Path, dict[str, Any]]:
        """Load metadata from multiple files (MetadataServiceProtocol adapter).

        Adapter method for MetadataServiceProtocol compatibility.
        Delegates to extract_batch() and converts string keys back to Path keys.

        Args:
            paths: List of file paths

        Returns:
            Dict mapping Path -> metadata dict

        """
        results = self.extract_batch(paths)
        # Convert string keys back to Path objects
        from pathlib import Path as PathlibPath

        return {PathlibPath(k): v for k, v in results.items()}

    def write_metadata(
        self,
        path: Path,
        metadata: dict[str, Any],
        backup: bool = True,
    ) -> bool:
        """Write metadata to a file.

        Args:
            path: Path to file
            metadata: Metadata dict to write
            backup: Create backup before writing

        Returns:
            True if successful, False otherwise

        """
        if not self.is_available():
            logger.warning("ExifTool not available, cannot write metadata")
            return False

        try:
            wrapper = self._ensure_wrapper()

            # Prepare metadata for ExifTool format
            tags = {f"-{key}={value}" for key, value in metadata.items()}

            # Call wrapper's write method
            result = wrapper.write_metadata(str(path), list(tags), create_backup=backup)

            if result:
                logger.debug("Successfully wrote metadata to %s", path)
            else:
                logger.warning("Failed to write metadata to %s", path)

            return bool(result)

        except Exception as e:
            logger.exception("Error writing metadata to %s", path)
            return False

    def close(self) -> None:
        """Close the ExifTool wrapper and clean up resources."""
        if self._wrapper is not None:
            try:
                self._wrapper.close()
                logger.debug("ExifToolWrapper closed")
            except Exception as e:
                logger.warning("Error closing ExifToolWrapper: %s", e)
            finally:
                self._wrapper = None


# Global instance (singleton pattern)
_exiftool_client: ExifToolClient | None = None


def get_exiftool_client() -> ExifToolClient:
    """Get the global ExifTool client instance.

    Returns:
        Singleton ExifToolClient instance

    """
    global _exiftool_client
    if _exiftool_client is None:
        _exiftool_client = ExifToolClient()
    return _exiftool_client


def set_exiftool_client(client: ExifToolClient) -> None:
    """Set a custom ExifTool client (useful for testing).

    Args:
        client: Custom ExifToolClient instance

    """
    global _exiftool_client
    _exiftool_client = client
