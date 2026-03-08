"""Unit tests for NameComposer helper methods.

Tests the helper methods used during name composition to ensure correct
behavior and no regressions.

Originally tested as private methods on UnifiedPreviewManager; now
extracted to NameComposer.

Author: AI Assistant
Date: 2025-12-09
Updated: 2026-03-08 (retargeted to NameComposer after extraction)
"""

import pytest

from oncutf.core.rename.name_composer import NameComposer


@pytest.fixture
def composer():
    """Create a NameComposer instance for testing."""
    return NameComposer()


class TestStripExtensionFromFullname:
    """Test _strip_extension_from_fullname method."""

    def test_strip_extension_simple(self, composer):
        """Test stripping simple extension."""
        result = composer.strip_extension("photo.jpg", ".jpg")
        assert result == "photo"

    def test_strip_extension_case_insensitive(self, composer):
        """Test stripping extension is case-insensitive."""
        result = composer.strip_extension("photo.JPG", ".jpg")
        assert result == "photo"

    def test_strip_extension_no_match(self, composer):
        """Test when extension doesn't match - returns original."""
        result = composer.strip_extension("photo", ".jpg")
        assert result == "photo"

    def test_strip_extension_empty_extension(self, composer):
        """Test with empty extension."""
        result = composer.strip_extension("photo", "")
        assert result == "photo"

    def test_strip_extension_multiple_dots(self, composer):
        """Test with filename containing multiple dots."""
        result = composer.strip_extension("my.photo.jpg", ".jpg")
        assert result == "my.photo"

    def test_strip_extension_from_modified_name(self, composer):
        """Test stripping extension from a generated name that includes it."""
        result = composer.strip_extension("NewName.jpg", ".jpg")
        assert result == "NewName"


class TestApplyPostTransformIfNeeded:
    """Test _apply_post_transform_if_needed method."""

    def test_no_transform_returns_original(self, composer):
        """Test when transform is not needed."""
        result = composer.apply_post_transform("TestName", {"case": "upper"}, has_transform=False)
        assert result == "TestName"

    def test_uppercase_transform(self, composer):
        """Test uppercase transform."""
        result = composer.apply_post_transform(
            "testname",
            {"case": "UPPER", "separator": "as-is", "greeklish": False},
            has_transform=True,
        )
        assert result == "TESTNAME"

    def test_lowercase_transform(self, composer):
        """Test lowercase transform."""
        result = composer.apply_post_transform(
            "TESTNAME",
            {"case": "lower", "separator": "as-is", "greeklish": False},
            has_transform=True,
        )
        assert result == "testname"

    def test_title_case_transform(self, composer):
        """Test title case transform."""
        result = composer.apply_post_transform(
            "test name",
            {"case": "Title Case", "separator": "as-is", "greeklish": False},
            has_transform=True,
        )
        assert result == "Test Name"

    def test_empty_basename(self, composer):
        """Test with empty basename."""
        result = composer.apply_post_transform("", {"case": "upper"}, has_transform=True)
        assert result == ""


class TestBuildFinalFilename:
    """Test _build_final_filename method."""

    def test_build_with_extension(self, composer):
        """Test building filename with extension."""
        result = composer.build_final_filename("photo", ".jpg")
        assert result == "photo.jpg"

    def test_build_without_extension(self, composer):
        """Test building filename without extension."""
        result = composer.build_final_filename("document", "")
        assert result == "document"

    def test_build_with_empty_basename(self, composer):
        """Test with empty basename (edge case)."""
        result = composer.build_final_filename("", ".txt")
        assert result == ".txt"

    def test_build_complex_basename(self, composer):
        """Test with complex basename containing dots."""
        result = composer.build_final_filename("my.file.name", ".txt")
        assert result == "my.file.name.txt"

    def test_build_with_long_extension(self, composer):
        """Test with longer extension."""
        result = composer.build_final_filename("archive", ".tar.gz")
        assert result == "archive.tar.gz"


class TestIsValidFilenameText:
    """Test _is_valid_filename_text method."""

    def test_valid_simple_name(self, composer):
        """Test with simple valid name."""
        result = composer.is_valid_filename_text("photo")
        assert result is True

    def test_valid_name_with_spaces(self, composer):
        """Test with valid name containing spaces."""
        result = composer.is_valid_filename_text("my photo")
        assert result is True

    def test_valid_name_with_numbers(self, composer):
        """Test with valid name containing numbers."""
        result = composer.is_valid_filename_text("photo123")
        assert result is True

    def test_valid_name_with_underscores(self, composer):
        """Test with valid name containing underscores."""
        result = composer.is_valid_filename_text("my_photo_2024")
        assert result is True

    def test_valid_name_with_hyphens(self, composer):
        """Test with valid name containing hyphens."""
        result = composer.is_valid_filename_text("my-photo-2024")
        assert result is True

    def test_valid_unicode_name(self, composer):
        """Test with valid unicode name."""
        result = composer.is_valid_filename_text("φωτογραφία")
        assert result is True


class TestIntegrationNamePairGeneration:
    """Integration tests for the complete name pair generation flow."""

    def test_complete_flow_simple(self, composer):
        """Test complete flow with simple case."""
        # Simulate the flow
        fullname = "NewPhoto.jpg"
        extension = ".jpg"
        post_transform = {"case": "UPPER", "separator": "as-is", "greeklish": False}
        has_transform = True

        # Step 1: Strip extension
        basename = composer.strip_extension(fullname, extension)
        assert basename == "NewPhoto"

        # Step 2: Apply transform
        basename = composer.apply_post_transform(basename, post_transform, has_transform)
        assert basename == "NEWPHOTO"

        # Step 3: Validate
        is_valid = composer.is_valid_filename_text(basename)
        assert is_valid is True

        # Step 4: Build final
        final_name = composer.build_final_filename(basename, extension)
        assert final_name == "NEWPHOTO.jpg"

    def test_complete_flow_no_transform(self, composer):
        """Test complete flow without transform."""
        fullname = "Document"
        extension = ".txt"
        post_transform = {}
        has_transform = False

        basename = composer.strip_extension(fullname, extension)
        assert basename == "Document"

        basename = composer.apply_post_transform(basename, post_transform, has_transform)
        assert basename == "Document"

        is_valid = composer.is_valid_filename_text(basename)
        assert is_valid is True

        final_name = composer.build_final_filename(basename, extension)
        assert final_name == "Document.txt"

    def test_complete_flow_no_extension(self, composer):
        """Test complete flow with file without extension."""
        fullname = "README"
        extension = ""
        post_transform = {"case": "lower", "separator": "as-is", "greeklish": False}
        has_transform = True

        basename = composer.strip_extension(fullname, extension)
        assert basename == "README"

        basename = composer.apply_post_transform(basename, post_transform, has_transform)
        assert basename == "readme"

        is_valid = composer.is_valid_filename_text(basename)
        assert is_valid is True

        final_name = composer.build_final_filename(basename, extension)
        assert final_name == "readme"
