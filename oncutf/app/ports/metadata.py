"""Metadata provider ports.

Protocol interfaces for metadata extraction without infrastructure dependencies.

Author: Michael Economou
Date: 2026-01-22
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class MetadataProvider(Protocol):
    """Protocol for metadata extraction services.

    Implementations:
    - ExifToolClient (infra/external/exiftool_client.py)
    - FFmpegClient (future: infra/external/ffmpeg_client.py)
    """

    def is_available(self) -> bool:
        """Check if the metadata provider is available.

        Returns:
            True if the provider is installed and accessible
        """
        ...

    def extract_metadata(self, path: Path) -> dict[str, Any]:
        """Extract metadata from a single file.

        Args:
            path: Path to file

        Returns:
            Dictionary with metadata. Empty dict on error.
        """
        ...

    def extract_batch(self, paths: list[Path]) -> dict[str, dict[str, Any]]:
        """Extract metadata from multiple files.

        Args:
            paths: List of file paths

        Returns:
            Dict mapping path -> metadata dict
        """
        ...


class MetadataWriter(Protocol):
    """Protocol for writing metadata to files."""

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
        ...


class CacheStore(Protocol):
    """Protocol for caching metadata."""

    def get(self, key: str) -> dict[str, Any] | None:
        """Get cached metadata.

        Args:
            key: Cache key (usually file path)

        Returns:
            Cached metadata or None if not found
        """
        ...

    def set(self, key: str, value: dict[str, Any]) -> None:
        """Store metadata in cache.

        Args:
            key: Cache key
            value: Metadata to cache
        """
        ...

    def invalidate(self, key: str) -> None:
        """Invalidate cached entry.

        Args:
            key: Cache key to invalidate
        """
        ...

    def clear(self) -> None:
        """Clear all cached data."""
        ...
