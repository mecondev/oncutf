"""
hash_manager.py

Author: Michael Economou
Date: 2025-06-21

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
    - CRC32 hash calculation with progress tracking (10x faster than SHA-256)
    - File and folder comparison
    - Duplicate detection in file lists
    - Hash caching for performance optimization

    Note: Uses CRC32 for optimal speed while maintaining sufficient accuracy
    for file comparison, duplicate detection, and undo/redo operations.
    """

    def __init__(self):
        """Initialize HashManager with empty hash cache."""
        self._hash_cache: Dict[str, str] = {}
        logger.debug("[HashManager] Initialized with CRC32 hashing", extra={"dev_only": True})

    def calculate_hash(self, file_path: Union[str, Path], progress_callback=None) -> Optional[str]:
        """
        Calculate the CRC32 hash of a file with error handling and progress tracking.

        Args:
            file_path: Path to the file to hash
            progress_callback: Optional callback function(bytes_processed) for progress tracking

        Returns:
            str: CRC32 hash in hexadecimal format (8 characters), or None if error occurred
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        # Check cache first
        cache_key = str(file_path.resolve())
        if cache_key in self._hash_cache:
            logger.debug(f"[HashManager] Using cached hash for {file_path.name}", extra={"dev_only": True})
            return self._hash_cache[cache_key]

        try:
            if not file_path.exists():
                logger.warning(f"[HashManager] File does not exist: {file_path}")
                return None

            if not file_path.is_file():
                logger.warning(f"[HashManager] Path is not a file: {file_path}")
                return None

            # Calculate CRC32 with optimized memory buffer for better performance
            crc = 0
            # Use bytearray buffer to avoid memory allocations on each read
            buffer = bytearray(262144)  # 256KB buffer for optimal performance
            mv = memoryview(buffer)     # Zero-copy view for slicing
            bytes_processed = 0

            with file_path.open("rb") as f:
                while True:
                    bytes_read = f.readinto(buffer)
                    if not bytes_read:
                        break

                    # Use memoryview slice to avoid copying data
                    chunk_view = mv[:bytes_read]
                    crc = zlib.crc32(chunk_view, crc)

                    # Update progress if callback is provided
                    bytes_processed += bytes_read
                    if progress_callback:
                        progress_callback(bytes_processed)

            # Convert to unsigned 32-bit and format as hex
            hash_result = f"{crc & 0xffffffff:08x}"

            # Cache the result
            self._hash_cache[cache_key] = hash_result

            logger.debug(f"[HashManager] Calculated CRC32 for {file_path.name}: {hash_result}", extra={"dev_only": True})
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
                 is_same: True if files are identical
                 hash1: CRC32 hash of file in folder1
                 hash2: CRC32 hash of file in folder2
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

            logger.info(f"[HashManager] Compared {files_processed} files between folders (CRC32)")
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
                 Only includes hashes that have multiple files
        """
        if not file_items:
            return {}

        hash_to_files: Dict[str, List[FileItem]] = {}
        processed_count = 0

        logger.info(f"[HashManager] Scanning {len(file_items)} files for duplicates (CRC32)...")

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

        if matches:
            logger.debug(f"[HashManager] File integrity verified: {Path(file_path).name}", extra={"dev_only": True})
        else:
            logger.warning(f"[HashManager] File integrity check failed: {Path(file_path).name}")

        return matches

    def clear_cache(self) -> None:
        """Clear the internal hash cache."""
        cache_size = len(self._hash_cache)
        self._hash_cache.clear()
        logger.debug(f"[HashManager] Cleared hash cache ({cache_size} entries)", extra={"dev_only": True})

    def get_cache_info(self) -> Dict[str, int]:
        """
        Get information about the current hash cache.

        Returns:
            dict: Dictionary with cache statistics
        """
        return {
            "cache_size": len(self._hash_cache),
            "memory_usage_approx": len(self._hash_cache) * 50  # CRC32 uses less memory than SHA-256
        }


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
