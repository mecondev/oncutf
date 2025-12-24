import unicodedata

from oncutf.utils import transform_utils


def test_strip_accents():
    s = "Άά Έέ Ήή"
    out = transform_utils.strip_accents(s)
    # No combining marks should remain
    assert all(unicodedata.category(c) != "Mn" for c in out)


def test_safe_upper_basic():
    """Tests for utils.transform_utils.

    This module consolidates transform-related tests and removes duplicate blocks.
    """

    import unicodedata

    import pytest

    from oncutf.utils.transform_utils import (
        apply_transform,
        safe_upper,
        strip_accents,
        to_greeklish,
    )

    def test_strip_accents_no_combining_marks():
        s = "Άά Έέ Ήή"
        out = strip_accents(s)
        assert all(unicodedata.category(c) != "Mn" for c in out)

    def test_strip_accents_specific():
        assert strip_accents("Άέή") == "Αεη"

    def test_safe_upper_behavior():
        assert safe_upper("test") == "TEST"
        # preserve initial accented vowel
        assert safe_upper("άλφα")[0] == "Ά"
        assert safe_upper("beta") == "BETA"

    def test_to_greeklish_mappings():
        assert to_greeklish("μπαμπά") == "baba"
        assert to_greeklish("μπ") == "b"
        assert "th" in to_greeklish("θήτα")
        assert to_greeklish("αβγ") == "avg"

    @pytest.mark.parametrize(
        "input_str, transform, expected",
        [
            (" hello world ", "original", "hello world"),
            ("Hello WORLD", "lower", "hello world"),
            ("hello world", "UPPER", "HELLO WORLD"),
            ("my file name", "camelCase", "myFileName"),
            ("my file name", "PascalCase", "MyFileName"),
            ("a  b   c", "snake_case", "a_b_c"),
            ("My File Name", "snake_case", "My_File_Name"),
            ("My File Name", "kebab-case", "My-File-Name"),
            ("", "snake_case", ""),
            ("Test--Name__Mix", "snake_case", "Test-Name_Mix"),
            ("Symbols@!$%", "kebab-case", "Symbols@!$%"),
        ],
    )
    def test_apply_transform_parametrized(input_str, transform, expected):
        assert apply_transform(input_str, transform) == expected

    def test_snake_and_kebab_and_space_special_cases():
        s = "  a   b__c--d  "
        # preserves leading/trailing converted separators and collapses duplicates
        assert apply_transform(s, "snake_case") == "_a_b_c-d_"
        assert apply_transform(s, "kebab-case") == "-a-b_c-d-"
        res = apply_transform("__a-b__c--", "space")
        assert " " in res and res.strip().startswith("a")

    def test_greeklish_ascii_and_passthrough():
        greek = "Καλημέρα Ελλάδα"
        out = apply_transform(greek, "greeklish")
        assert isinstance(out, str)
        assert all(ord(c) < 128 for c in out)

        latin = "already_latin_text"
        assert apply_transform(latin, "greeklish") == latin
