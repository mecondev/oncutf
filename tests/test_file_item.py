import os
from datetime import datetime

from models.file_item import FileItem


def test_fileitem_from_path_and_size(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello world")

    fi = FileItem.from_path(str(p))
    assert fi.filename == "a.txt"
    assert fi.size == os.path.getsize(p)
    assert isinstance(fi.modified, datetime)
    # human readable string
    s = fi.get_human_readable_size()
    assert isinstance(s, str) and len(s) > 0


def test_metadata_flags():
    fi = FileItem("/tmp/x.txt", "txt", datetime.fromtimestamp(0))
    assert not fi.has_metadata
    fi.metadata = {"a": 1}
    assert fi.has_metadata
    fi.metadata = {"__extended__": True}
    assert fi.metadata_extended
