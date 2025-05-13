# tests/mocks.py

class MockFileItem:
    def __init__(self, *, filename="mockfile.mp3", date=None, metadata=None):
        self.filename = filename
        self.full_path = f"/mock/path/{filename}"
        self.date = date
        self.metadata = metadata or {}

