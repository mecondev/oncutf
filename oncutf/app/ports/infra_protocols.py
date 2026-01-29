"""Infrastructure protocols for dependency inversion.

This module defines protocols for infrastructure services, allowing
the app layer to depend on abstractions rather than concrete infra
implementations.

Author: Michael Economou
Date: 2026-01-30
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

# =============================================================================
# Database Protocols
# =============================================================================


@runtime_checkable
class DatabaseManagerProtocol(Protocol):
    """Protocol for database manager operations.

    Defines the interface for database operations without depending
    on the concrete DatabaseManager implementation.
    """

    def set_file_color(self, file_path: str, color_hex: str | None) -> bool:
        """Set color for a file."""
        ...

    def get_file_color(self, file_path: str) -> str | None:
        """Get color for a file."""
        ...

    def get_file_colors_batch(self, file_paths: list[str]) -> dict[str, str]:
        """Get colors for multiple files at once."""
        ...

    def record_rename_operation(
        self,
        operation_id: str,
        old_path: str,
        new_path: str,
        old_filename: str,
        new_filename: str,
        timestamp: str,
        modules_data: str | None = None,
        post_transform_data: str | None = None,
    ) -> bool:
        """Record a rename operation in the database."""
        ...

    def get_operation_details(self, operation_id: str) -> list[dict[str, Any]] | None:
        """Retrieve details for a specific operation ID."""
        ...

    def cleanup_orphaned_records(self) -> int:
        """Clean up orphaned records and return count of removed entries."""
        ...

    def get_database_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        ...

    def store_hash(self, file_path: str, hash_value: str, algorithm: str = "CRC32") -> bool:
        """Store hash for a file."""
        ...

    def get_hash(self, file_path: str, algorithm: str = "CRC32") -> str | None:
        """Get hash for a file."""
        ...


# =============================================================================
# Cache Protocols
# =============================================================================


@runtime_checkable
class HashCacheProtocol(Protocol):
    """Protocol for persistent hash cache operations."""

    def store_hash(self, file_path: str, hash_value: str, algorithm: str = "CRC32") -> bool:
        """Store hash for a file with database persistence."""
        ...

    def get_hash(self, file_path: str, algorithm: str = "CRC32") -> str | None:
        """Retrieve hash for a file."""
        ...

    def has_hash(self, file_path: str, algorithm: str = "CRC32") -> bool:
        """Check if hash exists for a file."""
        ...

    def invalidate_file(self, file_path: str) -> None:
        """Invalidate cache for a specific file."""
        ...

    def clear_all(self) -> None:
        """Clear all cached hashes."""
        ...

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        ...

    def get_files_with_hash_batch(
        self, file_paths: list[str], algorithm: str = "CRC32"
    ) -> set[str]:
        """Get set of files that have cached hashes.

        Args:
            file_paths: List of file paths to check
            algorithm: Hash algorithm to check (default: CRC32)

        Returns:
            Set of file paths that have cached hashes

        """
        ...


@runtime_checkable
class MetadataCacheProtocol(Protocol):
    """Protocol for persistent metadata cache operations."""

    def get_metadata(self, file_path: str) -> dict[str, Any] | None:
        """Get metadata for a file."""
        ...

    def store_metadata(
        self, file_path: str, metadata: dict[str, Any], is_extended: bool = False
    ) -> bool:
        """Store metadata for a file."""
        ...

    def has_metadata(self, file_path: str, extended: bool = False) -> bool:
        """Check if metadata exists for a file."""
        ...

    def invalidate_file(self, file_path: str) -> None:
        """Invalidate cache for a specific file."""
        ...

    def clear_all(self) -> None:
        """Clear all cached metadata."""
        ...

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        ...


# =============================================================================
# Batch Operations Protocols
# =============================================================================


@runtime_checkable
class BatchOperationsManagerProtocol(Protocol):
    """Protocol for batch operations manager."""

    def queue_operation(
        self,
        operation_type: str,
        file_path: str,
        data: Any = None,
    ) -> None:
        """Queue an operation for batch processing."""
        ...

    def flush(self) -> dict[str, Any]:
        """Flush all queued operations and return results."""
        ...

    def get_stats(self) -> dict[str, Any]:
        """Get batch operation statistics."""
        ...


# =============================================================================
# Folder Color Command Protocol
# =============================================================================


class AutoColorCommandProtocol(Protocol):
    """Protocol for auto color by folder command."""

    def execute(self) -> bool:
        """Execute auto-color operation."""
        ...

    def undo(self) -> bool:
        """Undo the auto-color operation."""
        ...

    def get_files_with_existing_colors(self) -> list[str]:
        """Get list of files that already have colors assigned."""
        ...


class AutoColorCommandFactoryProtocol(Protocol):
    """Protocol for creating auto color commands."""

    def create(
        self,
        file_items: list[Any],
        db_manager: DatabaseManagerProtocol,
        skip_existing: bool = True,
    ) -> AutoColorCommandProtocol:
        """Create an auto color command."""
        ...


# =============================================================================
# Factory Functions Protocol (for service registry)
# =============================================================================


class DatabaseManagerFactoryProtocol(Protocol):
    """Protocol for database manager factory."""

    def __call__(self) -> DatabaseManagerProtocol:
        """Create or get database manager instance."""
        ...


class HashCacheFactoryProtocol(Protocol):
    """Protocol for hash cache factory."""

    def __call__(self) -> HashCacheProtocol:
        """Create or get hash cache instance."""
        ...


class MetadataCacheFactoryProtocol(Protocol):
    """Protocol for metadata cache factory."""

    def __call__(self) -> MetadataCacheProtocol | None:
        """Create or get metadata cache instance (may return None if disabled)."""
        ...


class BatchManagerFactoryProtocol(Protocol):
    """Protocol for batch manager factory."""

    def __call__(self) -> BatchOperationsManagerProtocol:
        """Create or get batch manager instance."""
        ...
