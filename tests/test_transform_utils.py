import pytest
from utils.transform_utils import apply_transform

@pytest.mark.parametrize("name, transform, expected", [
    ("My File Name", "original", "My File Name"),
    ("My File Name", "lower", "my file name"),
    ("My File Name", "upper", "MY FILE NAME"),
    ("My File Name", "snake_case", "my_file_name"),
    ("My File Name", "kebab_case", "my-file-name"),
    ("", "snake_case", ""),
    ("Test--Name__Mix", "snake_case", "test_name_mix"),
    ("Symbols@!$%", "kebab_case", "symbols")
])
def test_apply_transform_basic(name, transform, expected):
    assert apply_transform(name, transform) == expected

def test_apply_transform_greeklish():
    greek = "Καλημέρα Ελλάδα"
    result = apply_transform(greek, "greeklish")
    assert isinstance(result, str)
    assert all(c.isascii() for c in result)
    assert "κ" not in result.lower() and "λ" not in result.lower()

def test_apply_transform_greeklish_passthrough():
    latin = "already_latin_text"
    result = apply_transform(latin, "greeklish")
    assert result == latin
