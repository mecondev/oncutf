"""Pure text removal logic (Qt-free).

Author: Michael Economou
Date: 2026-02-03
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@dataclass
class TextRemovalMatch:
    """Represents a matched text region for removal."""

    start: int
    end: int
    matched_text: str


class TextRemovalLogic:
    """Pure text removal logic without Qt dependencies."""

    @staticmethod
    def find_matches(
        text: str, pattern: str, position: str, case_sensitive: bool
    ) -> list[TextRemovalMatch]:
        """Find all matches of pattern in text based on position.

        Args:
            text: The text to search in
            pattern: The pattern to find
            position: Where to look ("Start of name", "End of name", "Anywhere in name")
            case_sensitive: Whether matching should be case-sensitive

        Returns:
            List of TextRemovalMatch objects

        """
        if not pattern:
            return []

        import re

        # Escape regex metacharacters in the pattern
        pattern_escaped = re.escape(pattern)

        # Build regex based on position
        if position == "Start of name":
            regex_pattern = f"^{pattern_escaped}"
        elif position == "End of name":
            regex_pattern = f"{pattern_escaped}$"
        else:  # "Anywhere in name"
            regex_pattern = pattern_escaped

        # Compile with appropriate flags
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            regex = re.compile(regex_pattern, flags)
        except re.error:
            logger.warning("Invalid regex pattern: %s", pattern)
            return []

        # Find all matches
        return [
            TextRemovalMatch(start=match.start(), end=match.end(), matched_text=match.group())
            for match in regex.finditer(text)
        ]

    @staticmethod
    def apply_removal(text: str, matches: list[TextRemovalMatch]) -> str:
        """Apply removal by deleting matched regions.

        Args:
            text: Original text
            matches: List of matches to remove (sorted by start position)

        Returns:
            Text with matches removed

        """
        if not matches:
            return text

        # Sort matches by start position (descending) to avoid index issues
        sorted_matches = sorted(matches, key=lambda m: m.start, reverse=True)

        # Remove each match
        result = text
        for match in sorted_matches:
            result = result[: match.start] + result[match.end :]

        return result

    @staticmethod
    def apply_from_data(
        data: dict[str, Any], file_item: Any, _index: int, _metadata_cache: Any = None
    ) -> str:
        """Apply text removal to a filename based on configuration data.

        Args:
            data: Configuration data
            file_item: File item with original filename
            _index: File index (unused in this module)
            _metadata_cache: Metadata cache (unused in this module)

        Returns:
            Modified filename with text removed

        """
        original_name = file_item.filename
        path_obj = Path(original_name)
        name_without_ext, ext = path_obj.stem, path_obj.suffix

        text_to_remove = data.get("text_to_remove", "").strip()
        if not text_to_remove:
            return original_name

        position = data.get("position", "End of name")
        case_sensitive = data.get("case_sensitive", False)

        matches = TextRemovalLogic.find_matches(
            name_without_ext, text_to_remove, position, case_sensitive
        )
        result_name = TextRemovalLogic.apply_removal(name_without_ext, matches)

        return f"{result_name}{ext}"

    @staticmethod
    def is_effective_data(data: dict[str, Any]) -> bool:
        """Check if text removal module data is effective.

        Args:
            data: Module configuration

        Returns:
            True if text_to_remove is non-empty

        """
        return bool(data.get("text_to_remove", "").strip())
