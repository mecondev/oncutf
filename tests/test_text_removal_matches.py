"""Test module for TextRemovalMatch and find_matches/apply_removal methods.

Author: Michael Economou
Date: 2025-12-18
"""

import pytest

from oncutf.modules.text_removal_module import TextRemovalMatch, TextRemovalModule


class TestTextRemovalMatch:
    """Test cases for TextRemovalMatch dataclass."""

    def test_match_creation(self):
        """Test creating a TextRemovalMatch."""
        match = TextRemovalMatch(start=5, end=10, matched_text="_copy")
        assert match.start == 5
        assert match.end == 10
        assert match.matched_text == "_copy"


class TestFindMatches:
    """Test cases for find_matches method."""

    def test_end_of_name_match(self):
        """Test finding match at end of name."""
        matches = TextRemovalModule.find_matches(
            "document_copy", "_copy", position="End of name", case_sensitive=False
        )
        assert len(matches) == 1
        assert matches[0].start == 8
        assert matches[0].end == 13
        assert matches[0].matched_text == "_copy"

    def test_end_of_name_no_match(self):
        """Test no match when pattern not at end."""
        matches = TextRemovalModule.find_matches(
            "copy_document", "_copy", position="End of name", case_sensitive=False
        )
        assert len(matches) == 0

    def test_start_of_name_match(self):
        """Test finding match at start of name."""
        matches = TextRemovalModule.find_matches(
            "backup_document", "backup_", position="Start of name", case_sensitive=False
        )
        assert len(matches) == 1
        assert matches[0].start == 0
        assert matches[0].end == 7
        assert matches[0].matched_text == "backup_"

    def test_start_of_name_no_match(self):
        """Test no match when pattern not at start."""
        matches = TextRemovalModule.find_matches(
            "document_backup", "backup_", position="Start of name", case_sensitive=False
        )
        assert len(matches) == 0

    def test_anywhere_first_match(self):
        """Test finding first match anywhere."""
        matches = TextRemovalModule.find_matches(
            "test_old_file_old",
            "_old",
            position="Anywhere (first)",
            case_sensitive=False,
        )
        assert len(matches) == 1
        assert matches[0].start == 4
        assert matches[0].end == 8
        assert matches[0].matched_text == "_old"

    def test_anywhere_all_matches(self):
        """Test finding all matches anywhere."""
        matches = TextRemovalModule.find_matches(
            "test_old_file_old", "_old", position="Anywhere (all)", case_sensitive=False
        )
        assert len(matches) == 2
        assert matches[0].start == 4
        assert matches[0].end == 8
        assert matches[0].matched_text == "_old"
        assert matches[1].start == 13
        assert matches[1].end == 17
        assert matches[1].matched_text == "_old"

    def test_case_sensitive_match(self):
        """Test case-sensitive matching."""
        matches = TextRemovalModule.find_matches(
            "Document_COPY", "_COPY", position="End of name", case_sensitive=True
        )
        assert len(matches) == 1
        assert matches[0].matched_text == "_COPY"

    def test_case_sensitive_no_match(self):
        """Test case-sensitive no match when case differs."""
        matches = TextRemovalModule.find_matches(
            "Document_COPY", "_copy", position="End of name", case_sensitive=True
        )
        assert len(matches) == 0

    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        matches = TextRemovalModule.find_matches(
            "Document_COPY", "_copy", position="End of name", case_sensitive=False
        )
        assert len(matches) == 1
        assert matches[0].matched_text == "_COPY"

    def test_empty_pattern(self):
        """Test with empty pattern returns no matches."""
        matches = TextRemovalModule.find_matches(
            "document", "", position="End of name", case_sensitive=False
        )
        assert len(matches) == 0

    def test_overlapping_matches_not_found(self):
        """Test that overlapping matches are handled correctly."""
        matches = TextRemovalModule.find_matches(
            "aaaa", "aa", position="Anywhere (all)", case_sensitive=False
        )
        assert len(matches) == 2
        assert matches[0].start == 0
        assert matches[0].end == 2
        assert matches[1].start == 2
        assert matches[1].end == 4

    def test_special_characters_in_pattern(self):
        """Test pattern with special regex characters."""
        matches = TextRemovalModule.find_matches(
            "file[1].txt", "[1]", position="Anywhere (first)", case_sensitive=False
        )
        assert len(matches) == 1
        assert matches[0].matched_text == "[1]"

    def test_unicode_pattern(self):
        """Test pattern with unicode characters."""
        matches = TextRemovalModule.find_matches(
            "file_λόγος", "_λόγος", position="End of name", case_sensitive=False
        )
        assert len(matches) == 1
        assert matches[0].matched_text == "_λόγος"


class TestApplyRemoval:
    """Test cases for apply_removal method."""

    def test_single_match_removal(self):
        """Test removing a single match."""
        matches = [TextRemovalMatch(8, 13, "_copy")]
        result = TextRemovalModule.apply_removal("document_copy", matches)
        assert result == "document"

    def test_multiple_matches_removal(self):
        """Test removing multiple matches."""
        matches = [
            TextRemovalMatch(4, 8, "_old"),
            TextRemovalMatch(13, 17, "_old"),
        ]
        result = TextRemovalModule.apply_removal("test_old_file_old", matches)
        assert result == "test_file"

    def test_no_matches_removal(self):
        """Test with no matches returns original text."""
        result = TextRemovalModule.apply_removal("document", [])
        assert result == "document"

    def test_removal_at_start(self):
        """Test removing match at start."""
        matches = [TextRemovalMatch(0, 7, "backup_")]
        result = TextRemovalModule.apply_removal("backup_document", matches)
        assert result == "document"

    def test_removal_at_end(self):
        """Test removing match at end."""
        matches = [TextRemovalMatch(8, 13, "_copy")]
        result = TextRemovalModule.apply_removal("document_copy", matches)
        assert result == "document"

    def test_adjacent_matches(self):
        """Test removing adjacent matches."""
        matches = [
            TextRemovalMatch(0, 2, "aa"),
            TextRemovalMatch(2, 4, "bb"),
        ]
        result = TextRemovalModule.apply_removal("aabbcc", matches)
        assert result == "cc"


class TestIntegration:
    """Integration tests for find_matches + apply_removal."""

    def test_end_position_flow(self):
        """Test complete flow for end position."""
        text = "document_copy"
        matches = TextRemovalModule.find_matches(text, "_copy", "End of name", False)
        result = TextRemovalModule.apply_removal(text, matches)
        assert result == "document"

    def test_start_position_flow(self):
        """Test complete flow for start position."""
        text = "backup_document"
        matches = TextRemovalModule.find_matches(text, "backup_", "Start of name", False)
        result = TextRemovalModule.apply_removal(text, matches)
        assert result == "document"

    def test_anywhere_first_flow(self):
        """Test complete flow for anywhere first."""
        text = "test_old_file_old"
        matches = TextRemovalModule.find_matches(text, "_old", "Anywhere (first)", False)
        result = TextRemovalModule.apply_removal(text, matches)
        assert result == "test_file_old"

    def test_anywhere_all_flow(self):
        """Test complete flow for anywhere all."""
        text = "test_old_file_old"
        matches = TextRemovalModule.find_matches(text, "_old", "Anywhere (all)", False)
        result = TextRemovalModule.apply_removal(text, matches)
        assert result == "test_file"

    def test_case_sensitive_flow(self):
        """Test complete flow with case sensitivity."""
        text = "Document_COPY"
        matches = TextRemovalModule.find_matches(text, "_copy", "End of name", True)
        result = TextRemovalModule.apply_removal(text, matches)
        assert result == "Document_COPY"

        matches = TextRemovalModule.find_matches(text, "_COPY", "End of name", True)
        result = TextRemovalModule.apply_removal(text, matches)
        assert result == "Document"

    def test_no_match_flow(self):
        """Test complete flow when no match found."""
        text = "document"
        matches = TextRemovalModule.find_matches(text, "_copy", "End of name", False)
        result = TextRemovalModule.apply_removal(text, matches)
        assert result == "document"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
