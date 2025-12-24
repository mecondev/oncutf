"""
Module: test_rename_controller.py

Author: Michael Economou
Date: 2025-12-16

Unit tests for RenameController.
Tests the controller's orchestration logic without Qt dependencies.
"""

import warnings
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

import pytest

from oncutf.controllers.rename_controller import RenameController
from oncutf.models.file_item import FileItem


class MockPreviewResult:
    """Mock PreviewResult from UnifiedRenameEngine."""

    def __init__(self, name_pairs: list[tuple[str, str]], has_changes: bool = True):
        self.name_pairs = name_pairs
        self.has_changes = has_changes


class MockValidationItem:
    """Mock ValidationItem."""

    def __init__(
        self,
        old_name: str,
        new_name: str,
        is_valid: bool = True,
        is_duplicate: bool = False,
        is_unchanged: bool = False,
        error_message: str = "",
    ):
        self.old_name = old_name
        self.new_name = new_name
        self.is_valid = is_valid
        self.is_duplicate = is_duplicate
        self.is_unchanged = is_unchanged
        self.error_message = error_message


class MockValidationResult:
    """Mock ValidationResult from UnifiedRenameEngine."""

    def __init__(
        self,
        has_errors: bool = False,
        valid_count: int = 0,
        invalid_count: int = 0,
        duplicate_count: int = 0,
        unchanged_count: int = 0,
        items: list = None,
    ):
        self.has_errors = has_errors
        self.valid_count = valid_count
        self.invalid_count = invalid_count
        self.duplicate_count = duplicate_count
        self.unchanged_count = unchanged_count
        self.items = items or []


class MockRenameResult:
    """Mock single rename result."""

    def __init__(self, old_path: str, new_path: str, success: bool = True, error: str = ""):
        self.old_path = old_path
        self.new_path = new_path
        self.success = success
        self.error = error


class MockExecutionResult:
    """Mock ExecutionResult from UnifiedRenameEngine."""

    def __init__(
        self,
        renamed_count: int = 0,
        failed_count: int = 0,
        skipped_count: int = 0,
        results: list = None,
    ):
        self.renamed_count = renamed_count
        self.failed_count = failed_count
        self.skipped_count = skipped_count
        self.results = results or []


class MockRenameState:
    """Mock RenameState."""

    def __init__(
        self,
        preview_result: Any = None,
        validation_result: Any = None,
        execution_result: Any = None,
    ):
        self.preview_result = preview_result
        self.validation_result = validation_result
        self.execution_result = execution_result
        self.preview_changed = False
        self.validation_changed = False
        self.execution_changed = False


@pytest.fixture
def mock_unified_rename_engine():
    """Create mock UnifiedRenameEngine."""
    engine = MagicMock()
    engine.state_manager = MagicMock()
    engine.state_manager.get_state.return_value = MockRenameState()
    return engine


@pytest.fixture
def mock_preview_manager():
    """Create mock PreviewManager."""
    return MagicMock()


@pytest.fixture
def mock_rename_manager():
    """Create mock RenameManager."""
    return MagicMock()


@pytest.fixture
def mock_file_store():
    """Create mock FileStore."""
    return MagicMock()


@pytest.fixture
def mock_context():
    """Create mock ApplicationContext."""
    return MagicMock()


@pytest.fixture
def rename_controller(
    mock_unified_rename_engine,
    mock_preview_manager,
    mock_rename_manager,
    mock_file_store,
    mock_context,
):
    """Create RenameController with mocked dependencies."""
    return RenameController(
        unified_rename_engine=mock_unified_rename_engine,
        preview_manager=mock_preview_manager,
        rename_manager=mock_rename_manager,
        file_store=mock_file_store,
        context=mock_context,
    )


@pytest.fixture
def sample_file_items():
    """Create sample FileItem objects for testing."""
    return [
        FileItem("/test/file1.txt", "txt", datetime.now()),
        FileItem("/test/file2.jpg", "jpg", datetime.now()),
        FileItem("/test/file3.pdf", "pdf", datetime.now()),
    ]


@pytest.fixture
def sample_modules_data():
    """Create sample modules data."""
    return [
        {"type": "specified_text", "text": "prefix_"},
        {"type": "counter", "start": 1, "digits": 3},
    ]


@pytest.fixture
def sample_post_transform():
    """Create sample post-transform data."""
    return {"case": "lower", "greeklish": False, "separator": "_"}


class TestRenameControllerInitialization:
    """Tests for RenameController initialization."""

    def test_initialization_with_all_dependencies(self, rename_controller):
        """Test controller initializes with all dependencies."""
        assert rename_controller._unified_rename_engine is not None
        assert rename_controller._preview_manager is not None
        assert rename_controller._rename_manager is not None
        assert rename_controller._file_store is not None
        assert rename_controller._context is not None

    def test_initialization_with_no_dependencies(self):
        """Test controller initializes with no dependencies."""
        controller = RenameController()
        assert controller._unified_rename_engine is None
        assert controller._preview_manager is None
        assert controller._rename_manager is None
        assert controller._file_store is None
        assert controller._context is None


class TestGeneratePreview:
    """Tests for generate_preview method."""

    def test_generate_preview_success(
        self, rename_controller, sample_file_items, sample_modules_data, sample_post_transform
    ):
        """Test successful preview generation."""
        # Setup mock
        expected_pairs = [
            ("file1.txt", "prefix_001.txt"),
            ("file2.jpg", "prefix_002.jpg"),
            ("file3.pdf", "prefix_003.pdf"),
        ]
        mock_result = MockPreviewResult(expected_pairs, has_changes=True)
        rename_controller._unified_rename_engine.generate_preview.return_value = mock_result

        # Execute
        result = rename_controller.generate_preview(
            file_items=sample_file_items,
            modules_data=sample_modules_data,
            post_transform=sample_post_transform,
            metadata_cache={},
        )

        # Verify
        assert result["success"] is True
        assert result["has_changes"] is True
        assert len(result["name_pairs"]) == 3
        assert result["name_pairs"] == expected_pairs
        assert len(result["errors"]) == 0

        # Verify engine was called
        rename_controller._unified_rename_engine.generate_preview.assert_called_once()

    def test_generate_preview_no_files(
        self, rename_controller, sample_modules_data, sample_post_transform
    ):
        """Test preview generation with no files."""
        result = rename_controller.generate_preview(
            file_items=[],
            modules_data=sample_modules_data,
            post_transform=sample_post_transform,
            metadata_cache={},
        )

        assert result["success"] is False
        assert result["has_changes"] is False
        assert len(result["name_pairs"]) == 0
        assert "No files provided" in result["errors"]

    def test_generate_preview_no_engine(
        self, sample_file_items, sample_modules_data, sample_post_transform
    ):
        """Test preview generation without engine."""
        controller = RenameController()  # No engine
        result = controller.generate_preview(
            file_items=sample_file_items,
            modules_data=sample_modules_data,
            post_transform=sample_post_transform,
            metadata_cache={},
        )

        assert result["success"] is False
        assert "Rename engine not initialized" in result["errors"]

    def test_generate_preview_no_changes(
        self, rename_controller, sample_file_items, sample_modules_data, sample_post_transform
    ):
        """Test preview generation with no changes."""
        # Setup mock
        mock_result = MockPreviewResult([], has_changes=False)
        rename_controller._unified_rename_engine.generate_preview.return_value = mock_result

        # Execute
        result = rename_controller.generate_preview(
            file_items=sample_file_items,
            modules_data=sample_modules_data,
            post_transform=sample_post_transform,
            metadata_cache={},
        )

        # Verify
        assert result["success"] is True
        assert result["has_changes"] is False
        assert len(result["name_pairs"]) == 0

    def test_generate_preview_exception_handling(
        self, rename_controller, sample_file_items, sample_modules_data, sample_post_transform
    ):
        """Test preview generation handles exceptions."""
        # Setup mock to raise exception
        rename_controller._unified_rename_engine.generate_preview.side_effect = Exception(
            "Test error"
        )

        # Execute
        result = rename_controller.generate_preview(
            file_items=sample_file_items,
            modules_data=sample_modules_data,
            post_transform=sample_post_transform,
            metadata_cache={},
        )

        # Verify
        assert result["success"] is False
        assert result["has_changes"] is False
        assert "Preview generation failed" in result["errors"][0]


class TestValidatePreview:
    """Tests for validate_preview method."""

    def test_validate_preview_success(self, rename_controller):
        """Test successful preview validation."""
        # Setup
        preview_pairs = [
            ("file1.txt", "new1.txt"),
            ("file2.jpg", "new2.jpg"),
            ("file3.pdf", "new3.pdf"),
        ]
        mock_result = MockValidationResult(
            has_errors=False,
            valid_count=3,
            invalid_count=0,
            duplicate_count=0,
            unchanged_count=0,
            items=[
                MockValidationItem("file1.txt", "new1.txt", is_valid=True),
                MockValidationItem("file2.jpg", "new2.jpg", is_valid=True),
                MockValidationItem("file3.pdf", "new3.pdf", is_valid=True),
            ],
        )
        rename_controller._unified_rename_engine.validate_preview.return_value = mock_result

        # Execute
        result = rename_controller.validate_preview(preview_pairs)

        # Verify
        assert result["success"] is True
        assert result["has_errors"] is False
        assert result["valid_count"] == 3
        assert result["invalid_count"] == 0
        assert result["duplicate_count"] == 0
        assert len(result["validation_items"]) == 3

    def test_validate_preview_with_errors(self, rename_controller):
        """Test validation with errors."""
        preview_pairs = [
            ("file1.txt", "invalid<>.txt"),
            ("file2.jpg", "valid.jpg"),
            ("file3.pdf", "valid.jpg"),  # Duplicate
        ]
        mock_result = MockValidationResult(
            has_errors=True,
            valid_count=1,
            invalid_count=1,
            duplicate_count=1,
            unchanged_count=0,
            items=[
                MockValidationItem(
                    "file1.txt", "invalid<>.txt", is_valid=False, error_message="Invalid characters"
                ),
                MockValidationItem("file2.jpg", "valid.jpg", is_valid=True),
                MockValidationItem("file3.pdf", "valid.jpg", is_valid=True, is_duplicate=True),
            ],
        )
        rename_controller._unified_rename_engine.validate_preview.return_value = mock_result

        # Execute
        result = rename_controller.validate_preview(preview_pairs)

        # Verify
        assert result["success"] is True
        assert result["has_errors"] is True
        assert result["valid_count"] == 1
        assert result["invalid_count"] == 1
        assert result["duplicate_count"] == 1

    def test_validate_preview_no_engine(self):
        """Test validation without engine."""
        controller = RenameController()  # No engine
        result = controller.validate_preview([("old.txt", "new.txt")])

        assert result["success"] is False
        assert result["has_errors"] is True
        assert "Rename engine not initialized" in result["errors"]

    def test_validate_preview_exception_handling(self, rename_controller):
        """Test validation handles exceptions."""
        rename_controller._unified_rename_engine.validate_preview.side_effect = Exception(
            "Test error"
        )

        result = rename_controller.validate_preview([("old.txt", "new.txt")])

        assert result["success"] is False
        assert result["has_errors"] is True
        assert "Validation failed" in result["errors"][0]


class TestExecuteRename:
    """Tests for execute_rename method."""

    def test_execute_rename_success(
        self, rename_controller, sample_file_items, sample_modules_data, sample_post_transform
    ):
        """Test successful rename execution."""
        # Setup mocks
        preview_pairs = [
            ("file1.txt", "new1.txt"),
            ("file2.jpg", "new2.jpg"),
            ("file3.pdf", "new3.pdf"),
        ]
        mock_preview = MockPreviewResult(preview_pairs, has_changes=True)
        mock_validation = MockValidationResult(has_errors=False, valid_count=3)
        mock_execution = MockExecutionResult(
            renamed_count=3,
            failed_count=0,
            skipped_count=0,
            results=[
                MockRenameResult("/test/file1.txt", "/test/new1.txt", success=True),
                MockRenameResult("/test/file2.jpg", "/test/new2.jpg", success=True),
                MockRenameResult("/test/file3.pdf", "/test/new3.pdf", success=True),
            ],
        )

        rename_controller._unified_rename_engine.generate_preview.return_value = mock_preview
        rename_controller._unified_rename_engine.validate_preview.return_value = mock_validation
        rename_controller._unified_rename_engine.execute_rename.return_value = mock_execution

        # Mock validator to always pass validation
        with patch(
            "oncutf.core.pre_execution_validator.PreExecutionValidator"
        ) as mock_validator_class:
            mock_validator = MagicMock()
            mock_validator.validate.return_value = MagicMock(
                is_valid=True, issues=[], valid_files=sample_file_items
            )
            mock_validator_class.return_value = mock_validator

            # Execute
            result = rename_controller.execute_rename(
                file_items=sample_file_items,
                modules_data=sample_modules_data,
                post_transform=sample_post_transform,
                metadata_cache={},
                current_folder="/test",
            )

        # Verify
        assert result["success"] is True
        assert result["renamed_count"] == 3
        assert result["failed_count"] == 0
        assert result["skipped_count"] == 0
        assert len(result["errors"]) == 0

    def test_execute_rename_no_files(
        self, rename_controller, sample_modules_data, sample_post_transform
    ):
        """Test rename execution with no files."""
        result = rename_controller.execute_rename(
            file_items=[],
            modules_data=sample_modules_data,
            post_transform=sample_post_transform,
            metadata_cache={},
            current_folder="/test",
        )

        assert result["success"] is False
        assert result["renamed_count"] == 0
        assert "No files provided" in result["errors"]

    def test_execute_rename_no_changes(
        self, rename_controller, sample_file_items, sample_modules_data, sample_post_transform
    ):
        """Test rename execution with no changes."""
        # Setup mock
        mock_preview = MockPreviewResult([], has_changes=False)
        rename_controller._unified_rename_engine.generate_preview.return_value = mock_preview

        # Execute
        result = rename_controller.execute_rename(
            file_items=sample_file_items,
            modules_data=sample_modules_data,
            post_transform=sample_post_transform,
            metadata_cache={},
            current_folder="/test",
        )

        # Verify
        assert result["success"] is False
        assert result["renamed_count"] == 0
        assert result["skipped_count"] == len(sample_file_items)
        assert "No changes detected" in result["errors"]

    def test_execute_rename_validation_errors(
        self, rename_controller, sample_file_items, sample_modules_data, sample_post_transform
    ):
        """Test rename execution with validation errors."""
        # Setup mocks
        preview_pairs = [("file1.txt", "invalid<>.txt")]
        mock_preview = MockPreviewResult(preview_pairs, has_changes=True)
        mock_validation = MockValidationResult(has_errors=True, invalid_count=1, duplicate_count=0)

        rename_controller._unified_rename_engine.generate_preview.return_value = mock_preview
        rename_controller._unified_rename_engine.validate_preview.return_value = mock_validation

        # Execute
        result = rename_controller.execute_rename(
            file_items=sample_file_items,
            modules_data=sample_modules_data,
            post_transform=sample_post_transform,
            metadata_cache={},
            current_folder="/test",
        )

        # Verify
        assert result["success"] is False
        assert result["renamed_count"] == 0
        assert "invalid filenames" in result["errors"][0]

    def test_execute_rename_partial_failure(
        self, rename_controller, sample_file_items, sample_modules_data, sample_post_transform
    ):
        """Test rename execution with partial failures."""
        # Setup mocks
        preview_pairs = [
            ("file1.txt", "new1.txt"),
            ("file2.jpg", "new2.jpg"),
            ("file3.pdf", "new3.pdf"),
        ]
        mock_preview = MockPreviewResult(preview_pairs, has_changes=True)
        mock_validation = MockValidationResult(has_errors=False, valid_count=3)
        mock_execution = MockExecutionResult(
            renamed_count=2,
            failed_count=1,
            skipped_count=0,
            results=[
                MockRenameResult("/test/file1.txt", "/test/new1.txt", success=True),
                MockRenameResult("/test/file2.jpg", "/test/new2.jpg", success=True),
                MockRenameResult(
                    "/test/file3.pdf", "/test/new3.pdf", success=False, error="Permission denied"
                ),
            ],
        )

        rename_controller._unified_rename_engine.generate_preview.return_value = mock_preview
        rename_controller._unified_rename_engine.validate_preview.return_value = mock_validation
        rename_controller._unified_rename_engine.execute_rename.return_value = mock_execution

        # Mock validator to always pass validation
        with patch(
            "oncutf.core.pre_execution_validator.PreExecutionValidator"
        ) as mock_validator_class:
            mock_validator = MagicMock()
            mock_validator.validate.return_value = MagicMock(
                is_valid=True, issues=[], valid_files=sample_file_items
            )
            mock_validator_class.return_value = mock_validator

            # Execute
            result = rename_controller.execute_rename(
                file_items=sample_file_items,
                modules_data=sample_modules_data,
                post_transform=sample_post_transform,
                metadata_cache={},
                current_folder="/test",
            )

        # Verify
        assert result["success"] is True  # Some files renamed
        assert result["renamed_count"] == 2
        assert result["failed_count"] == 1
        assert "Permission denied" in result["errors"]

    def test_execute_rename_no_engine(
        self, sample_file_items, sample_modules_data, sample_post_transform
    ):
        """Test rename execution without engine."""
        controller = RenameController()  # No engine
        result = controller.execute_rename(
            file_items=sample_file_items,
            modules_data=sample_modules_data,
            post_transform=sample_post_transform,
            metadata_cache={},
            current_folder="/test",
        )

        assert result["success"] is False
        assert "Rename engine not initialized" in result["errors"]

    def test_execute_rename_exception_handling(
        self, rename_controller, sample_file_items, sample_modules_data, sample_post_transform
    ):
        """Test rename execution handles exceptions."""
        rename_controller._unified_rename_engine.generate_preview.side_effect = Exception(
            "Test error"
        )

        result = rename_controller.execute_rename(
            file_items=sample_file_items,
            modules_data=sample_modules_data,
            post_transform=sample_post_transform,
            metadata_cache={},
            current_folder="/test",
        )

        assert result["success"] is False
        assert "Rename execution failed" in result["errors"][0]


class TestStateQueries:
    """Tests for state query methods."""

    def test_has_pending_changes_true(self, rename_controller):
        """Test has_pending_changes returns True when changes exist."""
        mock_state = MockRenameState(
            preview_result=MockPreviewResult([("old.txt", "new.txt")], has_changes=True),
            validation_result=MockValidationResult(has_errors=False),
        )
        rename_controller._unified_rename_engine.state_manager.get_state.return_value = mock_state

        assert rename_controller.has_pending_changes() is True

    def test_has_pending_changes_false_no_preview(self, rename_controller):
        """Test has_pending_changes returns False without preview."""
        mock_state = MockRenameState(preview_result=None)
        rename_controller._unified_rename_engine.state_manager.get_state.return_value = mock_state

        assert rename_controller.has_pending_changes() is False

    def test_has_pending_changes_false_with_errors(self, rename_controller):
        """Test has_pending_changes returns False with validation errors."""
        mock_state = MockRenameState(
            preview_result=MockPreviewResult([("old.txt", "new.txt")], has_changes=True),
            validation_result=MockValidationResult(has_errors=True),
        )
        rename_controller._unified_rename_engine.state_manager.get_state.return_value = mock_state

        assert rename_controller.has_pending_changes() is False

    def test_has_pending_changes_no_engine(self):
        """Test has_pending_changes without engine."""
        controller = RenameController()
        assert controller.has_pending_changes() is False

    def test_get_current_state_success(self, rename_controller):
        """Test get_current_state returns state."""
        mock_state = MockRenameState()
        rename_controller._unified_rename_engine.state_manager.get_state.return_value = mock_state

        state = rename_controller.get_current_state()
        assert state is mock_state

    def test_get_current_state_no_engine(self):
        """Test get_current_state without engine."""
        controller = RenameController()
        assert controller.get_current_state() is None

    def test_clear_state_success(self, rename_controller):
        """Test clear_state clears cache."""
        rename_controller.clear_state()
        rename_controller._unified_rename_engine.clear_cache.assert_called_once()

    def test_clear_state_no_engine(self):
        """Test clear_state without engine (no error)."""
        controller = RenameController()
        controller.clear_state()  # Should not raise exception
