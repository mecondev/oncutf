"""
Unit tests for MetadataExtractor.

Tests pure Python metadata extraction logic without UI dependencies.
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from oncutf.domain.metadata.extractor import ExtractionResult, MetadataExtractor


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("test content")
        temp_path = f.name

    yield Path(temp_path)

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def extractor():
    """Create a MetadataExtractor instance."""
    return MetadataExtractor()


class TestMetadataExtractorInit:
    """Test MetadataExtractor initialization."""

    def test_init(self):
        """Test extractor initializes correctly."""
        extractor = MetadataExtractor()
        assert extractor._cache == {}
        assert extractor._cache_timestamp == 0.0
        assert extractor._cache_validity_duration == 0.1

    def test_clear_cache(self):
        """Test cache clearing."""
        extractor = MetadataExtractor()
        extractor._cache["test"] = ExtractionResult(
            value="test", source="test", field="test", category="test"
        )
        extractor._cache_timestamp = 123.456

        extractor.clear_cache()

        assert extractor._cache == {}
        assert extractor._cache_timestamp == 0.0


class TestFilesystemDateExtraction:
    """Test filesystem date extraction."""

    def test_extract_last_modified_yymmdd(self, extractor, temp_file):
        """Test YYMMDD format extraction."""
        result = extractor.extract(temp_file, "last_modified_yymmdd", "file_dates")

        assert isinstance(result, ExtractionResult)
        assert result.source == "filesystem"
        assert result.category == "file_dates"
        assert result.field == "last_modified_yymmdd"
        assert len(result.value) == 6  # YYMMDD format
        assert result.value.isdigit()

    def test_extract_last_modified_iso(self, extractor, temp_file):
        """Test ISO date format extraction."""
        result = extractor.extract(temp_file, "last_modified_iso", "file_dates")

        assert result.source == "filesystem"
        assert len(result.value) == 10  # YYYY-MM-DD format
        assert result.value.count("-") == 2

        # Parse to verify format
        datetime.strptime(result.value, "%Y-%m-%d")

    def test_extract_last_modified_eu(self, extractor, temp_file):
        """Test EU date format extraction."""
        result = extractor.extract(temp_file, "last_modified_eu", "file_dates")

        assert result.source == "filesystem"
        assert len(result.value) == 10  # DD-MM-YYYY format
        assert result.value.count("-") == 2

        # Parse to verify format
        datetime.strptime(result.value, "%d-%m-%Y")

    def test_extract_last_modified_us(self, extractor, temp_file):
        """Test US date format extraction."""
        result = extractor.extract(temp_file, "last_modified_us", "file_dates")

        assert result.source == "filesystem"
        assert len(result.value) == 10  # MM-DD-YYYY format
        assert result.value.count("-") == 2

        # Parse to verify format
        datetime.strptime(result.value, "%m-%d-%Y")

    def test_extract_last_modified_year(self, extractor, temp_file):
        """Test year-only extraction."""
        result = extractor.extract(temp_file, "last_modified_year", "file_dates")

        assert result.source == "filesystem"
        assert len(result.value) == 4  # YYYY format
        assert result.value.isdigit()

    def test_extract_last_modified_month(self, extractor, temp_file):
        """Test year-month extraction."""
        result = extractor.extract(temp_file, "last_modified_month", "file_dates")

        assert result.source == "filesystem"
        assert len(result.value) == 7  # YYYY-MM format
        assert result.value.count("-") == 1

    def test_extract_last_modified_iso_time(self, extractor, temp_file):
        """Test ISO with time extraction."""
        result = extractor.extract(temp_file, "last_modified_iso_time", "file_dates")

        assert result.source == "filesystem"
        # Format: YYYY-MM-DD_HH-MM
        assert "_" in result.value
        date_part, time_part = result.value.split("_")
        assert len(date_part) == 10
        assert len(time_part) == 5

    def test_extract_last_modified_compact(self, extractor, temp_file):
        """Test compact format extraction."""
        result = extractor.extract(temp_file, "last_modified_compact", "file_dates")

        assert result.source == "filesystem"
        # Format: YYMMDD_HHMM
        assert "_" in result.value
        date_part, time_part = result.value.split("_")
        assert len(date_part) == 6
        assert len(time_part) == 4

    def test_extract_legacy_last_modified(self, extractor, temp_file):
        """Test legacy last_modified field."""
        result = extractor.extract(temp_file, "last_modified", "file_dates")

        assert result.source == "filesystem"
        assert len(result.value) == 10  # YYYY-MM-DD format
        datetime.strptime(result.value, "%Y-%m-%d")

    def test_extract_filesystem_date_nonexistent_file(self, extractor):
        """Test extraction from nonexistent file."""
        result = extractor.extract(Path("/nonexistent/file.txt"), "last_modified_iso", "file_dates")

        assert result.value == "invalid"
        assert result.source == "error"

    def test_extract_filesystem_date_unknown_format(self, extractor, temp_file):
        """Test extraction with unknown format falls back to YYMMDD."""
        result = extractor.extract(temp_file, "last_modified_unknown", "file_dates")

        # Should fallback to YYMMDD format
        assert result.source == "filesystem"
        assert len(result.value) == 6
        assert result.value.isdigit()


class TestHashExtraction:
    """Test hash extraction."""

    def test_extract_hash_valid_field(self, extractor, temp_file):
        """Test hash extraction with valid field."""
        # Note: This may return fallback if hash not computed
        result = extractor.extract(temp_file, "hash_crc32", "hash")

        assert isinstance(result, ExtractionResult)
        assert result.category == "hash"
        assert result.field == "hash_crc32"
        # Source could be 'hash' or 'fallback' depending on hash availability
        assert result.source in ["hash", "fallback"]

    def test_extract_hash_invalid_field(self, extractor, temp_file):
        """Test hash extraction with invalid field."""
        result = extractor.extract(temp_file, "invalid_field", "hash")

        assert result.value == "invalid"
        assert result.source == "error"

    def test_extract_hash_nonexistent_file(self, extractor):
        """Test hash extraction from nonexistent file."""
        result = extractor.extract(Path("/nonexistent/file.txt"), "hash_crc32", "hash")

        assert result.value == "invalid"
        assert result.source == "error"


class TestMetadataFieldExtraction:
    """Test metadata field extraction."""

    def test_extract_metadata_field_direct_access(self, extractor, temp_file):
        """Test direct metadata field access."""
        metadata = {"custom_field": "custom_value", "another_field": "another_value"}

        result = extractor.extract(temp_file, "custom_field", "metadata_keys", metadata=metadata)

        assert result.source == "exif"
        assert "custom_value" in result.value  # May be cleaned
        assert result.raw_value == "custom_value"

    def test_extract_metadata_field_legacy_creation_date(self, extractor, temp_file):
        """Test legacy creation_date field."""
        metadata = {"creation_date": "2025-12-17"}

        result = extractor.extract(temp_file, "creation_date", "metadata_keys", metadata=metadata)

        assert result.source == "exif"
        assert "2025" in result.value

    def test_extract_metadata_field_legacy_date_created(self, extractor, temp_file):
        """Test legacy date_created fallback."""
        metadata = {"date_created": "2025-12-17"}

        result = extractor.extract(temp_file, "creation_date", "metadata_keys", metadata=metadata)

        assert result.source == "exif"
        assert "2025" in result.value

    def test_extract_metadata_field_legacy_date(self, extractor, temp_file):
        """Test legacy date field."""
        metadata = {"date": "2025-12-17"}

        result = extractor.extract(temp_file, "date", "metadata_keys", metadata=metadata)

        assert result.source == "exif"
        assert "2025" in result.value

    def test_extract_metadata_field_missing(self, extractor, temp_file):
        """Test extraction of missing metadata field."""
        metadata = {"existing_field": "value"}

        result = extractor.extract(temp_file, "missing_field", "metadata_keys", metadata=metadata)

        # Should fallback to filename
        assert result.source == "fallback"
        assert result.value == temp_file.stem

    def test_extract_metadata_field_no_metadata(self, extractor, temp_file):
        """Test extraction with no metadata provided."""
        result = extractor.extract(temp_file, "some_field", "metadata_keys")

        # Should fallback to filename
        assert result.source == "fallback"
        assert result.value == temp_file.stem


class TestFilenameCleaning:
    """Test filename cleaning functionality."""

    def test_clean_for_filename_basic(self, extractor):
        """Test basic filename cleaning."""
        result = extractor.clean_for_filename("simple_text")
        assert result == "simple_text"

    def test_clean_for_filename_spaces(self, extractor):
        """Test cleaning spaces."""
        result = extractor.clean_for_filename("text with spaces")
        assert result == "text_with_spaces"
        assert " " not in result

    def test_clean_for_filename_multiple_spaces(self, extractor):
        """Test cleaning multiple spaces."""
        result = extractor.clean_for_filename("text  with   multiple    spaces")
        assert result == "text_with_multiple_spaces"

    def test_clean_for_filename_invalid_chars(self, extractor):
        """Test cleaning invalid Windows characters."""
        invalid = 'test<>:"/\\|?*file'
        result = extractor.clean_for_filename(invalid)

        # All invalid chars should be replaced
        for char in '<>:"/\\|?*':
            assert char not in result

    def test_clean_for_filename_colons(self, extractor):
        """Test cleaning colons (common in timestamps)."""
        result = extractor.clean_for_filename("2025:12:17 14:30:00")
        assert ":" not in result
        assert "_" in result

    def test_clean_for_filename_leading_trailing_underscores(self, extractor):
        """Test removal of leading/trailing underscores."""
        result = extractor.clean_for_filename("  test  ")
        assert not result.startswith("_")
        assert not result.endswith("_")

    def test_clean_for_filename_empty(self, extractor):
        """Test cleaning empty string."""
        result = extractor.clean_for_filename("")
        assert result == ""

    def test_clean_for_filename_unicode(self, extractor):
        """Test cleaning Unicode characters."""
        result = extractor.clean_for_filename("test→file•with✓symbols")
        # Should not contain the original Unicode symbols
        assert "→" not in result
        assert "•" not in result
        assert "✓" not in result
        # Should have underscores or be cleaned
        assert "_" in result or result.replace("_", "").isalnum()


class TestGetAvailableFields:
    """Test get_available_fields method."""

    def test_get_available_fields_file_dates(self, extractor):
        """Test getting available file date fields."""
        fields = extractor.get_available_fields("file_dates")

        assert isinstance(fields, list)
        assert len(fields) > 0
        assert "last_modified_iso" in fields
        assert "last_modified_yymmdd" in fields
        assert "last_modified_eu" in fields

    def test_get_available_fields_hash(self, extractor):
        """Test getting available hash fields."""
        fields = extractor.get_available_fields("hash")

        assert isinstance(fields, list)
        assert "hash_crc32" in fields

    def test_get_available_fields_metadata_keys(self, extractor):
        """Test getting available metadata fields."""
        fields = extractor.get_available_fields("metadata_keys")

        assert isinstance(fields, list)
        # Should return common fields
        assert len(fields) > 0

    def test_get_available_fields_unknown_category(self, extractor):
        """Test getting fields for unknown category."""
        fields = extractor.get_available_fields("unknown_category")

        assert fields == []


class TestCaching:
    """Test caching behavior."""

    def test_cache_hit(self, extractor, temp_file):
        """Test cache hit on repeated extraction."""
        # First call - should cache
        result1 = extractor.extract(temp_file, "last_modified_iso", "file_dates")

        # Second call - should hit cache
        result2 = extractor.extract(temp_file, "last_modified_iso", "file_dates")

        assert result1.value == result2.value
        assert len(extractor._cache) > 0

    def test_cache_different_fields(self, extractor, temp_file):
        """Test cache with different fields."""
        result1 = extractor.extract(temp_file, "last_modified_iso", "file_dates")
        result2 = extractor.extract(temp_file, "last_modified_yymmdd", "file_dates")

        # Different fields should create different cache entries
        assert len(extractor._cache) == 2
        assert result1.value != result2.value

    def test_cache_clear(self, extractor, temp_file):
        """Test cache clearing."""
        # Populate cache
        extractor.extract(temp_file, "last_modified_iso", "file_dates")
        assert len(extractor._cache) > 0

        # Clear cache
        extractor.clear_cache()
        assert len(extractor._cache) == 0


class TestInputValidation:
    """Test input validation."""

    def test_extract_with_empty_field(self, extractor, temp_file):
        """Test extraction with empty field."""
        result = extractor.extract(temp_file, "", "file_dates")

        assert result.value == "invalid"
        assert result.source == "error"

    def test_extract_with_nonexistent_file(self, extractor):
        """Test extraction with nonexistent file."""
        result = extractor.extract(Path("/does/not/exist.txt"), "last_modified_iso", "file_dates")

        assert result.value == "invalid"
        assert result.source == "error"

    def test_extract_with_string_path(self, extractor, temp_file):
        """Test extraction with string path (should work)."""
        result = extractor.extract(str(temp_file), "last_modified_iso", "file_dates")

        assert result.source == "filesystem"
        assert result.value != "invalid"


class TestExtractionResult:
    """Test ExtractionResult dataclass."""

    def test_extraction_result_creation(self):
        """Test creating ExtractionResult."""
        result = ExtractionResult(
            value="test_value",
            source="test_source",
            raw_value=123,
            field="test_field",
            category="test_category",
        )

        assert result.value == "test_value"
        assert result.source == "test_source"
        assert result.raw_value == 123
        assert result.field == "test_field"
        assert result.category == "test_category"

    def test_extraction_result_defaults(self):
        """Test ExtractionResult default values."""
        result = ExtractionResult(value="test", source="test")

        assert result.value == "test"
        assert result.source == "test"
        assert result.raw_value is None
        assert result.field == ""
        assert result.category == ""


class TestMetadataExtractorDependencyInjection:
    """Tests for service dependency injection."""

    def test_init_with_services(self):
        """Test initialization with injected services."""

        # Create mock services
        class MockMetadataService:
            def load_metadata(self, path):  # noqa: ARG002
                return {"test": "value"}

            def load_metadata_batch(self, paths):  # noqa: ARG002
                return {}

        class MockHashService:
            def compute_hash(self, path, algorithm="crc32"):  # noqa: ARG002
                return "abc12345"

            def compute_hashes_batch(self, paths, algorithm="crc32"):  # noqa: ARG002
                return {}

        metadata_svc = MockMetadataService()
        hash_svc = MockHashService()

        extractor = MetadataExtractor(
            metadata_service=metadata_svc,
            hash_service=hash_svc,
        )

        assert extractor._metadata_service is metadata_svc
        assert extractor._hash_service is hash_svc

    def test_extract_hash_uses_injected_service(self, temp_file):
        """Test that hash extraction uses injected service."""

        class MockHashService:
            call_count = 0

            def compute_hash(self, path, algorithm="crc32"):  # noqa: ARG002
                self.call_count += 1
                return "injected_hash"

            def compute_hashes_batch(self, paths, algorithm="crc32"):  # noqa: ARG002
                return {}

        mock_service = MockHashService()
        extractor = MetadataExtractor(hash_service=mock_service)

        result = extractor.extract(temp_file, "hash_crc32", category="hash")

        assert result.value == "injected_hash"
        assert mock_service.call_count == 1

    def test_extract_hash_fallback_without_service(self, temp_file):
        """Test that hash extraction works without injected service."""
        # Without service, falls back to internal implementation
        extractor = MetadataExtractor()

        result = extractor.extract(temp_file, "hash_crc32", category="hash")

        # Should still return a hash (from internal implementation)
        assert result.source in ("hash", "fallback")
