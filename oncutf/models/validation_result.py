"""Module: validation_result.py.

Author: Michael Economou
Date: 2025-12-16

Validation result dataclasses for pre-execution file validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oncutf.models.file_item import FileItem


class ValidationIssueType(Enum):
    """Types of validation issues that can occur."""

    MISSING = "missing"  # File no longer exists
    LOCKED = "locked"  # File is locked by another process
    PERMISSION_DENIED = "permission_denied"  # No write permission
    MODIFIED = "modified"  # File hash changed since preview
    INACCESSIBLE = "inaccessible"  # Other access error


@dataclass
class ValidationIssue:
    """Represents a single validation issue for a file."""

    file: FileItem
    issue_type: ValidationIssueType
    message: str
    technical_details: str = ""  # Additional error details


@dataclass
class ValidationResult:
    """Result of pre-execution file validation.

    Attributes:
        valid_files: Files that passed all validation checks
        issues: List of validation issues found
        total_files: Total number of files validated

    """

    valid_files: list[FileItem] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)
    total_files: int = 0

    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no issues)."""
        return len(self.issues) == 0

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are critical issues (missing/locked/permission denied)."""
        critical_types = {
            ValidationIssueType.MISSING,
            ValidationIssueType.LOCKED,
            ValidationIssueType.PERMISSION_DENIED,
        }
        return any(issue.issue_type in critical_types for issue in self.issues)

    @property
    def missing_files(self) -> list[FileItem]:
        """Get list of missing files."""
        return [
            issue.file for issue in self.issues if issue.issue_type == ValidationIssueType.MISSING
        ]

    @property
    def locked_files(self) -> list[FileItem]:
        """Get list of locked files."""
        return [
            issue.file for issue in self.issues if issue.issue_type == ValidationIssueType.LOCKED
        ]

    @property
    def permission_denied_files(self) -> list[FileItem]:
        """Get list of files with permission issues."""
        return [
            issue.file
            for issue in self.issues
            if issue.issue_type == ValidationIssueType.PERMISSION_DENIED
        ]

    @property
    def modified_files(self) -> list[FileItem]:
        """Get list of modified files."""
        return [
            issue.file for issue in self.issues if issue.issue_type == ValidationIssueType.MODIFIED
        ]

    def get_summary(self) -> str:
        """Get human-readable summary of validation results."""
        if self.is_valid:
            return f"All {self.total_files} files passed validation"

        lines = [f"Validation found {len(self.issues)} issue(s):"]
        if self.missing_files:
            lines.append(f"  - {len(self.missing_files)} file(s) missing")
        if self.locked_files:
            lines.append(f"  - {len(self.locked_files)} file(s) locked")
        if self.permission_denied_files:
            lines.append(f"  - {len(self.permission_denied_files)} file(s) permission denied")
        if self.modified_files:
            lines.append(f"  - {len(self.modified_files)} file(s) modified")

        return "\n".join(lines)
