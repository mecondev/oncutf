
from modules.metadata_module import MetadataModule
from tests.mocks import MockFileItem

def test_metadata_module_basic():
    data = {"type": "metadata", "field": "date"}
    file_item = MockFileItem(date="2024-01-01")
    result = MetadataModule.apply_from_data(data, file_item)
    assert result == "2024-01-01"

def test_metadata_module_missing_field():
    data = {"type": "metadata", "field": "location"}
    file_item = MockFileItem(date="2024-01-01")
    result = MetadataModule.apply_from_data(data, file_item)
    assert result == "unknown"

def test_metadata_module_basic():
    data = {"type": "metadata", "field": "date"}
    file_item = MockFileItem(date="2024-01-01 15:30:00")
    result = MetadataModule.apply_from_data(data, file_item)
    assert result == "20240101"

def test_metadata_module_metadata_dict():
    data = {"type": "metadata", "field": "date"}
    metadata = {"FileModifyDate": "2024:01:01 15:30:00"}
    file_item = MockFileItem(metadata=metadata)
    result = MetadataModule.apply_from_data(data, file_item)
    assert result == "20240101"

def test_metadata_module_exif_style_date():
    data = {"type": "metadata", "field": "date"}
    metadata = {"DateTimeOriginal": "2024:05:12 10:00:00"}
    file_item = MockFileItem(metadata=metadata)
    result = MetadataModule.apply_from_data(data, file_item)
    assert result == "20240512"

def test_metadata_module_invalid_date_format():
    data = {"type": "metadata", "field": "date"}
    metadata = {"FileModifyDate": "12-05-2024 10:00"}  # wrong format
    file_item = MockFileItem(metadata=metadata)
    result = MetadataModule.apply_from_data(data, file_item)
    assert result == "invalid_date"

def test_metadata_module_date_with_timezone():
    data = {"type": "metadata", "field": "date"}
    metadata = {"FileModifyDate": "2024-05-12 10:00:00+03:00"}
    file_item = MockFileItem(metadata=metadata)
    result = MetadataModule.apply_from_data(data, file_item)
    assert result == "20240512"

def test_metadata_module_unknown_field_type():
    data = {"type": "metadata", "field": "camera_model"}
    metadata = {"Model": "Canon"}
    file_item = MockFileItem(metadata=metadata)
    result = MetadataModule.apply_from_data(data, file_item)
    assert result == "unknown"
