"""Canonical metadata client backed by Exopsis.

Consolidates all metadata interactions into a single location by wrapping
ExopsisWrapper and exposing a clean interface to the rest of the application.

Author: Michael Economou
Date: 2026-01-22
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ExopsisClient:
    """Canonical metadata client backed by Exopsis.

    Single entry point for all metadata extraction and writing in the app.

    Usage:
        client = ExopsisClient()
        if client.is_available():
            metadata = client.extract_metadata(Path("image.jpg"))
    """

    def __init__(self, use_extended: bool = False) -> None:
        """Initialize the metadata client.

        Args:
            use_extended: Request extended field set. Frame sampling is always
                         first-frame regardless of this flag.

        """
        self._use_extended = use_extended
        self._wrapper: Any = None  # Lazy init
        self._available: bool | None = None

    def _ensure_wrapper(self) -> Any:
        """Lazy-initialize and return the metadata wrapper."""
        if self._wrapper is None:
            try:
                from oncutf.infra.external.exopsis_wrapper import ExopsisWrapper

                self._wrapper = ExopsisWrapper()
                logger.debug("Metadata wrapper initialized")
            except Exception as e:
                logger.exception("Failed to initialize metadata wrapper")
                raise RuntimeError("Metadata wrapper not available") from e
        return self._wrapper

    def is_available(self) -> bool:
        """Check if Exopsis is available for metadata extraction.

        Returns:
            True if Exopsis is installed and accessible

        """
        if self._available is not None:
            return self._available

        try:
            from oncutf.infra.external.exopsis_wrapper import ExopsisWrapper

            self._available = ExopsisWrapper.is_available()
        except Exception as e:
            logger.warning("Error checking Exopsis availability: %s", e)
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
            logger.warning("Exopsis not available, cannot extract metadata")
            return {}

        try:
            wrapper = self._ensure_wrapper()
            result = wrapper.get_metadata(str(path), use_extended=self._use_extended)
        except Exception:
            logger.exception("Error extracting metadata from %s", path)
            return {}
        else:
            return result or {}

    def extract_batch(self, paths: list[Path]) -> dict[str, dict[str, Any]]:
        """Extract metadata from multiple files (batch operation).

        Args:
            paths: List of file paths

        Returns:
            Dict mapping path -> metadata dict

        """
        if not self.is_available():
            logger.warning("Exopsis not available, cannot extract batch metadata")
            return {}

        if not paths:
            return {}

        try:
            wrapper = self._ensure_wrapper()

            # Convert Path objects to strings
            path_strings = [str(p) for p in paths]

            # Use batch extraction
            results = wrapper.get_metadata_batch(path_strings, use_extended=self._use_extended)

            return {str(path): results[index] for index, path in enumerate(paths)}

        except Exception:
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
            logger.warning("Exopsis not available, cannot write metadata")
            return False

        try:
            wrapper = self._ensure_wrapper()
            del backup

            result = wrapper.write_metadata(str(path), metadata)

            if result:
                logger.debug("Successfully wrote metadata to %s", path)
            else:
                logger.warning("Failed to write metadata to %s", path)

            return bool(result)

        except Exception:
            logger.exception("Error writing metadata to %s", path)
            return False

    def close(self) -> None:
        """Close the metadata wrapper and clean up resources."""
        if self._wrapper is not None:
            try:
                self._wrapper.close()
                logger.debug("Metadata wrapper closed")
            except Exception as e:
                logger.warning("Error closing metadata wrapper: %s", e)
            finally:
                self._wrapper = None


# Global instance (singleton pattern)
_exopsis_client: ExopsisClient | None = None


def get_exopsis_client() -> ExopsisClient:
    """Get the global Exopsis client instance."""
    global _exopsis_client
    if _exopsis_client is None:
        _exopsis_client = ExopsisClient()
    return _exopsis_client


def set_exopsis_client(client: ExopsisClient) -> None:
    """Set a custom Exopsis client (useful for testing)."""
    global _exopsis_client
    _exopsis_client = client

