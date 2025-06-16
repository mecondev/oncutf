from modules.specified_text_module import SpecifiedTextModule


def test_specified_text_simple():
    data = {"type": "specified_text", "text": "hello"}
    result = SpecifiedTextModule.apply_from_data(data, file_item=None)
    assert result == "hello"

def test_specified_text_invalid():
    data = {"type": "specified_text", "text": "file/name"}
    result = SpecifiedTextModule.apply_from_data(data, file_item=None)
    from config import INVALID_FILENAME_MARKER
    assert result == INVALID_FILENAME_MARKER
