"""
persistent_hash_cache.py

Author: Michael Economou
Date: 2025-01-27

Persistent hash cache that stores file hashes in SQLite database.
Provides enhanced hash management with persistence and duplicate detection.

Features:
- Persistent storage of file hashes
- Automatic hash validation and integrity checking
- Integration with existing hash operations
- Support for multiple hash algorithms
"""

import os
from typing import Dict, List, Optional, Set

from core.database_manager import get_database_manager
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class PersistentHashCache:
    """
    Persistent hash cache with database backend.

    Stores file hashes persistently and provides enhanced functionality
    for duplicate detection and integrity checking.
    """

    def __init__(self):
        """Initialize persistent hash cache with database backend."""
        self._db_manager = get_database_manager()
        self._memory_cache: Dict[str, str] = {}  # Hot cache for performance
        self._cache_hits = 0
        self._cache_misses = 0

        logger.info("[PersistentHashCache] Initialized with database backend")

        # Migrate any existing relative paths to absolute paths
        try:
            migrated = self.migrate_relative_paths()
            if migrated > 0:
                logger.info(f"[PersistentHashCache] Migrated {migrated} paths from relative to absolute")
        except Exception as e:
            logger.warning(f"[PersistentHashCache] Path migration failed: {e}")

    def _normalize_path(self, file_path: str) -> str:
        """
        Normalize file path for consistent storage.

        Converts to absolute path and normalizes to ensure consistent
        storage and retrieval regardless of how the path was specified.
        """
        try:
            # Convert to absolute path first, then normalize
            abs_path = os.path.abspath(file_path)
            return os.path.normpath(abs_path)
        except Exception:
            # Fallback to basic normalization if abspath fails
            return os.path.normpath(file_path)

    def store_hash(self, file_path: str, hash_value: str, algorithm: str = 'CRC32') -> bool:
        """
        Store hash for a file with database persistence.

        Args:
            file_path: Path to the file
            hash_value: Calculated hash value
            algorithm: Hash algorithm used

        Returns:
            True if stored successfully
        """
        norm_path = self._normalize_path(file_path)

        # Store in memory cache for fast access
        cache_key = f"{norm_path}:{algorithm}"
        self._memory_cache[cache_key] = hash_value

        # Persist to database
        try:
            success = self._db_manager.store_hash(norm_path, hash_value, algorithm)
            if success:
                logger.debug(f"[PersistentHashCache] Stored {algorithm} hash for: {os.path.basename(file_path)}")
            return success

        except Exception as e:
            logger.error(f"[PersistentHashCache] Error storing hash for {file_path}: {e}")
            return False

    def get_hash(self, file_path: str, algorithm: str = 'CRC32') -> Optional[str]:
        """
        Retrieve hash for a file, checking memory cache first.

        Args:
            file_path: Path to the file
            algorithm: Hash algorithm

        Returns:
            Hash value or None if not found
        """
        norm_path = self._normalize_path(file_path)
        cache_key = f"{norm_path}:{algorithm}"

        # Check memory cache first
        if cache_key in self._memory_cache:
            self._cache_hits += 1
            return self._memory_cache[cache_key]

        # Load from database
        self._cache_misses += 1
        try:
            hash_value = self._db_manager.get_hash(norm_path, algorithm)
            if hash_value:
                # Cache it for future access
                self._memory_cache[cache_key] = hash_value
                return hash_value

        except Exception as e:
            logger.error(f"[PersistentHashCache] Error loading hash for {file_path}: {e}")

        return None

    def has_hash(self, file_path: str, algorithm: str = 'CRC32') -> bool:
        """
        Check if hash exists for a file.

        Args:
            file_path: Path to the file
            algorithm: Hash algorithm

        Returns:
            True if hash exists
        """
        norm_path = self._normalize_path(file_path)
        cache_key = f"{norm_path}:{algorithm}"

        # Check memory cache first
        if cache_key in self._memory_cache:
            return True

        # Check database
        try:
            return self._db_manager.has_hash(norm_path, algorithm)
        except Exception as e:
            logger.error(f"[PersistentHashCache] Error checking hash for {file_path}: {e}")
            return False

    def remove_hash(self, file_path: str) -> bool:
        """
        Remove hash for a file from both cache and database.

        Args:
            file_path: Path to the file

        Returns:
            True if removed successfully
        """
        norm_path = self._normalize_path(file_path)

        # Remove from memory cache (all algorithms)
        keys_to_remove = [key for key in self._memory_cache.keys() if key.startswith(f"{norm_path}:")]
        for key in keys_to_remove:
            self._memory_cache.pop(key, None)

        # Remove from database
        try:
            return self._db_manager.remove_file(norm_path)
        except Exception as e:
            logger.error(f"[PersistentHashCache] Error removing hash for {file_path}: {e}")
            return False

    def find_duplicates(self, file_paths: List[str], algorithm: str = 'CRC32') -> Dict[str, List[str]]:
        """
        Find duplicate files based on stored hashes.

        Args:
            file_paths: List of file paths to check
            algorithm: Hash algorithm to use

        Returns:
            Dictionary with hash as key and list of duplicate file paths as value
        """
        hash_to_paths: Dict[str, List[str]] = {}

        for file_path in file_paths:
            hash_value = self.get_hash(file_path, algorithm)
            if hash_value:
                if hash_value not in hash_to_paths:
                    hash_to_paths[hash_value] = []
                hash_to_paths[hash_value].append(file_path)

        # Filter to only return groups with duplicates
        duplicates = {hash_val: paths for hash_val, paths in hash_to_paths.items() if len(paths) > 1}

        logger.info(f"[PersistentHashCache] Found {len(duplicates)} duplicate groups from {len(file_paths)} files")
        return duplicates

    def verify_file_integrity(self, file_path: str, algorithm: str = 'CRC32') -> Optional[bool]:
        """
        Verify file integrity by comparing current hash with stored hash.

        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use

        Returns:
            True if hashes match, False if they don't, None if no stored hash
        """
        stored_hash = self.get_hash(file_path, algorithm)
        if not stored_hash:
            return None

        # Calculate current hash
        try:
            from core.hash_manager import HashManager
            hash_manager = HashManager()
            current_hash = hash_manager.calculate_hash(file_path)

            if current_hash:
                matches = current_hash.lower() == stored_hash.lower()
                if not matches:
                    logger.warning(f"[PersistentHashCache] File integrity check failed: {os.path.basename(file_path)}")
                return matches

        except Exception as e:
            logger.error(f"[PersistentHashCache] Error verifying integrity for {file_path}: {e}")

        return False

    def get_files_with_hash(self, hash_value: str, algorithm: str = 'CRC32') -> List[str]:
        """
        Get all files that have a specific hash value.

        Args:
            hash_value: Hash value to search for
            algorithm: Hash algorithm

        Returns:
            List of file paths with the given hash
        """
        # This would require a database query - implement if needed
        # For now, we can search through memory cache
        matching_files = []

        for cache_key, cached_hash in self._memory_cache.items():
            if cached_hash.lower() == hash_value.lower() and cache_key.endswith(f":{algorithm}"):
                file_path = cache_key.rsplit(':', 1)[0]
                matching_files.append(file_path)

        return matching_files

    def clear_memory_cache(self):
        """Clear the memory cache (database remains intact)."""
        self._memory_cache.clear()
        logger.info("[PersistentHashCache] Memory cache cleared")

    def get_cache_stats(self) -> dict:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            'memory_cache_size': len(self._memory_cache),
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate_percent': round(hit_rate, 2),
            'database_stats': self._db_manager.get_database_stats()
        }

    def migrate_relative_paths(self) -> int:
        """
        Migrate existing relative paths to absolute paths in the database.

        This is needed when upgrading from the old normalization method
        that only used os.path.normpath() to the new method that uses
        absolute paths.

        Returns:
            int: Number of records migrated
        """
        migrated_count = 0

        try:
            with self._db_manager._get_connection() as conn:
                cursor = conn.cursor()

                # Get all file paths from the database
                cursor.execute("""
                    SELECT DISTINCT f.file_path, f.id
                    FROM files f
                    JOIN hashes h ON f.id = h.file_id
                    WHERE f.file_path NOT LIKE '/%'  -- Not already absolute (Unix)
                    AND f.file_path NOT LIKE '_:/%'  -- Not already absolute (Windows)
                """)

                relative_paths = cursor.fetchall()

                for row in relative_paths:
                    old_path = row['file_path']
                    file_id = row['id']

                    # Try to convert to absolute path
                    try:
                        new_path = os.path.abspath(old_path)
                        new_path = os.path.normpath(new_path)

                        # Only update if the path actually changed
                        if old_path != new_path:
                            # Check if the file actually exists at the new path
                            if os.path.exists(new_path):
                                cursor.execute("""
                                    UPDATE files
                                    SET file_path = ?
                                    WHERE id = ?
                                """, (new_path, file_id))

                                migrated_count += 1
                                logger.debug(f"[PersistentHashCache] Migrated path: {old_path} -> {new_path}")

                    except Exception as e:
                        logger.warning(f"[PersistentHashCache] Could not migrate path {old_path}: {e}")
                        continue

                logger.info(f"[PersistentHashCache] Migrated {migrated_count} relative paths to absolute paths")

        except Exception as e:
            logger.error(f"[PersistentHashCache] Error during path migration: {e}")

        return migrated_count

    def cleanup_orphaned_records(self) -> int:
        """
        Clean up database records for files that no longer exist.

        Returns:
            Number of records cleaned up
        """
        try:
            cleaned_count = self._db_manager.cleanup_orphaned_records()

            # Also clean memory cache
            orphaned_keys = []
            for cache_key in self._memory_cache:
                file_path = cache_key.rsplit(':', 1)[0]
                if not os.path.exists(file_path):
                    orphaned_keys.append(cache_key)

            for key in orphaned_keys:
                self._memory_cache.pop(key, None)

            if orphaned_keys:
                logger.info(f"[PersistentHashCache] Cleaned {len(orphaned_keys)} orphaned entries from memory cache")

            return cleaned_count

        except Exception as e:
            logger.error(f"[PersistentHashCache] Error during cleanup: {e}")
            return 0

    # Legacy compatibility methods (only keep what's actually used)
    def get(self, file_path: str) -> Optional[str]:
        """Legacy method for backward compatibility."""
        return self.get_hash(file_path, 'CRC32')

    def __contains__(self, file_path: str) -> bool:
        """Support for 'in' operator."""
        return self.has_hash(file_path, 'CRC32')


# Global instance for easy access
_persistent_hash_cache: Optional[PersistentHashCache] = None


def get_persistent_hash_cache() -> PersistentHashCache:
    """Get global PersistentHashCache instance."""
    global _persistent_hash_cache
    if _persistent_hash_cache is None:
        _persistent_hash_cache = PersistentHashCache()
    return _persistent_hash_cache
