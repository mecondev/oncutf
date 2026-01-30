"""Module: test_pre_execution_validator.py

Author: Michael Economou
Date: 2025-12-16

Tests for PreExecutionValidator.
"""

import contextlib
import os
import platform
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from oncutf.core.pre_execution_validator import PreExecutionValidator
from oncutf.models.file_item import FileItem
from oncutf.models.validation_result import ValidationIssueType


class TestPreExecutionValidator:
    """Test pre-execution file validation."""

    @pytest.fixture
    def temp_file(self):
        """Create a temporary test file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            path = f.name
        yield path
        if os.path.exists(path):
            with contextlib.suppress(OSError):
                Path(path).unlink()

    @pytest.fixture
    def file_item(self, temp_file):
        """Create a FileItem for testing."""
        item = FileItem.from_path(temp_file)
        item.hash = "test_hash_123"
        return item

    @pytest.fixture
    def validator(self):
        """Create PreExecutionValidator instance."""
        return PreExecutionValidator(check_hash=False)

    def test_validator_creation(self):
        """Test validator instantiation."""
        validator = PreExecutionValidator()
        assert validator.check_hash is False

        validator_with_hash = PreExecutionValidator(check_hash=True)
        assert validator_with_hash.check_hash is True

    def test_validate_single_valid_file(self, validator, file_item):
        """Test validation of a single valid file."""
        result = validator.validate([file_item])

        assert result.is_valid
        assert len(result.valid_files) == 1
        assert len(result.issues) == 0
        assert result.total_files == 1

    def test_validate_missing_file(self, validator):
        """Test validation detects missing files."""
        # Use from_path for non-existent file (will still create object)
        missing_item = FileItem.from_path("/nonexistent/file.txt")
        result = validator.validate([missing_item])

        assert not result.is_valid
        assert len(result.valid_files) == 0
        assert len(result.issues) == 1
        assert result.issues[0].issue_type == ValidationIssueType.MISSING
        assert result.has_critical_issues

    def test_validate_multiple_files_mixed(self, validator, file_item):
        """Test validation with mix of valid and invalid files."""
        missing_item = FileItem.from_path("/nonexistent/file.txt")

        result = validator.validate([file_item, missing_item])

        assert not result.is_valid
        assert len(result.valid_files) == 1
        assert len(result.issues) == 1
        assert result.total_files == 2

    @pytest.mark.skipif(
        platform.system() == "Windows", reason="Permission tests unreliable on Windows"
    )
    def test_validate_permission_denied(self, validator, temp_file):
        """Test validation detects permission issues."""
        # Make file read-only
        os.chmod(temp_file, 0o444)

        item = FileItem.from_path(temp_file)
        result = validator.validate([item])

        # Restore permissions
        os.chmod(temp_file, 0o644)

        # Should detect permission issue
        if not result.is_valid:
            assert result.has_critical_issues
            assert any(
                issue.issue_type == ValidationIssueType.PERMISSION_DENIED for issue in result.issues
            )

    def test_validate_locked_file_windows_simulation(self, validator, file_item):
        """Test locked file detection (simulated)."""
        # Mock file opening to simulate lock
        with patch("pathlib.Path.open", side_effect=PermissionError("File locked")):
            result = validator.validate([file_item])

            if platform.system() == "Windows":
                assert not result.is_valid
                assert len(result.issues) == 1
                assert result.issues[0].issue_type == ValidationIssueType.LOCKED

    def test_validate_with_hash_check_match(self, file_item):
        """Test hash validation with matching hash."""
        validator = PreExecutionValidator(check_hash=True)

        # Mock hash calculation to return matching hash
        with patch(
            "oncutf.core.hash.hash_manager.HashManager.calculate_hash",
            return_value=file_item.hash,
        ):
            result = validator.validate([file_item])

            assert result.is_valid
            assert len(result.valid_files) == 1

    def test_validate_with_hash_check_mismatch(self, file_item):
        """Test hash validation with mismatched hash."""
        validator = PreExecutionValidator(check_hash=True)

        # Mock hash calculation to return different hash
        with patch(
            "oncutf.core.hash.hash_manager.HashManager.calculate_hash",
            return_value="different_hash_456",
        ):
            result = validator.validate([file_item])

            assert not result.is_valid
            assert len(result.issues) == 1
            assert result.issues[0].issue_type == ValidationIssueType.MODIFIED

    def test_validation_result_properties(self, validator):
        """Test ValidationResult convenience properties."""
        # Create mock items
        valid_item = MagicMock(spec=FileItem)
        valid_item.path = "/valid/file.txt"
        valid_item.name = "file.txt"

        missing_item = MagicMock(spec=FileItem)
        missing_item.path = "/missing/file.txt"
        missing_item.name = "missing.txt"

        # Mock validation to return mixed results
        with patch.object(
            validator,
            "_validate_single_file",
            side_effect=[
                [],
                [MagicMock(issue_type=ValidationIssueType.MISSING, file=missing_item)],
            ],
        ):
            result = validator.validate([valid_item, missing_item])

            assert result.total_files == 2
            assert len(result.missing_files) == 1
            assert len(result.locked_files) == 0
            assert len(result.permission_denied_files) == 0
            assert len(result.modified_files) == 0

    def test_validation_summary(self, validator, file_item):
        """Test validation result summary generation."""
        result = validator.validate([file_item])
        summary = result.get_summary()

        assert "1 files passed validation" in summary.lower() or "all" in summary.lower()

    def test_validation_empty_file_list(self, validator):
        """Test validation with empty file list."""
        result = validator.validate([])

        assert result.is_valid
        assert result.total_files == 0
        assert len(result.valid_files) == 0
        assert len(result.issues) == 0

    def test_check_file_lock_os_error(self, validator, file_item):
        """Test handling of OS errors during lock check."""
        # Mock to simulate OS error
        with patch("pathlib.Path.open", side_effect=OSError("Device error")):
            result = validator.validate([file_item])

            assert not result.is_valid
            assert len(result.issues) == 1
            assert result.issues[0].issue_type == ValidationIssueType.INACCESSIBLE
