"""
Module: pre_execution_validator.py

Author: Michael Economou
Date: 2025-12-16

Validates files before rename execution to catch filesystem issues.
"""

from __future__ import annotations

import logging
import os
import platform
from pathlib import Path
from typing import TYPE_CHECKING

from oncutf.models.validation_result import (
    ValidationIssue,
    ValidationIssueType,
    ValidationResult,
)

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem

logger = logging.getLogger(__name__)


class PreExecutionValidator:
    """Validates files before rename execution.

    Checks for:
    - File existence
    - Write permissions
    - File locks (Windows)
    - Hash changes (optional)
    """

    def __init__(self, check_hash: bool = False) -> None:
        """Initialize validator.

        Args:
            check_hash: Whether to verify file hashes haven't changed
        """
        self.check_hash = check_hash
        self._is_windows = platform.system() == "Windows"

    def validate(self, files: list[FileItem]) -> ValidationResult:
        """Validate all files before rename execution.

        Args:
            files: List of files to validate

        Returns:
            ValidationResult with valid files and issues
        """
        result = ValidationResult(total_files=len(files))

        for file_item in files:
            issues = self._validate_single_file(file_item)
            if issues:
                result.issues.extend(issues)
            else:
                result.valid_files.append(file_item)

        logger.info(
            "Pre-execution validation: %d valid, %d issues",
            len(result.valid_files),
            len(result.issues)
        )

        return result

    def _validate_single_file(self, file_item: FileItem) -> list[ValidationIssue]:
        """Validate a single file.

        Args:
            file_item: File to validate

        Returns:
            List of validation issues (empty if valid)
        """
        issues: list[ValidationIssue] = []
        file_path = Path(file_item.path)

        # Check 1: File existence
        if not file_path.exists():
            issues.append(
                ValidationIssue(
                    file=file_item,
                    issue_type=ValidationIssueType.MISSING,
                    message=f"File no longer exists: {file_item.name}",
                    technical_details=f"Path: {file_path}"
                )
            )
            return issues  # No point in further checks

        # Check 2: Write permissions
        if not os.access(file_path, os.W_OK):
            issues.append(
                ValidationIssue(
                    file=file_item,
                    issue_type=ValidationIssueType.PERMISSION_DENIED,
                    message=f"No write permission: {file_item.name}",
                    technical_details=f"Path: {file_path}"
                )
            )

        # Check 3: File lock (try opening for write)
        lock_check_result = self._check_file_lock(file_path, file_item)
        if lock_check_result:
            issues.append(lock_check_result)

        # Check 4: Hash verification (optional)
        if self.check_hash and not issues:
            hash_check_result = self._check_file_hash(file_path, file_item)
            if hash_check_result:
                issues.append(hash_check_result)

        return issues

    def _check_file_lock(
        self, file_path: Path, file_item: FileItem
    ) -> ValidationIssue | None:
        """Check if file is locked by another process.

        Args:
            file_path: Path to file
            file_item: FileItem object

        Returns:
            ValidationIssue if locked, None otherwise
        """
        try:
            # Try opening file for writing (non-destructive)
            # Use 'r+' mode which requires write permission but doesn't truncate
            if file_path.is_file():
                with file_path.open('r+b'):
                    pass  # Successfully opened for writing
            return None

        except PermissionError as e:
            # File is locked or permission denied
            if self._is_windows:
                # On Windows, this usually means file is open in another program
                return ValidationIssue(
                    file=file_item,
                    issue_type=ValidationIssueType.LOCKED,
                    message=f"File is locked (open in another program): {file_item.name}",
                    technical_details=str(e)
                )
            else:
                # On Unix, permission error was already caught
                return None

        except OSError as e:
            # Other OS errors (e.g., file is a directory, device error)
            logger.warning("OS error checking file lock for %s: %s", file_path, e)
            return ValidationIssue(
                file=file_item,
                issue_type=ValidationIssueType.INACCESSIBLE,
                message=f"Cannot access file: {file_item.name}",
                technical_details=str(e)
            )

        except Exception as e:
            # Unexpected errors
            logger.error("Unexpected error checking file lock for %s: %s", file_path, e)
            return ValidationIssue(
                file=file_item,
                issue_type=ValidationIssueType.INACCESSIBLE,
                message=f"Error accessing file: {file_item.name}",
                technical_details=str(e)
            )

    def _check_file_hash(
        self, file_path: Path, file_item: FileItem
    ) -> ValidationIssue | None:
        """Check if file hash matches cached value.

        Args:
            file_path: Path to file
            file_item: FileItem with cached hash

        Returns:
            ValidationIssue if hash changed, None otherwise
        """
        if not hasattr(file_item, 'hash') or not file_item.hash:
            # No cached hash available
            return None

        try:
            # Import here to avoid circular dependency
            from oncutf.core.hash.hash_manager import HashManager

            hash_manager = HashManager()
            current_hash = hash_manager.calculate_hash(str(file_path))

            if current_hash and current_hash != file_item.hash:
                return ValidationIssue(
                    file=file_item,
                    issue_type=ValidationIssueType.MODIFIED,
                    message=f"File modified since preview: {file_item.name}",
                    technical_details=f"Expected: {file_item.hash[:8]}..., Got: {current_hash[:8]}..."
                )

        except Exception as e:
            logger.warning("Error checking hash for %s: %s", file_path, e)
            # Don't fail validation on hash check errors
            return None

        return None
