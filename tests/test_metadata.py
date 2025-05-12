from modules.metadata_module import MetadataModule

class DummyFile:
    def __init__(self, date=None, metadata=None):
        self.date = date
        self.metadata = metadata or {}
        self.filename = "test.jpg"

def test_metadata_from_date_attr():
    file = DummyFile(date="2024-05-12 14:23:10")
    data = {"type": "metadata", "field": "date"}
    assert MetadataModule.apply_from_data(data, file) == "20240512"

def test_metadata_from_metadata_field():
    file = DummyFile(metadata={"FileModifyDate": "2024:05:12 14:23:10+03:00"})
    data = {"type": "metadata", "field": "date"}
    assert MetadataModule.apply_from_data(data, file) == "20240512"
