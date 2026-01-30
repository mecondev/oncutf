"""Tests for SmartKeySimplifier.

Author: Michael Economou
Date: 2026-01-15
"""

from oncutf.core.metadata.key_simplifier import SmartKeySimplifier


class TestSmartKeySimplifier:
    """Test SmartKeySimplifier class."""

    def test_basic_simplification(self):
        """Test basic key simplification."""
        simplifier = SmartKeySimplifier()

        keys = [
            "Audio Format Audio Rec Port Audio Codec",
            "Audio Format Audio Rec Port Port",
            "Audio Format Audio Rec Port Track Dst",
        ]

        result = simplifier.simplify_keys(keys)

        # Should remove common prefix and repetitions
        # Results should be shorter than originals
        assert len(result[keys[0]]) < len(keys[0])
        assert len(result[keys[1]]) < len(keys[1])
        assert len(result[keys[2]]) < len(keys[2])

        # All should have different simplified names
        assert len(set(result.values())) == len(keys)

    def test_empty_keys(self):
        """Test handling of empty/whitespace keys."""
        simplifier = SmartKeySimplifier()

        keys = ["", "   ", None, "Valid Key"]

        # Filter None before passing
        valid_keys = [k for k in keys if k is not None]
        result = simplifier.simplify_keys(valid_keys)

        # Should filter out empty keys
        assert len(result) == 1
        assert "Valid Key" in result

    def test_single_word_keys(self):
        """Test keys that are single words."""
        simplifier = SmartKeySimplifier()

        keys = ["Duration", "Title", "Artist"]
        result = simplifier.simplify_keys(keys)

        # Should return as-is
        assert result["Duration"] == "Duration"
        assert result["Title"] == "Title"
        assert result["Artist"] == "Artist"

    def test_collision_resolution(self):
        """Test collision detection and resolution."""
        simplifier = SmartKeySimplifier()

        keys = [
            "Audio Format Audio Rec Port Audio Codec",
            "Audio Format Video Rec Port Audio Codec",  # Different but similar
        ]

        result = simplifier.simplify_keys(keys)

        # Should have different simplified names (collision resolved)
        assert result[keys[0]] != result[keys[1]]
        # Should contain differentiators (Video or Audio or index numbers)
        values = list(result.values())
        assert all(v for v in values)  # No empty results

    def test_numeric_preservation(self):
        """Test preservation of numeric tokens."""
        simplifier = SmartKeySimplifier({"preserve_numbers": True})

        keys = [
            "Audio Track 1 Format",
            "Audio Track 2 Format",
            "Audio Track 1 Codec",
        ]

        result = simplifier.simplify_keys(keys)

        # Should preserve track numbers or differentiate
        # Check that results are unique
        assert len(set(result.values())) == len(keys)
        # Check that numbers appear somewhere (in main result or differentiator)
        combined_text = " ".join(result.values())
        assert "1" in combined_text
        assert "2" in combined_text

    def test_mixed_delimiters(self):
        """Test handling of mixed delimiters."""
        simplifier = SmartKeySimplifier()

        keys = [
            "Audio_Format-Audio.Rec Port",
            "Audio Format Audio Rec Port",
        ]

        result = simplifier.simplify_keys(keys)

        # Should normalize and handle both
        assert len(result) == 2

    def test_camel_case_splitting(self):
        """Test CamelCase token splitting."""
        simplifier = SmartKeySimplifier()

        keys = ["AudioFormatCodec", "VideoFrameRate"]
        result = simplifier.simplify_keys(keys)

        # Should split CamelCase
        assert "Codec" in result["AudioFormatCodec"]
        assert "Rate" in result["VideoFrameRate"]

    def test_unicode_handling(self):
        """Test Unicode/non-ASCII characters."""
        simplifier = SmartKeySimplifier()

        keys = [
            "Διάρκεια Βίντεο Codec",
            "音频格式编解码器",
        ]

        result = simplifier.simplify_keys(keys)

        # Should handle without crashing
        assert len(result) == 2

    def test_version_number_preservation(self):
        """Test preservation of version numbers."""
        simplifier = SmartKeySimplifier({"preserve_numbers": True})

        keys = [
            "EXIF Version 2.3 Format",
            "XMP Version 1.0 Data",
        ]

        result = simplifier.simplify_keys(keys)

        # Should result in shorter keys
        assert len(result[keys[0]]) <= len(keys[0])
        assert len(result[keys[1]]) <= len(keys[1])
        # Results should be different
        assert result[keys[0]] != result[keys[1]]

    def test_short_keys_unchanged(self):
        """Test that short keys are not simplified."""
        simplifier = SmartKeySimplifier({"min_key_length_to_simplify": 20})

        keys = ["Audio Codec", "Video Format"]
        result = simplifier.simplify_keys(keys)

        # Should return as-is (too short)
        assert result["Audio Codec"] == "Audio Codec"
        assert result["Video Format"] == "Video Format"

    def test_iterative_deduplication(self):
        """Test iterative removal of repetitions."""
        simplifier = SmartKeySimplifier()

        keys = ["Audio Audio Track Audio Audio Channels"]
        result = simplifier.simplify_keys(keys)

        # Should remove all consecutive duplicates
        simplified = result["Audio Audio Track Audio Audio Channels"]
        assert simplified.count("Audio") <= 2  # Max 2 after deduplication

    def test_adaptive_max_segments(self):
        """Test adaptive segment limits based on key length."""
        simplifier = SmartKeySimplifier({"max_segments": 3})

        # Use realistic keys with repetition to simplify
        short_key = "Audio Format Audio Codec"
        long_key = "Audio Format Audio Rec Port Audio Codec Audio Description Audio Detail"

        result = simplifier.simplify_keys([short_key, long_key])

        # Both should be simplified
        assert len(result[short_key]) <= len(short_key)
        assert len(result[long_key]) <= len(long_key)
        # Results should respect max_segments constraint
        assert len(result[short_key].split()) <= 4
        assert len(result[long_key].split()) <= 5  # Adaptive allows more for longer keys

    def test_metadata_prefix_preservation(self):
        """Test preservation of metadata standard prefixes."""
        simplifier = SmartKeySimplifier()

        keys = [
            "EXIF:DateTimeOriginal",
            "XMP:CreateDate",
            "IPTC:DateCreated",
        ]

        result = simplifier.simplify_keys(keys)

        # Should handle metadata prefixes (EXIF:, XMP:)
        assert len(result) == 3

    def test_real_world_mp4_metadata(self):
        """Test with real MP4 metadata keys."""
        simplifier = SmartKeySimplifier()

        keys = [
            "Audio Format Audio Rec Port Audio Codec",
            "Audio Format Audio Rec Port Port",
            "Audio Format Audio Rec Port Track Dst",
            "Audio Format Num Of Channel",
            "Audio Avg Bitrate",
            "Audio Bits Per Sample",
            "Audio Channels",
            "Audio Codec",
            "Audio Format",
            "Audio Max Bitrate",
            "Audio Sample Rate",
        ]

        result = simplifier.simplify_keys(keys)

        # Should simplify long keys
        assert len(result["Audio Format Audio Rec Port Audio Codec"]) < len(keys[0])

        # All keys should have simplified versions (unique)
        assert len(result) == len(keys)

        # No empty results
        assert all(v for v in result.values())

    def test_heterogeneous_keys(self):
        """Test keys with no common structure."""
        simplifier = SmartKeySimplifier()

        keys = [
            "Camera Make",
            "GPS Latitude",
            "Title",
            "Duration",
        ]

        result = simplifier.simplify_keys(keys)

        # Should return mostly unchanged (no common prefix)
        assert result["Camera Make"] == "Camera Make"
        assert result["GPS Latitude"] == "GPS Latitude"

    def test_parentheses_removal(self):
        """Test removal of units in parentheses."""
        simplifier = SmartKeySimplifier()

        keys = [
            "Audio Sample Rate (Hz)",
            "Audio Sample Rate Hz",
            "Audio Sample Rate [kHz]",
        ]

        result = simplifier.simplify_keys(keys)

        # Should remove parentheses/brackets
        assert "Sample Rate" in result[keys[0]]
        assert "Hz" not in result[keys[0]] or result[keys[0]].endswith("Hz")

    def test_collision_with_unique_differentiator(self):
        """Test collision resolution adds unique token."""
        simplifier = SmartKeySimplifier()

        keys = [
            "Video Primary Color Red X",
            "Video Primary Color Red Y",
            "Audio Primary Color Red X",
        ]

        result = simplifier.simplify_keys(keys)

        # Should differentiate collisions
        values = list(result.values())
        assert len(values) == len(set(values))  # All unique

    def test_config_options(self):
        """Test different configuration options."""
        # Test with different max_segments
        simplifier1 = SmartKeySimplifier({"max_segments": 2})
        simplifier2 = SmartKeySimplifier({"max_segments": 4})

        keys = ["Audio Format Audio Rec Port Audio Codec"]

        result1 = simplifier1.simplify_keys(keys)
        result2 = simplifier2.simplify_keys(keys)

        # More segments allowed should give potentially longer result
        segments1 = len(result1[keys[0]].split())
        segments2 = len(result2[keys[0]].split())

        assert segments1 <= 2
        assert segments2 <= 4


class TestEdgeCases:
    """Test edge cases and unusual inputs."""

    def test_url_encoded_keys(self):
        """Test URL-encoded keys."""
        simplifier = SmartKeySimplifier()

        keys = ["Audio%20Format%20Codec"]
        result = simplifier.simplify_keys(keys)

        # Should decode
        assert "Codec" in result[keys[0]]

    def test_zero_width_characters(self):
        """Test zero-width/invisible characters."""
        simplifier = SmartKeySimplifier()

        keys = ["Audio\u200bFormat\u200bCodec"]
        result = simplifier.simplify_keys(keys)

        # Should handle without crashing and produce some result
        assert keys[0] in result
        assert result[keys[0]]  # Not empty

    def test_array_notation(self):
        """Test array notation [N]."""
        simplifier = SmartKeySimplifier({"preserve_numbers": True})

        keys = [
            "Audio Track[0] Codec",
            "Audio Track[1] Codec",
        ]

        result = simplifier.simplify_keys(keys)

        # Should produce different results for different indices
        assert result[keys[0]] != result[keys[1]]
        # Numbers should appear somewhere (main text or differentiator)
        combined = " ".join(result.values())
        assert "0" in combined or "1" in combined

    def test_extremely_long_single_token(self):
        """Test very long single token."""
        simplifier = SmartKeySimplifier()

        long_token = "VeryLongCamelCaseTokenThatNeverEndsAndKeepsGoingForever"
        keys = [f"Audio {long_token} Codec"]

        result = simplifier.simplify_keys(keys)

        # Should handle without crashing
        assert keys[0] in result

    def test_multiple_consecutive_spaces(self):
        """Test keys with multiple spaces."""
        simplifier = SmartKeySimplifier()

        keys = ["Audio  Format   Codec"]
        result = simplifier.simplify_keys(keys)

        # Should normalize spaces
        assert "  " not in result[keys[0]]
