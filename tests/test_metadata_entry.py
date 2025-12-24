"""test_metadata_entry.py

Test suite for MetadataEntry dataclass.
"""

import time

from oncutf.models.metadata_entry import MetadataEntry


class TestMetadataEntryCreation:
    """Test MetadataEntry creation and initialization."""

    def test_basic_creation(self):
        """Test creating MetadataEntry with minimum fields."""
        data = {"Title": "Test Image", "Artist": "John Doe"}
        entry = MetadataEntry(data=data)

        assert entry.data == data
        assert not entry.is_extended
        assert not entry.modified
        assert isinstance(entry.timestamp, float)

    def test_creation_with_all_fields(self):
        """Test creating MetadataEntry with all fields."""
        data = {"Title": "Test", "EXIF": {"DateTimeOriginal": "2024:01:01 12:00:00"}}
        timestamp = time.time()

        entry = MetadataEntry(
            data=data,
            is_extended=True,
            modified=True,
            timestamp=timestamp,
        )

        assert entry.is_extended
        assert entry.modified
        assert entry.timestamp == timestamp

    def test_cleans_internal_markers(self):
        """Test that internal markers are cleaned on init."""
        data = {
            "Title": "Test",
            "__extended__": True,
            "__modified__": True,
            "Artist": "John",
        }

        entry = MetadataEntry(data=data)

        assert "__extended__" not in entry.data
        assert "__modified__" not in entry.data
        assert "Title" in entry.data
        assert "Artist" in entry.data

    def test_invalid_data_type(self):
        """Test handling of invalid data type."""
        entry = MetadataEntry(data="not a dict")  # type: ignore
        assert entry.data == {}


class TestMetadataEntryFactoryMethods:
    """Test MetadataEntry factory methods."""

    def test_create_fast(self):
        """Test create_fast factory method."""
        data = {"Title": "Test"}
        entry = MetadataEntry.create_fast(data)

        assert entry.data == data
        assert not entry.is_extended

    def test_create_extended(self):
        """Test create_extended factory method."""
        data = {"Title": "Test", "EXIF": {"DateTimeOriginal": "2024:01:01"}}
        entry = MetadataEntry.create_extended(data)

        assert entry.data == data
        assert entry.is_extended

    def test_from_dict(self):
        """Test from_dict factory method."""
        dict_data = {
            "data": {"Title": "Test"},
            "is_extended": True,
            "modified": True,
            "timestamp": 123456.789,
        }

        entry = MetadataEntry.from_dict(dict_data)

        assert entry.data == {"Title": "Test"}
        assert entry.is_extended
        assert entry.modified
        assert entry.timestamp == 123456.789


class TestMetadataEntryFieldOperations:
    """Test MetadataEntry field get/set/remove operations."""

    def test_has_field_top_level(self):
        """Test has_field with top-level field."""
        entry = MetadataEntry(data={"Title": "Test", "Artist": "John"})

        assert entry.has_field("Title")
        assert entry.has_field("Artist")
        assert not entry.has_field("NonExistent")

    def test_has_field_nested(self):
        """Test has_field with nested field."""
        entry = MetadataEntry(data={"EXIF": {"DateTimeOriginal": "2024:01:01", "Model": "Camera"}})

        assert entry.has_field("EXIF/DateTimeOriginal")
        assert entry.has_field("EXIF/Model")
        assert not entry.has_field("EXIF/NonExistent")
        assert not entry.has_field("NonExistent/Field")

    def test_get_field_top_level(self):
        """Test get_field with top-level field."""
        entry = MetadataEntry(data={"Title": "Test Image"})

        assert entry.get_field("Title") == "Test Image"
        assert entry.get_field("NonExistent") is None
        assert entry.get_field("NonExistent", "default") == "default"

    def test_get_field_nested(self):
        """Test get_field with nested field."""
        entry = MetadataEntry(data={"EXIF": {"DateTimeOriginal": "2024:01:01", "Model": "Camera"}})

        assert entry.get_field("EXIF/DateTimeOriginal") == "2024:01:01"
        assert entry.get_field("EXIF/Model") == "Camera"
        assert entry.get_field("EXIF/NonExistent") is None
        assert entry.get_field("EXIF/NonExistent", "default") == "default"

    def test_set_field_top_level(self):
        """Test set_field with top-level field."""
        entry = MetadataEntry(data={"Title": "Original"})

        entry.set_field("Title", "Updated")
        assert entry.get_field("Title") == "Updated"
        assert entry.modified

        entry.set_field("NewField", "New Value")
        assert entry.get_field("NewField") == "New Value"

    def test_set_field_nested(self):
        """Test set_field with nested field."""
        entry = MetadataEntry(data={"EXIF": {"Model": "Camera"}})

        entry.set_field("EXIF/Model", "New Camera")
        assert entry.get_field("EXIF/Model") == "New Camera"
        assert entry.modified

        # Create new group
        entry.set_field("GPS/Latitude", "40.7128")
        assert entry.get_field("GPS/Latitude") == "40.7128"

    def test_remove_field_top_level(self):
        """Test remove_field with top-level field."""
        entry = MetadataEntry(data={"Title": "Test", "Artist": "John"})

        assert entry.remove_field("Title")
        assert not entry.has_field("Title")
        assert entry.has_field("Artist")
        assert entry.modified

        # Remove non-existent field
        assert not entry.remove_field("NonExistent")

    def test_remove_field_nested(self):
        """Test remove_field with nested field."""
        entry = MetadataEntry(data={"EXIF": {"Model": "Camera", "Make": "Canon"}})

        assert entry.remove_field("EXIF/Model")
        assert not entry.has_field("EXIF/Model")
        assert entry.has_field("EXIF/Make")
        assert entry.modified


class TestMetadataEntryProperties:
    """Test MetadataEntry properties."""

    def test_field_count_simple(self):
        """Test field_count with simple metadata."""
        entry = MetadataEntry(data={"Title": "Test", "Artist": "John", "Date": "2024"})
        assert entry.field_count == 3

    def test_field_count_nested(self):
        """Test field_count with nested metadata."""
        entry = MetadataEntry(
            data={
                "Title": "Test",
                "EXIF": {"Model": "Camera", "Make": "Canon", "DateTimeOriginal": "2024"},
            }
        )
        # 1 top-level + 3 nested = 4
        assert entry.field_count == 4

    def test_is_empty(self):
        """Test is_empty property."""
        entry1 = MetadataEntry(data={})
        assert entry1.is_empty

        entry2 = MetadataEntry(data={"Title": "Test"})
        assert not entry2.is_empty

        # Internal markers don't count
        entry3 = MetadataEntry(data={"__extended__": True})
        assert entry3.is_empty

    def test_age_seconds(self):
        """Test age_seconds property."""
        entry = MetadataEntry(data={"Title": "Test"})

        # Age should be very small (just created)
        assert 0 <= entry.age_seconds < 1

        # Test with old timestamp
        entry.timestamp = time.time() - 100
        assert 99 < entry.age_seconds < 101


class TestMetadataEntrySerialization:
    """Test MetadataEntry serialization methods."""

    def test_to_dict(self):
        """Test to_dict serialization."""
        data = {"Title": "Test", "EXIF": {"Model": "Camera"}}
        entry = MetadataEntry(data=data, is_extended=True, modified=True)

        result = entry.to_dict()

        assert result["data"] == data
        assert result["is_extended"]
        assert result["modified"]
        assert "timestamp" in result
        assert "field_count" in result
        assert "age_seconds" in result

    def test_to_database_dict(self):
        """Test to_database_dict cleans internal markers."""
        data = {
            "Title": "Test",
            "__extended__": True,
            "__modified__": True,
            "Artist": "John",
        }

        entry = MetadataEntry(data=data)
        db_dict = entry.to_database_dict()

        assert "__extended__" not in db_dict
        assert "__modified__" not in db_dict
        assert "Title" in db_dict
        assert "Artist" in db_dict


class TestMetadataEntryStringRepresentation:
    """Test MetadataEntry string representations."""

    def test_str(self):
        """Test __str__ representation."""
        entry = MetadataEntry(data={"Title": "Test", "Artist": "John"})
        str_repr = str(entry)

        assert "MetadataEntry" in str_repr
        assert "2 fields" in str_repr

    def test_repr(self):
        """Test __repr__ representation."""
        entry = MetadataEntry(data={"Title": "Test"}, is_extended=True, modified=True)
        repr_str = repr(entry)

        assert "MetadataEntry" in repr_str
        assert "extended=True" in repr_str
        assert "modified=True" in repr_str
        assert "fields=" in repr_str


class TestMetadataEntryEdgeCases:
    """Test MetadataEntry edge cases."""

    def test_nested_field_overwrites_non_dict(self):
        """Test that setting nested field converts non-dict groups to dict."""
        entry = MetadataEntry(data={"EXIF": "not a dict"})

        entry.set_field("EXIF/Model", "Camera")
        assert entry.get_field("EXIF/Model") == "Camera"
        assert isinstance(entry.data["EXIF"], dict)

    def test_timestamp_updates_on_modification(self):
        """Test that timestamp updates when metadata is modified."""
        entry = MetadataEntry(data={"Title": "Test"})
        original_timestamp = entry.timestamp

        time.sleep(0.01)  # Small delay
        entry.set_field("Title", "Updated")

        assert entry.timestamp > original_timestamp

    def test_multiple_modifications(self):
        """Test multiple modifications maintain modified flag."""
        entry = MetadataEntry(data={"Title": "Test"})

        assert not entry.modified

        entry.set_field("Title", "Updated")
        assert entry.modified

        entry.set_field("Artist", "John")
        assert entry.modified

        entry.remove_field("Artist")
        assert entry.modified
