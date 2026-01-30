"""Module: hash_manager.py.

Author: Michael Economou
Date: 2025-06-10

Primary hash manager for the application. Manages file hashing operations,
duplicate detection, and file integrity checking with persistent caching.

NOTE: This is the main hash implementation used throughout the application.
For DI-compatible interface, see HashServiceProtocol in services/interfaces.py.
"""

import zlib
from collections.abc import Callable
from pathlib import Path

from oncutf.models.file_item import FileItem
from oncutf.utils.filesystem.path_normalizer import normalize_path
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class HashManager:
    """Manages file hashing operations and duplicate detection.

    Provides functionality for:
    - CRC32 hash calculation with progress tracking
    - File and folder comparison
    - Duplicate detection in file lists
    - Hash caching for performance optimization
    """

    def __init__(self) -> None:
        """Initialize HashManager with persistent hash cache."""
        # Use persistent hash cache for better performance and persistence
        try:
            from oncutf.infra.cache.persistent_hash_cache import (
                get_persistent_hash_cache,
            )

            self._persistent_cache = get_persistent_hash_cache()
            self._use_persistent_cache = True
        except ImportError:
            # Fallback to memory-only cache if persistent cache not available
            self._hash_cache: dict[str, str] = {}
            self._use_persistent_cache = False

    def has_cached_hash(self, file_path: str | Path) -> bool:
        """Check if a hash exists in cache without calculating it.

        Args:
            file_path: Path to the file to check

        Returns:
            bool: True if hash exists in cache, False otherwise

        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        # Use central path normalization
        cache_key = normalize_path(file_path)

        if self._use_persistent_cache:
            return self._persistent_cache.has_hash(cache_key)
        else:
            return cache_key in self._hash_cache

    def get_cached_hash(self, file_path: str | Path) -> str | None:
        """Get hash from cache without calculating it.

        Args:
            file_path: Path to the file

        Returns:
            str: Cached hash if found, None otherwise

        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        # Use central path normalization
        cache_key = normalize_path(file_path)

        if self._use_persistent_cache:
            return self._persistent_cache.get_hash(cache_key)
        else:
            return self._hash_cache.get(cache_key)

    def calculate_hash(
        self,
        file_path: str | Path,
        progress_callback: Callable[[int], None] | None = None,
        cancellation_check: Callable[[], bool] | None = None,
    ) -> str | None:
        """Calculate the CRC32 hash of a file with error handling and progress tracking.
        Checks cache first before calculating.

        Args:
            file_path: Path to the file to hash
            progress_callback: Optional callback function(bytes_processed) for progress tracking
            cancellation_check: Optional callback to check if operation should be cancelled

        Returns:
            str: CRC32 hash in hexadecimal format (8 characters), or None if error occurred

        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        # Check cache first (persistent or memory)
        cache_key = normalize_path(file_path)
        if self._use_persistent_cache:
            cached_hash = self._persistent_cache.get_hash(cache_key)
            if cached_hash:
                logger.debug("[HashManager] Cache hit for: %s", file_path.name)
                return cached_hash
        elif cache_key in self._hash_cache:
            logger.debug("[HashManager] Cache hit for: %s", file_path.name)
            return self._hash_cache[cache_key]

        # Cache miss - need to calculate hash
        logger.debug("[HashManager] Cache miss, calculating hash for: %s", file_path.name)

        try:
            if not file_path.exists():
                logger.warning("[HashManager] File does not exist: %s", file_path)
                return None

            if not file_path.is_file():
                logger.warning("[HashManager] Path is not a file: %s", file_path)
                return None

            # Adaptive buffer sizing based on file size
            file_size = file_path.stat().st_size
            if file_size < 64 * 1024:  # Files < 64KB
                buffer_size = min(file_size, 8 * 1024)  # 8KB max for small files
            elif file_size < 10 * 1024 * 1024:  # Files < 10MB
                buffer_size = 64 * 1024  # 64KB for medium files
            else:  # Large files >= 10MB
                buffer_size = 256 * 1024  # 256KB for large files

            # Calculate CRC32 with optimized memory buffer
            crc = 0
            buffer = bytearray(buffer_size)
            mv = memoryview(buffer)
            bytes_processed = 0

            with file_path.open("rb") as f:
                while True:
                    # Check for cancellation
                    if cancellation_check and cancellation_check():
                        logger.debug(
                            "[HashManager] Hash calculation cancelled for: %s",
                            file_path.name,
                        )
                        return None

                    bytes_read = f.readinto(buffer)
                    if not bytes_read:
                        break

                    chunk_view = mv[:bytes_read]
                    crc = zlib.crc32(chunk_view, crc)

                    bytes_processed += bytes_read
                    if progress_callback:
                        progress_callback(bytes_processed)

            # Convert to unsigned 32-bit and format as hex
            hash_result = f"{crc & 0xFFFFFFFF:08x}"

            # Cache the result (persistent or memory)
            if self._use_persistent_cache:
                self._persistent_cache.store_hash(cache_key, hash_result)
            else:
                self._hash_cache[cache_key] = hash_result

            return hash_result

        except PermissionError:
            logger.error("[HashManager] Permission denied accessing file: %s", file_path)
            return None
        except OSError as e:
            logger.error("[HashManager] OS error reading file %s: %s", file_path, e)
            return None
        except Exception as e:
            logger.error("[HashManager] Unexpected error hashing file %s: %s", file_path, e)
            return None

    def compare_folders(
        self, folder1: str | Path, folder2: str | Path
    ) -> dict[str, tuple[bool, str, str]]:
        """Compare two folders and return file comparison results.

        Args:
            folder1: First folder to compare
            folder2: Second folder to compare

        Returns:
            dict: Dictionary with filename as key and (is_same, hash1, hash2) as value

        """
        if isinstance(folder1, str):
            folder1 = Path(folder1)
        if isinstance(folder2, str):
            folder2 = Path(folder2)

        if not folder1.exists() or not folder1.is_dir():
            logger.error(
                "[HashManager] First folder does not exist or is not a directory: %s",
                folder1,
            )
            return {}

        if not folder2.exists() or not folder2.is_dir():
            logger.error(
                "[HashManager] Second folder does not exist or is not a directory: %s",
                folder2,
            )
            return {}

        result = {}
        files_processed = 0

        try:
            for file1 in folder1.glob("*"):
                if not file1.is_file():
                    continue

                file2 = folder2 / file1.name
                if file2.exists() and file2.is_file():
                    hash1 = self.calculate_hash(file1)
                    hash2 = self.calculate_hash(file2)

                    if hash1 is not None and hash2 is not None:
                        result[file1.name] = (hash1 == hash2, hash1, hash2)
                        files_processed += 1
                    else:
                        logger.warning(
                            "[HashManager] Could not hash one or both files: %s",
                            file1.name,
                        )

            logger.info("[HashManager] Compared %d files between folders", files_processed)
            return result

        except Exception as e:
            logger.error("[HashManager] Error comparing folders: %s", e)
            return {}

    def find_duplicates_in_list(self, file_items: list[FileItem]) -> dict[str, list[FileItem]]:
        """Find duplicate files in a list of FileItem objects based on CRC32 hash.

        Args:
            file_items: List of FileItem objects to check for duplicates

        Returns:
            dict: Dictionary with hash as key and list of duplicate FileItem objects as value

        """
        if not file_items:
            return {}

        hash_to_files: dict[str, list[FileItem]] = {}
        processed_count = 0

        logger.info("[HashManager] Scanning %d files for duplicates...", len(file_items))

        for file_item in file_items:
            try:
                file_hash = self.calculate_hash(file_item.full_path)
                if file_hash is not None:
                    if file_hash not in hash_to_files:
                        hash_to_files[file_hash] = []
                    hash_to_files[file_hash].append(file_item)
                    processed_count += 1
            except Exception as e:
                logger.error("[HashManager] Error processing file %s: %s", file_item.filename, e)

        # Filter to only return groups with duplicates
        duplicates = {
            hash_val: files for hash_val, files in hash_to_files.items() if len(files) > 1
        }

        duplicate_count = sum(len(files) for files in duplicates.values())
        duplicate_groups = len(duplicates)

        logger.info(
            "[HashManager] Found %d duplicate files in %d groups",
            duplicate_count,
            duplicate_groups,
        )

        return duplicates

    def find_duplicates_in_paths(self, file_paths: list[str]) -> dict[str, list[str]]:
        """Find duplicate files in a list of file paths based on CRC32 hash.

        Args:
            file_paths: List of file paths (strings) to check for duplicates

        Returns:
            dict: Dictionary with hash as key and list of duplicate file paths as value

        """
        if not file_paths:
            return {}

        hash_to_paths: dict[str, list[str]] = {}
        processed_count = 0

        logger.info("[HashManager] Scanning %d files for duplicates...", len(file_paths))

        for file_path in file_paths:
            try:
                file_hash = self.calculate_hash(file_path)
                if file_hash is not None:
                    if file_hash not in hash_to_paths:
                        hash_to_paths[file_hash] = []
                    hash_to_paths[file_hash].append(file_path)
                    processed_count += 1
            except Exception as e:
                logger.error("[HashManager] Error processing file %s: %s", file_path, e)

        # Filter to only return groups with duplicates
        duplicates = {
            hash_val: paths for hash_val, paths in hash_to_paths.items() if len(paths) > 1
        }

        duplicate_count = sum(len(paths) for paths in duplicates.values())
        duplicate_groups = len(duplicates)

        logger.info(
            "[HashManager] Found %d duplicate files in %d groups",
            duplicate_count,
            duplicate_groups,
        )

        return duplicates

    def verify_file_integrity(self, file_path: str | Path, expected_hash: str) -> bool:
        """Verify file integrity by comparing its hash with an expected hash.

        Args:
            file_path: Path to the file to verify
            expected_hash: Expected CRC32 hash in hexadecimal format

        Returns:
            bool: True if file hash matches expected hash, False otherwise

        """
        actual_hash = self.calculate_hash(file_path)
        if actual_hash is None:
            return False

        matches = actual_hash.lower() == expected_hash.lower()

        if not matches:
            logger.warning("[HashManager] File integrity check failed: %s", Path(file_path).name)

        return matches

    def get_cache_info(self) -> dict[str, str | int | float]:
        """Get cache performance and size information.

        Returns:
            dict: Dictionary with cache statistics

        """
        if self._use_persistent_cache:
            # Get persistent cache stats
            persistent_stats = self._persistent_cache.get_cache_stats()
            return {
                "cache_type": "persistent",
                "memory_entries": persistent_stats.get("memory_entries", 0),
                "cache_hits": persistent_stats.get("cache_hits", 0),
                "cache_misses": persistent_stats.get("cache_misses", 0),
                "hit_rate_percent": persistent_stats.get("hit_rate_percent", 0.0),
            }
        else:
            # Memory cache only
            return {
                "cache_type": "memory",
                "memory_entries": len(self._hash_cache),
                "cache_hits": 0,  # Not tracked in memory-only mode
                "cache_misses": 0,  # Not tracked in memory-only mode
                "hit_rate_percent": 0.0,
            }

    def clear_cache(self) -> None:
        """Clear hash cache (memory and/or persistent)."""
        if self._use_persistent_cache:
            self._persistent_cache.clear_memory_cache()
            logger.info("[HashManager] Persistent cache memory cleared")
        else:
            self._hash_cache.clear()
            logger.info("[HashManager] Memory cache cleared")


# Convenience functions for simple usage
def calculate_crc32(file_path: str | Path) -> str | None:
    """Calculate the CRC32 hash of a file (convenience function).

    Args:
        file_path: Path to the file to hash

    Returns:
        str: CRC32 hash in hexadecimal format, or None if error occurred

    """
    manager = HashManager()
    return manager.calculate_hash(file_path)


def compare_folders(folder1: str | Path, folder2: str | Path) -> dict[str, tuple[bool, str, str]]:
    """Compare two folders and return file comparison results (convenience function).

    Args:
        folder1: First folder to compare
        folder2: Second folder to compare

    Returns:
        dict: Dictionary with filename as key and (is_same, hash1, hash2) as value

    """
    manager = HashManager()
    return manager.compare_folders(folder1, folder2)
