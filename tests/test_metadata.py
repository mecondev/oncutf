from modules.metadata_module import MetadataModule
from tests.mocks import MockFileItem


def test_metadata_from_date_attr():
    data = {"type": "metadata", "field": "date", "category": "metadata_keys"}
    file_item = MockFileItem()
    metadata_cache = {"/mock/path/mockfile.mp3": {"date": "2024-05-12 14:23:10"}}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    assert result == "2024-05-12 14:23:10"

def test_metadata_from_metadata_field():
    data = {"type": "metadata", "field": "FileModifyDate", "category": "metadata_keys"}
    file_item = MockFileItem()
    metadata_cache = {"/mock/path/mockfile.mp3": {"FileModifyDate": "2024:05:12 14:23:10+03:00"}}
    result = MetadataModule.apply_from_data(data, file_item, metadata_cache=metadata_cache)
    assert result == "2024:05:12 14:23:10+03:00"
