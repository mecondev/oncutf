"""
Module: hash_manager.py

Author: Michael Economou
Date: 2025-06-10

hash_manager.py
Manages file hashing operations, duplicate detection, and file integrity checking.
Provides CRC32 hash calculations optimized for speed and efficiency.
"""
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from models.file_item import FileItem
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class HashManager:
    """
    Manages file hashing operations and duplicate detection.

    Provides functionality for:
    - CRC32 hash calculation with progress tracking
    - File and folder comparison
    - Duplicate detection in file lists
    - Hash caching for performance optimization
    """

    def __init__(self):
        """Initialize HashManager with persistent hash cache."""
        # Use persistent hash cache for better performance and persistence
        try:
            from core.persistent_hash_cache import get_persistent_hash_cache
            self._persistent_cache = get_persistent_hash_cache()
            self._use_persistent_cache = True
        except ImportError:
            # Fallback to memory-only cache if persistent cache not available
            self._hash_cache: Dict[str, str] = {}
            self._use_persistent_cache = False

    def has_cached_hash(self, file_path: Union[str, Path]) -> bool:
        """
        Check if a hash exists in cache without calculating it.

        Args:
            file_path: Path to the file to check

        Returns:
            bool: True if hash exists in cache, False otherwise
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        cache_key = str(file_path.resolve())

        if self._use_persistent_cache:
            return self._persistent_cache.has_hash(cache_key)
        else:
            return cache_key in self._hash_cache

    def get_cached_hash(self, file_path: Union[str, Path]) -> Optional[str]:
        """
        Get hash from cache without calculating it.

        Args:
            file_path: Path to the file

        Returns:
            str: Cached hash if found, None otherwise
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        cache_key = str(file_path.resolve())

        if self._use_persistent_cache:
            return self._persistent_cache.get_hash(cache_key)
        else:
            return self._hash_cache.get(cache_key)

    def calculate_hash(self, file_path: Union[str, Path], progress_callback=None) -> Optional[str]:
        """
        Calculate the CRC32 hash of a file with error handling and progress tracking.
        Checks cache first before calculating.

        Args:
            file_path: Path to the file to hash
            progress_callback: Optional callback function(bytes_processed) for progress tracking

        Returns:
            str: CRC32 hash in hexadecimal format (8 characters), or None if error occurred
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        # Check cache first (persistent or memory)
        cache_key = str(file_path.resolve())
        if self._use_persistent_cache:
            cached_hash = self._persistent_cache.get_hash(cache_key)
            if cached_hash:
                logger.debug(f"[HashManager] Cache hit for: {file_path.name}")
                return cached_hash
        else:
            if cache_key in self._hash_cache:
                logger.debug(f"[HashManager] Cache hit for: {file_path.name}")
                return self._hash_cache[cache_key]

        # Cache miss - need to calculate hash
        logger.debug(f"[HashManager] Cache miss, calculating hash for: {file_path.name}")

        try:
            if not file_path.exists():
                logger.warning(f"[HashManager] File does not exist: {file_path}")
                return None

            if not file_path.is_file():
                logger.warning(f"[HashManager] Path is not a file: {file_path}")
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
                    bytes_read = f.readinto(buffer)
                    if not bytes_read:
                        break

                    chunk_view = mv[:bytes_read]
                    crc = zlib.crc32(chunk_view, crc)

                    bytes_processed += bytes_read
                    if progress_callback:
                        progress_callback(bytes_processed)

            # Convert to unsigned 32-bit and format as hex
            hash_result = f"{crc & 0xffffffff:08x}"

            # Cache the result (persistent or memory)
            if self._use_persistent_cache:
                self._persistent_cache.store_hash(cache_key, hash_result)
            else:
                self._hash_cache[cache_key] = hash_result

            return hash_result

        except PermissionError:
            logger.error(f"[HashManager] Permission denied accessing file: {file_path}")
            return None
        except OSError as e:
            logger.error(f"[HashManager] OS error reading file {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"[HashManager] Unexpected error hashing file {file_path}: {e}")
            return None

    def compare_folders(self, folder1: Union[str, Path], folder2: Union[str, Path]) -> Dict[str, Tuple[bool, str, str]]:
        """
        Compare two folders and return file comparison results.

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
            logger.error(f"[HashManager] First folder does not exist or is not a directory: {folder1}")
            return {}

        if not folder2.exists() or not folder2.is_dir():
            logger.error(f"[HashManager] Second folder does not exist or is not a directory: {folder2}")
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
                        logger.warning(f"[HashManager] Could not hash one or both files: {file1.name}")

            logger.info(f"[HashManager] Compared {files_processed} files between folders")
            return result

        except Exception as e:
            logger.error(f"[HashManager] Error comparing folders: {e}")
            return {}

    def find_duplicates_in_list(self, file_items: List[FileItem]) -> Dict[str, List[FileItem]]:
        """
        Find duplicate files in a list of FileItem objects based on CRC32 hash.

        Args:
            file_items: List of FileItem objects to check for duplicates

        Returns:
            dict: Dictionary with hash as key and list of duplicate FileItem objects as value
        """
        if not file_items:
            return {}

        hash_to_files: Dict[str, List[FileItem]] = {}
        processed_count = 0

        logger.info(f"[HashManager] Scanning {len(file_items)} files for duplicates...")

        for file_item in file_items:
            try:
                file_hash = self.calculate_hash(file_item.full_path)
                if file_hash is not None:
                    if file_hash not in hash_to_files:
                        hash_to_files[file_hash] = []
                    hash_to_files[file_hash].append(file_item)
                    processed_count += 1
            except Exception as e:
                logger.error(f"[HashManager] Error processing file {file_item.filename}: {e}")

        # Filter to only return groups with duplicates
        duplicates = {hash_val: files for hash_val, files in hash_to_files.items() if len(files) > 1}

        duplicate_count = sum(len(files) for files in duplicates.values())
        duplicate_groups = len(duplicates)

        logger.info(f"[HashManager] Found {duplicate_count} duplicate files in {duplicate_groups} groups")

        return duplicates

    def find_duplicates_in_paths(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """
        Find duplicate files in a list of file paths based on CRC32 hash.

        Args:
            file_paths: List of file paths (strings) to check for duplicates

        Returns:
            dict: Dictionary with hash as key and list of duplicate file paths as value
        """
        if not file_paths:
            return {}

        hash_to_paths: Dict[str, List[str]] = {}
        processed_count = 0

        logger.info(f"[HashManager] Scanning {len(file_paths)} files for duplicates...")

        for file_path in file_paths:
            try:
                file_hash = self.calculate_hash(file_path)
                if file_hash is not None:
                    if file_hash not in hash_to_paths:
                        hash_to_paths[file_hash] = []
                    hash_to_paths[file_hash].append(file_path)
                    processed_count += 1
            except Exception as e:
                logger.error(f"[HashManager] Error processing file {file_path}: {e}")

        # Filter to only return groups with duplicates
        duplicates = {hash_val: paths for hash_val, paths in hash_to_paths.items() if len(paths) > 1}

        duplicate_count = sum(len(paths) for paths in duplicates.values())
        duplicate_groups = len(duplicates)

        logger.info(f"[HashManager] Found {duplicate_count} duplicate files in {duplicate_groups} groups")

        return duplicates

    def verify_file_integrity(self, file_path: Union[str, Path], expected_hash: str) -> bool:
        """
        Verify file integrity by comparing its hash with an expected hash.

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
            logger.warning(f"[HashManager] File integrity check failed: {Path(file_path).name}")

        return matches

    def get_cache_info(self) -> Dict[str, Union[str, int, float]]:
        """
        Get cache performance and size information.

        Returns:
            dict: Dictionary with cache statistics
        """
        if self._use_persistent_cache:
            # Get persistent cache stats
            persistent_stats = self._persistent_cache.get_cache_stats()
            return {
                'cache_type': 'persistent',
                'memory_entries': persistent_stats.get('memory_entries', 0),
                'cache_hits': persistent_stats.get('cache_hits', 0),
                'cache_misses': persistent_stats.get('cache_misses', 0),
                'hit_rate_percent': persistent_stats.get('hit_rate_percent', 0.0)
            }
        else:
            # Memory cache only
            return {
                'cache_type': 'memory',
                'memory_entries': len(self._hash_cache),
                'cache_hits': 0,  # Not tracked in memory-only mode
                'cache_misses': 0,  # Not tracked in memory-only mode
                'hit_rate_percent': 0.0
            }

    def clear_cache(self) -> None:
        """
        Clear hash cache (memory and/or persistent).
        """
        if self._use_persistent_cache:
            self._persistent_cache.clear_memory_cache()
            logger.info("[HashManager] Persistent cache memory cleared")
        else:
            self._hash_cache.clear()
            logger.info("[HashManager] Memory cache cleared")


# Convenience functions for simple usage
def calculate_crc32(file_path: Union[str, Path]) -> Optional[str]:
    """
    Calculate the CRC32 hash of a file (convenience function).

    Args:
        file_path: Path to the file to hash

    Returns:
        str: CRC32 hash in hexadecimal format, or None if error occurred
    """
    manager = HashManager()
    return manager.calculate_hash(file_path)


def compare_folders(folder1: Union[str, Path], folder2: Union[str, Path]) -> Dict[str, Tuple[bool, str, str]]:
    """
    Compare two folders and return file comparison results (convenience function).

    Args:
        folder1: First folder to compare
        folder2: Second folder to compare

    Returns:
        dict: Dictionary with filename as key and (is_same, hash1, hash2) as value
    """
    manager = HashManager()
    return manager.compare_folders(folder1, folder2)
