"""
Service protocol definitions for oncutf application.

Author: Michael Economou
Date: December 18, 2025

This module defines Protocol classes that serve as interfaces for all external
services. Using Protocols allows for structural subtyping (duck typing with
type checking) and enables dependency injection for testability.

All protocols are runtime-checkable, meaning isinstance() works with them.

Usage:
    from oncutf.services.interfaces import MetadataServiceProtocol

    class MockMetadataService:
        def load_metadata(self, path: Path) -> dict[str, Any]:
            return {"test": "value"}

    # This works due to structural subtyping:
    service: MetadataServiceProtocol = MockMetadataService()
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "MetadataServiceProtocol",
    "HashServiceProtocol",
    "FilesystemServiceProtocol",
    "DatabaseServiceProtocol",
    "ConfigServiceProtocol",
]


@runtime_checkable
class MetadataServiceProtocol(Protocol):
    """Protocol for metadata extraction services.

    Implementations provide metadata loading from files using various backends
    (e.g., ExifTool, PIL, built-in Python libraries).
    """

    def load_metadata(self, path: Path) -> dict[str, Any]:
        """Load metadata from a single file.

        Args:
            path: Path to the file to extract metadata from.

        Returns:
            Dictionary with metadata key-value pairs.
            Returns empty dict if file cannot be read.
        """
        ...

    def load_metadata_batch(self, paths: list[Path]) -> dict[Path, dict[str, Any]]:
        """Load metadata from multiple files efficiently.

        Args:
            paths: List of file paths to extract metadata from.

        Returns:
            Dictionary mapping paths to their metadata dicts.
        """
        ...


@runtime_checkable
class HashServiceProtocol(Protocol):
    """Protocol for file hashing services.

    Implementations provide various hash algorithms (CRC32, MD5, SHA256, etc.)
    for file integrity verification and duplicate detection.
    """

    def compute_hash(self, path: Path, algorithm: str = "crc32") -> str:
        """Compute hash of a single file.

        Args:
            path: Path to the file to hash.
            algorithm: Hash algorithm ('crc32', 'md5', 'sha256').

        Returns:
            Hex string representation of the hash.
        """
        ...

    def compute_hashes_batch(self, paths: list[Path], algorithm: str = "crc32") -> dict[Path, str]:
        """Compute hashes for multiple files.

        Args:
            paths: List of file paths to hash.
            algorithm: Hash algorithm to use.

        Returns:
            Dictionary mapping paths to their hash strings.
        """
        ...


@runtime_checkable
class FilesystemServiceProtocol(Protocol):
    """Protocol for filesystem operations.

    Implementations provide file operations with proper error handling,
    atomic operations, and cross-platform compatibility.
    """

    def rename_file(self, source: Path, target: Path) -> bool:
        """Rename a file atomically.

        Args:
            source: Current file path.
            target: New file path.

        Returns:
            True if successful, False otherwise.
        """
        ...

    def file_exists(self, path: Path) -> bool:
        """Check if a file exists.

        Args:
            path: Path to check.

        Returns:
            True if file exists and is a file (not directory).
        """
        ...

    def get_file_info(self, path: Path) -> dict[str, Any]:
        """Get file information (size, dates, etc.).

        Args:
            path: Path to the file.

        Returns:
            Dictionary with file info (size, mtime, ctime, etc.).
        """
        ...


@runtime_checkable
class DatabaseServiceProtocol(Protocol):
    """Protocol for database operations.

    Implementations provide persistent storage for rename history,
    metadata caching, and application state.
    """

    def store_rename(self, source: str, target: str, timestamp: float) -> None:
        """Store a rename operation in history.

        Args:
            source: Original file path.
            target: New file path.
            timestamp: Unix timestamp of the operation.
        """
        ...

    def get_rename_history(self, path: str) -> list[dict[str, Any]]:
        """Get rename history for a file.

        Args:
            path: File path to lookup.

        Returns:
            List of rename operations involving this path.
        """
        ...


@runtime_checkable
class ConfigServiceProtocol(Protocol):
    """Protocol for configuration access.

    Implementations provide typed access to application configuration
    with defaults and persistence.
    """

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key (dot-notation supported).
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        ...

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: Configuration key.
            value: Value to set.
        """
        ...
