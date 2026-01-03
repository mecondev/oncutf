"""File hashing service implementation.

Author: Michael Economou
Date: December 18, 2025

This module provides a concrete implementation of HashServiceProtocol
for computing file hashes. It supports multiple algorithms and provides
both single-file and batch operations.

Usage:
    from oncutf.services.hash_service import HashService

    service = HashService()
    crc = service.compute_hash(Path("/path/to/file.jpg"))
    md5 = service.compute_hash(Path("/path/to/file.jpg"), algorithm="md5")
"""

from __future__ import annotations

import hashlib
import zlib
from collections.abc import Callable
from pathlib import Path

from oncutf.services.interfaces import HashServiceProtocol
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

# Supported hash algorithms
SUPPORTED_ALGORITHMS = {"crc32", "md5", "sha256", "sha1"}


class HashService:
    """File hashing service with multiple algorithm support.

    Implements HashServiceProtocol for dependency injection.
    Provides efficient hash computation with adaptive buffer sizes.

    This is a Qt-free service that can be tested in isolation.
    """

    def __init__(
        self,
        default_algorithm: str = "crc32",
        use_cache: bool = True,
    ) -> None:
        """Initialize the hash service.

        Args:
            default_algorithm: Default algorithm to use when not specified.
            use_cache: Whether to cache computed hashes.

        """
        if default_algorithm not in SUPPORTED_ALGORITHMS:
            raise ValueError(
                f"Unsupported algorithm: {default_algorithm}. " f"Supported: {SUPPORTED_ALGORITHMS}"
            )
        self._default_algorithm = default_algorithm
        self._use_cache = use_cache
        self._cache: dict[str, str] = {}

    def compute_hash(
        self,
        path: Path,
        algorithm: str = "crc32",
        progress_callback: Callable[[int], None] | None = None,
    ) -> str:
        """Compute hash of a single file.

        Args:
            path: Path to the file to hash.
            algorithm: Hash algorithm ('crc32', 'md5', 'sha256', 'sha1').
            progress_callback: Optional callback(bytes_processed) for progress.

        Returns:
            Hex string representation of the hash.
            Returns empty string on error.

        """
        if algorithm not in SUPPORTED_ALGORITHMS:
            logger.error("Unsupported hash algorithm: %s", algorithm)
            return ""

        if not path.exists():
            logger.warning("File not found: %s", path)
            return ""

        if not path.is_file():
            logger.warning("Path is not a file: %s", path)
            return ""

        # Check cache
        cache_key = f"{path}:{algorithm}"
        if self._use_cache and cache_key in self._cache:
            logger.debug("Hash cache hit for %s", path.name)
            return self._cache[cache_key]

        try:
            if algorithm == "crc32":
                result = self._compute_crc32(path, progress_callback)
            else:
                result = self._compute_hashlib(path, algorithm, progress_callback)

            # Cache result
            if self._use_cache and result:
                self._cache[cache_key] = result

            return result

        except PermissionError:
            logger.error("Permission denied accessing file: %s", path)
            return ""
        except OSError as e:
            logger.error("OS error reading file %s: %s", path, e)
            return ""
        except Exception as e:
            logger.exception("Unexpected error hashing file %s: %s", path, e)
            return ""

    def compute_hashes_batch(
        self,
        paths: list[Path],
        algorithm: str = "crc32",
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[Path, str]:
        """Compute hashes for multiple files.

        Args:
            paths: List of file paths to hash.
            algorithm: Hash algorithm to use.
            progress_callback: Optional callback(file_index, total_files).

        Returns:
            Dictionary mapping paths to their hash strings.

        """
        results: dict[Path, str] = {}
        total = len(paths)

        for i, path in enumerate(paths):
            results[path] = self.compute_hash(path, algorithm)

            if progress_callback:
                progress_callback(i + 1, total)

        return results

    def _compute_crc32(
        self,
        path: Path,
        progress_callback: Callable[[int], None] | None = None,
    ) -> str:
        """Compute CRC32 hash using zlib.

        Args:
            path: Path to the file.
            progress_callback: Optional progress callback.

        Returns:
            8-character hex string of CRC32 hash.

        """
        # Adaptive buffer sizing based on file size
        file_size = path.stat().st_size
        buffer_size = self._get_optimal_buffer_size(file_size)

        crc = 0
        buffer = bytearray(buffer_size)
        mv = memoryview(buffer)
        bytes_processed = 0

        with path.open("rb") as f:
            while True:
                bytes_read = f.readinto(buffer)
                if not bytes_read:
                    break

                chunk_view = mv[:bytes_read]
                crc = zlib.crc32(chunk_view, crc)

                bytes_processed += bytes_read
                if progress_callback:
                    progress_callback(bytes_processed)

        # Convert to unsigned 32-bit and format as 8-char hex
        return f"{crc & 0xFFFFFFFF:08x}"

    def _compute_hashlib(
        self,
        path: Path,
        algorithm: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> str:
        """Compute hash using hashlib algorithms.

        Args:
            path: Path to the file.
            algorithm: One of 'md5', 'sha256', 'sha1'.
            progress_callback: Optional progress callback.

        Returns:
            Hex digest string.

        """
        hasher = hashlib.new(algorithm)
        file_size = path.stat().st_size
        buffer_size = self._get_optimal_buffer_size(file_size)

        buffer = bytearray(buffer_size)
        mv = memoryview(buffer)
        bytes_processed = 0

        with path.open("rb") as f:
            while True:
                bytes_read = f.readinto(buffer)
                if not bytes_read:
                    break

                chunk_view = mv[:bytes_read]
                hasher.update(chunk_view)

                bytes_processed += bytes_read
                if progress_callback:
                    progress_callback(bytes_processed)

        return hasher.hexdigest()

    def _get_optimal_buffer_size(self, file_size: int) -> int:
        """Determine optimal buffer size based on file size.

        Args:
            file_size: Size of the file in bytes.

        Returns:
            Optimal buffer size in bytes.

        """
        if file_size < 64 * 1024:  # Files < 64KB
            return min(file_size, 8 * 1024)  # 8KB max for small files
        elif file_size < 10 * 1024 * 1024:  # Files < 10MB
            return 64 * 1024  # 64KB for medium files
        else:  # Large files >= 10MB
            return 256 * 1024  # 256KB for large files

    def clear_cache(self) -> None:
        """Clear the hash cache."""
        self._cache.clear()
        logger.debug("Hash cache cleared")

    def get_cache_size(self) -> int:
        """Get the number of cached hashes.

        Returns:
            Number of entries in the cache.

        """
        return len(self._cache)


# Type assertion to verify protocol compliance
def _verify_protocol_compliance() -> None:
    """Verify that HashService implements HashServiceProtocol."""
    service: HashServiceProtocol = HashService()
    _ = service  # Unused, just for type checking
