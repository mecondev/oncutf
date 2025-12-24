"""Module: file_validation_manager.py

Author: Michael Economou
Date: 2025-06-15

file_validation_manager.py
Advanced file validation manager with content-based identification and smart caching.
Designed for archival applications with occasional use and high probability of path changes.
Features:
- Content-based file identification (survives path changes)
- Medium accuracy validation (balanced performance)
- Smart TTL caching based on file characteristics
- Adaptive thresholds based on operation type
- Efficient batch processing for bulk operations
- User preference memory for validation choices
"""

import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from oncutf.config import EXTENDED_METADATA_SIZE_LIMIT_MB, LARGE_FOLDER_WARNING_THRESHOLD
from oncutf.core.database.database_manager import get_database_manager
from oncutf.core.hash.hash_manager import HashManager
from oncutf.utils.file_size_calculator import calculate_files_total_size
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ValidationAccuracy(Enum):
    """Validation accuracy levels"""

    LOW = "low"  # Only existence check
    MEDIUM = "medium"  # mtime + size check
    HIGH = "high"  # Full hash verification


class OperationType(Enum):
    """Types of operations for adaptive thresholds"""

    METADATA_FAST = "metadata_fast"
    METADATA_EXTENDED = "metadata_extended"
    HASH_CALCULATION = "hash_calculation"
    RENAME_OPERATION = "rename_operation"
    FILE_LOADING = "file_loading"


@dataclass
class FileSignature:
    """File signature for content-based identification"""

    content_hash: str
    file_size: int
    filename: str
    quick_signature: str  # size_filename for fast lookups

    @classmethod
    def create(cls, file_path: str, content_hash: str = None) -> "FileSignature":
        """Create file signature from path"""
        path = Path(file_path)
        size = path.stat().st_size if path.exists() else 0
        filename = path.name

        return cls(
            content_hash=content_hash or "",
            file_size=size,
            filename=filename,
            quick_signature=f"{size}_{filename}",
        )


@dataclass
class ValidationResult:
    """Result of file validation"""

    is_valid: bool
    file_exists: bool
    content_changed: bool
    path_changed: bool
    original_path: str | None = None
    confidence: float = 0.0  # 0.0 to 1.0


@dataclass
class ValidationThresholds:
    """Validation thresholds for different operations"""

    max_files: int
    max_size_mb: int
    batch_size: int
    warning_enabled: bool = True


class FileValidationManager:
    """Advanced file validation manager with content-based identification.

    Optimized for archival applications where files may be moved/renamed
    at the OS level, requiring robust content-based tracking.
    """

    def __init__(self):
        """Initialize FileValidationManager with balanced settings."""
        self.db_manager = get_database_manager()
        self.hash_manager = HashManager()

        # Validation settings (balanced approach)
        self.default_accuracy = ValidationAccuracy.MEDIUM
        self.enable_content_based_identification = True

        # Smart TTL settings (in seconds)
        self.ttl_settings = {
            # Media files (rarely change)
            "media": 7 * 24 * 3600,  # 7 days
            # Documents (change occasionally)
            "document": 24 * 3600,  # 1 day
            # Temporary files (change frequently)
            "temporary": 3600,  # 1 hour
            # Default for unknown types
            "default": 12 * 3600,  # 12 hours
        }

        # File type classifications
        self.file_types = {
            "media": {
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".bmp",
                ".tiff",
                ".webp",
                ".mp4",
                ".avi",
                ".mkv",
                ".mov",
                ".wmv",
                ".flv",
                ".webm",
                ".mp3",
                ".wav",
                ".flac",
                ".aac",
                ".ogg",
                ".m4a",
            },
            "document": {
                ".pdf",
                ".doc",
                ".docx",
                ".txt",
                ".rtf",
                ".odt",
                ".xls",
                ".xlsx",
                ".ppt",
                ".pptx",
                ".csv",
            },
            "temporary": {".tmp", ".temp", ".log", ".cache", ".bak"},
        }

        # Default thresholds for different operations
        self.default_thresholds = {
            OperationType.METADATA_FAST: ValidationThresholds(
                max_files=500, max_size_mb=100, batch_size=50
            ),
            OperationType.METADATA_EXTENDED: ValidationThresholds(
                max_files=LARGE_FOLDER_WARNING_THRESHOLD,
                max_size_mb=EXTENDED_METADATA_SIZE_LIMIT_MB,
                batch_size=20,
            ),
            OperationType.HASH_CALCULATION: ValidationThresholds(
                max_files=1000, max_size_mb=1000, batch_size=25
            ),
            OperationType.RENAME_OPERATION: ValidationThresholds(
                max_files=2000, max_size_mb=5000, batch_size=100
            ),
            OperationType.FILE_LOADING: ValidationThresholds(
                max_files=1000, max_size_mb=2000, batch_size=100
            ),
        }

        # User preferences cache
        self.user_preferences = {}

        logger.debug("[FileValidationManager] Initialized with balanced settings")

    def get_file_type_category(self, file_path: str) -> str:
        """Get file type category for TTL calculation."""
        extension = Path(file_path).suffix.lower()

        for category, extensions in self.file_types.items():
            if extension in extensions:
                return category

        return "default"

    def calculate_smart_ttl(self, file_path: str, file_size: int = None) -> int:
        """Calculate smart TTL based on file characteristics."""
        category = self.get_file_type_category(file_path)
        base_ttl = self.ttl_settings[category]

        # Adjust based on file size (larger files get longer TTL)
        if file_size and file_size > 100 * 1024 * 1024:  # >100MB
            base_ttl = int(base_ttl * 1.5)

        # Adjust based on file age (older files get longer TTL)
        try:
            file_age_days = (time.time() - os.path.getctime(file_path)) / (24 * 3600)
            if file_age_days > 365:  # Files older than 1 year
                base_ttl = int(base_ttl * 2)
        except OSError:
            pass

        return base_ttl

    def validate_file_medium_accuracy(self, file_path: str, cached_data: dict) -> ValidationResult:
        """Validate file using medium accuracy (mtime + size).
        Balanced approach for archival applications.
        """
        try:
            if not os.path.exists(file_path):
                return ValidationResult(
                    is_valid=False,
                    file_exists=False,
                    content_changed=False,
                    path_changed=True,
                    confidence=0.8,
                )

            # Get current file stats
            stat = os.stat(file_path)
            current_mtime = stat.st_mtime
            current_size = stat.st_size

            # Compare with cached data
            cached_mtime = cached_data.get("modified_time", 0)
            cached_size = cached_data.get("file_size", 0)

            # Check if file content likely changed
            content_changed = (
                abs(current_mtime - cached_mtime) > 1.0  # 1 second tolerance
                or current_size != cached_size
            )

            return ValidationResult(
                is_valid=not content_changed,
                file_exists=True,
                content_changed=content_changed,
                path_changed=False,
                confidence=0.95 if not content_changed else 0.3,
            )

        except OSError as e:
            logger.debug("[FileValidationManager] Error validating %s: %s", file_path, e)
            return ValidationResult(
                is_valid=False,
                file_exists=False,
                content_changed=True,
                path_changed=True,
                confidence=0.1,
            )

    def find_moved_file_by_content(self, target_signature: FileSignature) -> dict | None:
        """Find moved file using content-based identification.
        Critical for archival applications where files are moved at OS level.
        """
        if not target_signature.content_hash:
            return None

        # Try to find file by content signature in database
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()

                # First try: exact content match (hash + size + filename)
                cursor.execute(
                    """
                    SELECT fp.*, fh.hash_value, fh.file_size_at_hash
                    FROM file_paths fp
                    JOIN file_hashes fh ON fp.id = fh.path_id
                    WHERE fh.hash_value = ?
                    AND fp.file_size = ?
                    AND fp.filename = ?
                    ORDER BY fp.updated_at DESC
                    LIMIT 1
                """,
                    (
                        target_signature.content_hash,
                        target_signature.file_size,
                        target_signature.filename,
                    ),
                )

                row = cursor.fetchone()
                if row:
                    logger.info(
                        "[FileValidationManager] Found moved file by exact content match: %s",
                        row["filename"],
                    )
                    return dict(row)

                # Second try: content hash + size (filename might have changed)
                cursor.execute(
                    """
                    SELECT fp.*, fh.hash_value, fh.file_size_at_hash
                    FROM file_paths fp
                    JOIN file_hashes fh ON fp.id = fh.path_id
                    WHERE fh.hash_value = ?
                    AND fh.file_size_at_hash = ?
                    ORDER BY fp.updated_at DESC
                    LIMIT 1
                """,
                    (target_signature.content_hash, target_signature.file_size),
                )

                row = cursor.fetchone()
                if row:
                    logger.info(
                        "[FileValidationManager] Found moved file by content hash + size: %s",
                        row["filename"],
                    )
                    return dict(row)

        except Exception as e:
            logger.error("[FileValidationManager] Error searching for moved file: %s", e)

        return None

    def identify_file_with_content_fallback(self, file_path: str) -> tuple[dict | None, bool]:
        """Identify file using hybrid approach: path-based first, then content-based.
        Returns (file_record, was_moved).
        """
        # First try: direct path lookup (fastest)
        path_id = self.db_manager.get_path_id(file_path)
        if path_id:
            # File found by path, verify it hasn't changed
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM file_paths WHERE id = ?", (path_id,))
                file_record = cursor.fetchone()

                if file_record:
                    cached_data = dict(file_record)
                    validation = self.validate_file_medium_accuracy(file_path, cached_data)

                    if validation.is_valid:
                        return cached_data, False  # Found by path, not moved

        # Second try: content-based identification (for moved files)
        if self.enable_content_based_identification:
            # Calculate hash for content identification
            content_hash = self.hash_manager.calculate_hash(file_path)
            if content_hash:
                signature = FileSignature.create(file_path, content_hash)
                moved_file = self.find_moved_file_by_content(signature)

                if moved_file:
                    # Update path in database
                    self.db_manager.get_or_create_path_id(file_path)  # This updates the path
                    logger.info(
                        "[FileValidationManager] Updated path for moved file: %s", file_path
                    )
                    return moved_file, True  # Found by content, was moved

        return None, False  # New file

    def get_operation_thresholds(self, operation: OperationType) -> ValidationThresholds:
        """Get validation thresholds for specific operation type."""
        return self.default_thresholds.get(
            operation, self.default_thresholds[OperationType.FILE_LOADING]
        )

    def should_warn_user(
        self, operation: OperationType, file_count: int, total_size_mb: float
    ) -> bool:
        """Determine if user should be warned about operation size.
        Considers user preferences and operation-specific thresholds.
        """
        thresholds = self.get_operation_thresholds(operation)

        if not thresholds.warning_enabled:
            return False

        # Check if user has remembered preference for this scenario
        pref_key = f"{operation.value}_{file_count // 100 * 100}_{int(total_size_mb // 100 * 100)}"
        if pref_key in self.user_preferences:
            pref = self.user_preferences[pref_key]
            if time.time() - pref["timestamp"] < pref.get("ttl", 3600):  # 1 hour default
                return pref["should_warn"]

        # Apply thresholds
        exceeds_file_limit = file_count > thresholds.max_files
        exceeds_size_limit = total_size_mb > thresholds.max_size_mb

        return exceeds_file_limit or exceeds_size_limit

    def remember_user_choice(
        self,
        operation: OperationType,
        file_count: int,
        total_size_mb: float,
        choice: str,
        remember_duration: int = 3600,
    ):
        """Remember user's validation choice for similar scenarios."""
        pref_key = f"{operation.value}_{file_count // 100 * 100}_{int(total_size_mb // 100 * 100)}"

        self.user_preferences[pref_key] = {
            "should_warn": choice == "cancel",
            "timestamp": time.time(),
            "ttl": remember_duration,
            "choice": choice,
        }

        logger.debug(
            "[FileValidationManager] Remembered user choice: %s for %s",
            choice,
            operation.value,
        )

    def validate_operation_batch(
        self, files: list[str], operation: OperationType
    ) -> dict[str, Any]:
        """Validate a batch of files for specific operation.
        Returns validation summary and recommendations.
        """
        if not files:
            return {"proceed": True, "warnings": [], "file_count": 0, "total_size_mb": 0}

        # Calculate total size efficiently
        total_size_bytes = calculate_files_total_size(files)
        total_size_mb = total_size_bytes / (1024 * 1024)
        file_count = len(files)

        # Get thresholds for this operation
        thresholds = self.get_operation_thresholds(operation)

        # Determine if warning is needed
        should_warn = self.should_warn_user(operation, file_count, total_size_mb)

        # Generate warnings and recommendations
        warnings = []
        if file_count > thresholds.max_files:
            warnings.append(
                f"Large number of files: {file_count} (threshold: {thresholds.max_files})"
            )

        if total_size_mb > thresholds.max_size_mb:
            warnings.append(
                f"Large total size: {total_size_mb:.1f} MB (threshold: {thresholds.max_size_mb} MB)"
            )

        # Estimate operation time
        estimated_time = self._estimate_operation_time(file_count, total_size_bytes, operation)

        return {
            "proceed": not should_warn,
            "should_warn": should_warn,
            "warnings": warnings,
            "file_count": file_count,
            "total_size_mb": total_size_mb,
            "estimated_time_seconds": estimated_time,
            "recommended_batch_size": thresholds.batch_size,
            "operation": operation.value,
        }

    def _estimate_operation_time(
        self, file_count: int, total_size_bytes: int, operation: OperationType
    ) -> float:
        """Estimate operation time based on file count, size, and operation type."""
        # Base rates (conservative estimates for archival scenarios)
        rates = {
            OperationType.METADATA_FAST: {"files_per_sec": 15, "bytes_per_sec": 80 * 1024 * 1024},
            OperationType.METADATA_EXTENDED: {
                "files_per_sec": 5,
                "bytes_per_sec": 30 * 1024 * 1024,
            },
            OperationType.HASH_CALCULATION: {
                "files_per_sec": 8,
                "bytes_per_sec": 120 * 1024 * 1024,
            },
            OperationType.RENAME_OPERATION: {
                "files_per_sec": 100,
                "bytes_per_sec": 1000 * 1024 * 1024,
            },
            OperationType.FILE_LOADING: {"files_per_sec": 200, "bytes_per_sec": 2000 * 1024 * 1024},
        }

        rate = rates.get(operation, rates[OperationType.FILE_LOADING])

        # Calculate time estimates
        time_by_files = file_count / rate["files_per_sec"]
        time_by_size = total_size_bytes / rate["bytes_per_sec"]

        # Use the larger estimate (bottleneck) with minimum time
        estimated_time = max(time_by_files, time_by_size, 1.0)

        return estimated_time

    def cleanup_stale_cache_entries(self, _max_age_days: int = 30):
        """Clean up stale cache entries older than specified days."""
        try:
            logger.debug("Cleaning up stale cache entries", extra={"dev_only": True})
            # Implementation would go here - currently just a placeholder
        except Exception as e:
            logger.error("Error cleaning up stale cache entries: %s", e)

    def get_validation_stats(self) -> dict[str, Any]:
        """Get validation manager statistics."""
        try:
            stats = self.db_manager.get_database_stats()

            return {
                "total_files_tracked": stats.get("file_paths", 0),
                "files_with_metadata": stats.get("file_metadata", 0),
                "files_with_hashes": stats.get("file_hashes", 0),
                "user_preferences_cached": len(self.user_preferences),
                "content_based_identification_enabled": self.enable_content_based_identification,
                "default_accuracy": self.default_accuracy.value,
            }

        except Exception as e:
            logger.error("[FileValidationManager] Error getting stats: %s", e)
            return {}


# Global instance
_file_validation_manager = None


def get_file_validation_manager() -> FileValidationManager:
    """Get the global FileValidationManager instance."""
    global _file_validation_manager
    if _file_validation_manager is None:
        _file_validation_manager = FileValidationManager()
    return _file_validation_manager
