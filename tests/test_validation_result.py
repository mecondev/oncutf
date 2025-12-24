"""Module: test_validation_result.py

Author: Michael Economou
Date: 2025-12-16

Tests for ValidationResult and related classes.
"""

from unittest.mock import MagicMock

import pytest

from oncutf.models.file_item import FileItem
from oncutf.models.validation_result import (
    ValidationIssue,
    ValidationIssueType,
    ValidationResult,
)


class TestValidationIssueType:
    """Test ValidationIssueType enum."""

    def test_issue_types_exist(self):
        """Test all issue types are defined."""
        assert ValidationIssueType.MISSING
        assert ValidationIssueType.LOCKED
        assert ValidationIssueType.PERMISSION_DENIED
        assert ValidationIssueType.MODIFIED
        assert ValidationIssueType.INACCESSIBLE

    def test_issue_type_values(self):
        """Test issue type values."""
        assert ValidationIssueType.MISSING.value == "missing"
        assert ValidationIssueType.LOCKED.value == "locked"
        assert ValidationIssueType.PERMISSION_DENIED.value == "permission_denied"
        assert ValidationIssueType.MODIFIED.value == "modified"
        assert ValidationIssueType.INACCESSIBLE.value == "inaccessible"


class TestValidationIssue:
    """Test ValidationIssue dataclass."""

    @pytest.fixture
    def mock_file_item(self):
        """Create mock FileItem."""
        item = MagicMock(spec=FileItem)
        item.name = "test.txt"
        item.path = "/path/to/test.txt"
        return item

    def test_issue_creation(self, mock_file_item):
        """Test creating validation issue."""
        issue = ValidationIssue(
            file=mock_file_item,
            issue_type=ValidationIssueType.MISSING,
            message="File not found",
            technical_details="Path: /path/to/test.txt",
        )

        assert issue.file == mock_file_item
        assert issue.issue_type == ValidationIssueType.MISSING
        assert issue.message == "File not found"
        assert issue.technical_details == "Path: /path/to/test.txt"

    def test_issue_creation_minimal(self, mock_file_item):
        """Test creating issue with minimal fields."""
        issue = ValidationIssue(
            file=mock_file_item, issue_type=ValidationIssueType.LOCKED, message="File is locked"
        )

        assert issue.file == mock_file_item
        assert issue.issue_type == ValidationIssueType.LOCKED
        assert issue.message == "File is locked"
        assert issue.technical_details == ""


class TestValidationResult:
    """Test ValidationResult dataclass."""

    @pytest.fixture
    def mock_files(self):
        """Create mock FileItems."""
        files = []
        for i in range(5):
            item = MagicMock(spec=FileItem)
            item.name = f"file{i}.txt"
            item.path = f"/path/to/file{i}.txt"
            files.append(item)
        return files

    def test_empty_result(self):
        """Test empty validation result."""
        result = ValidationResult()

        assert result.is_valid
        assert not result.has_critical_issues
        assert len(result.valid_files) == 0
        assert len(result.issues) == 0
        assert result.total_files == 0

    def test_valid_result(self, mock_files):
        """Test result with only valid files."""
        result = ValidationResult(valid_files=mock_files, issues=[], total_files=len(mock_files))

        assert result.is_valid
        assert not result.has_critical_issues
        assert len(result.valid_files) == 5
        assert len(result.issues) == 0

    def test_result_with_missing_files(self, mock_files):
        """Test result with missing files."""
        issues = [
            ValidationIssue(
                file=mock_files[0], issue_type=ValidationIssueType.MISSING, message="File missing"
            ),
            ValidationIssue(
                file=mock_files[1], issue_type=ValidationIssueType.MISSING, message="File missing"
            ),
        ]

        result = ValidationResult(
            valid_files=mock_files[2:], issues=issues, total_files=len(mock_files)
        )

        assert not result.is_valid
        assert result.has_critical_issues
        assert len(result.valid_files) == 3
        assert len(result.issues) == 2
        assert len(result.missing_files) == 2

    def test_result_with_locked_files(self, mock_files):
        """Test result with locked files."""
        issues = [
            ValidationIssue(
                file=mock_files[0], issue_type=ValidationIssueType.LOCKED, message="File locked"
            )
        ]

        result = ValidationResult(
            valid_files=mock_files[1:], issues=issues, total_files=len(mock_files)
        )

        assert not result.is_valid
        assert result.has_critical_issues
        assert len(result.locked_files) == 1

    def test_result_with_permission_denied(self, mock_files):
        """Test result with permission issues."""
        issues = [
            ValidationIssue(
                file=mock_files[0],
                issue_type=ValidationIssueType.PERMISSION_DENIED,
                message="No write permission",
            )
        ]

        result = ValidationResult(
            valid_files=mock_files[1:], issues=issues, total_files=len(mock_files)
        )

        assert not result.is_valid
        assert result.has_critical_issues
        assert len(result.permission_denied_files) == 1

    def test_result_with_modified_files(self, mock_files):
        """Test result with modified files."""
        issues = [
            ValidationIssue(
                file=mock_files[0], issue_type=ValidationIssueType.MODIFIED, message="File modified"
            )
        ]

        result = ValidationResult(
            valid_files=mock_files[1:], issues=issues, total_files=len(mock_files)
        )

        assert not result.is_valid
        assert not result.has_critical_issues  # Modified is not critical
        assert len(result.modified_files) == 1

    def test_result_with_mixed_issues(self, mock_files):
        """Test result with multiple issue types."""
        issues = [
            ValidationIssue(
                file=mock_files[0], issue_type=ValidationIssueType.MISSING, message="Missing"
            ),
            ValidationIssue(
                file=mock_files[1], issue_type=ValidationIssueType.LOCKED, message="Locked"
            ),
            ValidationIssue(
                file=mock_files[2], issue_type=ValidationIssueType.MODIFIED, message="Modified"
            ),
        ]

        result = ValidationResult(
            valid_files=mock_files[3:], issues=issues, total_files=len(mock_files)
        )

        assert not result.is_valid
        assert result.has_critical_issues
        assert len(result.missing_files) == 1
        assert len(result.locked_files) == 1
        assert len(result.modified_files) == 1
        assert len(result.permission_denied_files) == 0

    def test_get_summary_valid(self, mock_files):
        """Test summary for valid result."""
        result = ValidationResult(valid_files=mock_files, issues=[], total_files=len(mock_files))

        summary = result.get_summary()
        assert "5 files passed validation" in summary.lower() or "all" in summary.lower()

    def test_get_summary_with_issues(self, mock_files):
        """Test summary with issues."""
        issues = [
            ValidationIssue(
                file=mock_files[0], issue_type=ValidationIssueType.MISSING, message="Missing"
            ),
            ValidationIssue(
                file=mock_files[1], issue_type=ValidationIssueType.LOCKED, message="Locked"
            ),
        ]

        result = ValidationResult(
            valid_files=mock_files[2:], issues=issues, total_files=len(mock_files)
        )

        summary = result.get_summary()
        assert "2 issue" in summary.lower()
        assert "1 file(s) missing" in summary.lower()
        assert "1 file(s) locked" in summary.lower()

    def test_issue_filtering(self, mock_files):
        """Test convenience properties filter correctly."""
        issues = [
            ValidationIssue(mock_files[0], ValidationIssueType.MISSING, "msg"),
            ValidationIssue(mock_files[1], ValidationIssueType.LOCKED, "msg"),
            ValidationIssue(mock_files[2], ValidationIssueType.PERMISSION_DENIED, "msg"),
            ValidationIssue(mock_files[3], ValidationIssueType.MODIFIED, "msg"),
        ]

        result = ValidationResult(
            valid_files=[mock_files[4]], issues=issues, total_files=len(mock_files)
        )

        assert len(result.missing_files) == 1
        assert result.missing_files[0] == mock_files[0]

        assert len(result.locked_files) == 1
        assert result.locked_files[0] == mock_files[1]

        assert len(result.permission_denied_files) == 1
        assert result.permission_denied_files[0] == mock_files[2]

        assert len(result.modified_files) == 1
        assert result.modified_files[0] == mock_files[3]
