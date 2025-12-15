"""Unit tests for UnifiedPreviewManager helper methods.

Tests the extracted helper methods from the refactoring of
unified_rename_engine._generate_name_pairs to ensure correct behavior
and no regressions.

Author: AI Assistant
Date: 2025-12-09
"""

import pytest

from oncutf.core.unified_rename_engine import BatchQueryManager, SmartCacheManager, UnifiedPreviewManager


@pytest.fixture
def preview_manager():
    """Create a UnifiedPreviewManager instance for testing."""
    batch_query_manager = BatchQueryManager()
    cache_manager = SmartCacheManager()
    return UnifiedPreviewManager(batch_query_manager, cache_manager)


class TestStripExtensionFromFullname:
    """Test _strip_extension_from_fullname method."""

    def test_strip_extension_simple(self, preview_manager):
        """Test stripping simple extension."""
        result = preview_manager._strip_extension_from_fullname("photo.jpg", ".jpg")
        assert result == "photo"

    def test_strip_extension_case_insensitive(self, preview_manager):
        """Test stripping extension is case-insensitive."""
        result = preview_manager._strip_extension_from_fullname("photo.JPG", ".jpg")
        assert result == "photo"

    def test_strip_extension_no_match(self, preview_manager):
        """Test when extension doesn't match - returns original."""
        result = preview_manager._strip_extension_from_fullname("photo", ".jpg")
        assert result == "photo"

    def test_strip_extension_empty_extension(self, preview_manager):
        """Test with empty extension."""
        result = preview_manager._strip_extension_from_fullname("photo", "")
        assert result == "photo"

    def test_strip_extension_multiple_dots(self, preview_manager):
        """Test with filename containing multiple dots."""
        result = preview_manager._strip_extension_from_fullname("my.photo.jpg", ".jpg")
        assert result == "my.photo"

    def test_strip_extension_from_modified_name(self, preview_manager):
        """Test stripping extension from a generated name that includes it."""
        result = preview_manager._strip_extension_from_fullname("NewName.jpg", ".jpg")
        assert result == "NewName"


class TestApplyPostTransformIfNeeded:
    """Test _apply_post_transform_if_needed method."""

    def test_no_transform_returns_original(self, preview_manager):
        """Test when transform is not needed."""
        result = preview_manager._apply_post_transform_if_needed(
            "TestName", {"case": "upper"}, has_transform=False
        )
        assert result == "TestName"

    def test_uppercase_transform(self, preview_manager):
        """Test uppercase transform."""
        result = preview_manager._apply_post_transform_if_needed(
            "testname",
            {"case": "UPPER", "separator": "as-is", "greeklish": False},
            has_transform=True,
        )
        assert result == "TESTNAME"

    def test_lowercase_transform(self, preview_manager):
        """Test lowercase transform."""
        result = preview_manager._apply_post_transform_if_needed(
            "TESTNAME",
            {"case": "lower", "separator": "as-is", "greeklish": False},
            has_transform=True,
        )
        assert result == "testname"

    def test_title_case_transform(self, preview_manager):
        """Test title case transform."""
        result = preview_manager._apply_post_transform_if_needed(
            "test name",
            {"case": "Title Case", "separator": "as-is", "greeklish": False},
            has_transform=True,
        )
        assert result == "Test Name"

    def test_empty_basename(self, preview_manager):
        """Test with empty basename."""
        result = preview_manager._apply_post_transform_if_needed(
            "", {"case": "upper"}, has_transform=True
        )
        assert result == ""


class TestBuildFinalFilename:
    """Test _build_final_filename method."""

    def test_build_with_extension(self, preview_manager):
        """Test building filename with extension."""
        result = preview_manager._build_final_filename("photo", ".jpg")
        assert result == "photo.jpg"

    def test_build_without_extension(self, preview_manager):
        """Test building filename without extension."""
        result = preview_manager._build_final_filename("document", "")
        assert result == "document"

    def test_build_with_empty_basename(self, preview_manager):
        """Test with empty basename (edge case)."""
        result = preview_manager._build_final_filename("", ".txt")
        assert result == ".txt"

    def test_build_complex_basename(self, preview_manager):
        """Test with complex basename containing dots."""
        result = preview_manager._build_final_filename("my.file.name", ".txt")
        assert result == "my.file.name.txt"

    def test_build_with_long_extension(self, preview_manager):
        """Test with longer extension."""
        result = preview_manager._build_final_filename("archive", ".tar.gz")
        assert result == "archive.tar.gz"


class TestIsValidFilenameText:
    """Test _is_valid_filename_text method."""

    def test_valid_simple_name(self, preview_manager):
        """Test with simple valid name."""
        result = preview_manager._is_valid_filename_text("photo")
        assert result is True

    def test_valid_name_with_spaces(self, preview_manager):
        """Test with valid name containing spaces."""
        result = preview_manager._is_valid_filename_text("my photo")
        assert result is True

    def test_valid_name_with_numbers(self, preview_manager):
        """Test with valid name containing numbers."""
        result = preview_manager._is_valid_filename_text("photo123")
        assert result is True

    def test_valid_name_with_underscores(self, preview_manager):
        """Test with valid name containing underscores."""
        result = preview_manager._is_valid_filename_text("my_photo_2024")
        assert result is True

    def test_valid_name_with_hyphens(self, preview_manager):
        """Test with valid name containing hyphens."""
        result = preview_manager._is_valid_filename_text("my-photo-2024")
        assert result is True

    def test_valid_unicode_name(self, preview_manager):
        """Test with valid unicode name."""
        result = preview_manager._is_valid_filename_text("φωτογραφία")
        assert result is True


class TestIntegrationNamePairGeneration:
    """Integration tests for the complete name pair generation flow."""

    def test_complete_flow_simple(self, preview_manager):
        """Test complete flow with simple case."""
        # Simulate the flow
        fullname = "NewPhoto.jpg"
        extension = ".jpg"
        post_transform = {"case": "UPPER", "separator": "as-is", "greeklish": False}
        has_transform = True

        # Step 1: Strip extension
        basename = preview_manager._strip_extension_from_fullname(fullname, extension)
        assert basename == "NewPhoto"

        # Step 2: Apply transform
        basename = preview_manager._apply_post_transform_if_needed(
            basename, post_transform, has_transform
        )
        assert basename == "NEWPHOTO"

        # Step 3: Validate
        is_valid = preview_manager._is_valid_filename_text(basename)
        assert is_valid is True

        # Step 4: Build final
        final_name = preview_manager._build_final_filename(basename, extension)
        assert final_name == "NEWPHOTO.jpg"

    def test_complete_flow_no_transform(self, preview_manager):
        """Test complete flow without transform."""
        fullname = "Document"
        extension = ".txt"
        post_transform = {}
        has_transform = False

        basename = preview_manager._strip_extension_from_fullname(fullname, extension)
        assert basename == "Document"

        basename = preview_manager._apply_post_transform_if_needed(
            basename, post_transform, has_transform
        )
        assert basename == "Document"

        is_valid = preview_manager._is_valid_filename_text(basename)
        assert is_valid is True

        final_name = preview_manager._build_final_filename(basename, extension)
        assert final_name == "Document.txt"

    def test_complete_flow_no_extension(self, preview_manager):
        """Test complete flow with file without extension."""
        fullname = "README"
        extension = ""
        post_transform = {"case": "lower", "separator": "as-is", "greeklish": False}
        has_transform = True

        basename = preview_manager._strip_extension_from_fullname(fullname, extension)
        assert basename == "README"

        basename = preview_manager._apply_post_transform_if_needed(
            basename, post_transform, has_transform
        )
        assert basename == "readme"

        is_valid = preview_manager._is_valid_filename_text(basename)
        assert is_valid is True

        final_name = preview_manager._build_final_filename(basename, extension)
        assert final_name == "readme"

