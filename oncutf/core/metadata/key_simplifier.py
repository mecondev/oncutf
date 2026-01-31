"""Smart metadata key simplification.

Provides algorithmic simplification of long metadata keys by removing
common prefixes, repetitions, and keeping only significant segments.

Author: Michael Economou
Date: 2026-01-15
"""

import re
import unicodedata
from typing import Any, ClassVar
from urllib.parse import unquote

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class SmartKeySimplifier:
    """Algorithmic metadata key simplification without hardcoded rules.

    Handles edge cases:
    - Empty/whitespace keys
    - Single-word keys
    - Unicode/non-ASCII characters
    - Numeric tokens (preserves them)
    - Version numbers (preserves them)
    - Mixed delimiters
    - CamelCase splitting
    - Very long single tokens
    - Repetitive segments
    - Heterogeneous key sets

    Example:
        >>> simplifier = SmartKeySimplifier({"max_segments": 3})
        >>> keys = [
        ...     "Audio Format Audio Rec Port Audio Codec",
        ...     "Audio Format Audio Rec Port Port",
        ...     "Audio Format Num Of Channel"
        ... ]
        >>> result = simplifier.simplify_keys(keys)
        >>> result["Audio Format Audio Rec Port Audio Codec"]
        'Rec Port Codec'

    """

    # Stop words that can be optionally removed (currently disabled by default)
    STOP_WORDS: ClassVar[set[str]] = {
        "of",
        "the",
        "a",
        "an",
        "in",
        "on",
        "at",
        "to",
        "for",
    }

    # Words to preserve (boolean/negation/important)
    PRESERVE_WORDS: ClassVar[set[str]] = {"not", "is", "has", "can", "no", "yes"}

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize simplifier with configuration.

        Args:
            config: Configuration dict with optional keys:
                - max_segments: Maximum segments in simplified key (default: 3)
                - min_key_length_to_simplify: Minimum length before simplification (default: 20)
                - preserve_numbers: Keep numeric tokens (default: True)
                - preserve_domain: Keep first token as domain prefix (default: True)
                - remove_stop_words: Remove filler words (default: False)

        """
        config = config or {}
        self.max_segments = config.get("max_segments", 3)
        self.min_key_length = config.get("min_key_length_to_simplify", 20)
        self.preserve_numbers = config.get("preserve_numbers", True)
        self.preserve_domain = config.get("preserve_domain", True)
        self.remove_stop_words = config.get("remove_stop_words", False)

    def simplify_keys(self, keys: list[str]) -> dict[str, str]:
        """Simplify a list of metadata keys.

        Args:
            keys: List of original metadata keys

        Returns:
            Dict mapping original key -> simplified key

        """
        # Filter invalid keys
        valid_keys = [k for k in keys if k and k.strip()]

        if not valid_keys:
            return {}

        # Preprocess all keys
        preprocessed = {k: self._preprocess_key(k) for k in valid_keys}

        # Check if all keys are single-word (nothing to simplify)
        if all(len(self._tokenize(preprocessed[k])) == 1 for k in valid_keys):
            return {k: k for k in valid_keys}

        # Simplify each key
        simplified = {}
        for key in valid_keys:
            processed = preprocessed[key]

            # Skip if already short
            if len(key) < self.min_key_length:
                simplified[key] = key
                continue

            result = self._simplify_single_key(processed, list(preprocessed.values()))
            simplified[key] = result if result else key

        # Resolve collisions
        simplified = self._resolve_collisions(simplified)

        return simplified

    def _preprocess_key(self, key: str) -> str:
        """Preprocess key: decode, normalize, clean.

        Args:
            key: Original key

        Returns:
            Cleaned key

        """
        # URL decode
        key = unquote(key)

        # Unicode normalization (NFC)
        key = unicodedata.normalize("NFC", key)

        # Remove zero-width and invisible characters
        key = re.sub(r"[\u200B-\u200D\uFEFF]", "", key)

        # Strip whitespace and trailing punctuation
        key = key.strip().rstrip(".,;")

        # Normalize multiple spaces
        key = re.sub(r"\s+", " ", key)

        return key

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into segments.

        Handles:
        - Mixed delimiters (space, underscore, dash, dot)
        - CamelCase splitting
        - Array notation [N]
        - Parentheses/brackets removal

        Args:
            text: Text to tokenize

        Returns:
            List of tokens

        """
        # Remove zero-width chars if still present
        text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)

        # Remove key-value separators (but keep metadata prefixes like "EXIF:")
        # Only split on : if not followed by word (to keep EXIF:, XMP:, etc.)
        if ":" in text and not re.search(r"[A-Z]+:", text):
            text = text.split(":")[0].strip()
        if "=" in text:
            text = text.split("=")[0].strip()

        # Remove units in parentheses/brackets
        text = re.sub(r"\s*[\(\[]([^)\]]+)[\)\]]", "", text)

        # Split CamelCase
        text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

        # Normalize array notation [N] -> keep as "N"
        text = re.sub(r"\s*\[(\d+)\]", r" \1 ", text)

        # Split by delimiters (space, underscore, dash, dot)
        tokens = re.split(r"[\s_\-\.]+", text)

        # Filter empty tokens
        return [t for t in tokens if t]

    def _simplify_single_key(self, key: str, _all_keys: list[str]) -> str:
        """Simplify a single key with context awareness.

        Args:
            key: Key to simplify
            _all_keys: All keys (for context - reserved for future use)

        Returns:
            Simplified key

        """
        tokens = self._tokenize(key)

        # Too few tokens - nothing to simplify
        if len(tokens) <= 2:
            return key

        # Preserve domain (first token) if enabled
        domain = tokens[0] if self.preserve_domain and len(tokens) > 3 else None

        # Remove repetitions
        cleaned_tokens = self._remove_repetitions_iterative(tokens)

        # Preserve numeric tokens
        if self.preserve_numbers:
            cleaned_tokens = self._preserve_numbers(tokens, cleaned_tokens)

        # Remove stop words if enabled
        if self.remove_stop_words:
            cleaned_tokens = self._remove_stop_words(cleaned_tokens)

        # Keep last N segments (adaptive)
        max_seg = self._adaptive_max_segments(len(key))
        if len(cleaned_tokens) > max_seg:
            if domain and domain in cleaned_tokens:
                # Keep domain + last (N-1)
                cleaned_tokens.remove(domain)
                cleaned_tokens = [domain, *cleaned_tokens[-(max_seg - 1) :]]
            else:
                cleaned_tokens = cleaned_tokens[-max_seg:]

        result = " ".join(cleaned_tokens)
        return result if result else key

    def _remove_repetitions_iterative(self, tokens: list[str]) -> list[str]:
        """Remove consecutive repetitions iteratively until stable.

        Args:
            tokens: List of tokens

        Returns:
            Deduplicated tokens

        """
        prev_len = len(tokens)
        max_iterations = 10

        for _ in range(max_iterations):
            tokens = self._remove_repetitions_tokens(tokens)
            if len(tokens) == prev_len:
                break  # Stable
            prev_len = len(tokens)

        return tokens

    def _remove_repetitions_tokens(self, tokens: list[str]) -> list[str]:
        """Remove consecutive duplicate tokens (case-insensitive).

        Args:
            tokens: List of tokens

        Returns:
            Deduplicated list

        """
        result = []
        prev_lower = None

        for token in tokens:
            token_lower = token.lower()
            if token_lower != prev_lower:
                result.append(token)  # Keep original case
                prev_lower = token_lower

        return result

    def _preserve_numbers(self, original: list[str], cleaned: list[str]) -> list[str]:
        """Preserve numeric tokens that were removed.

        Args:
            original: Original token list
            cleaned: Cleaned token list

        Returns:
            Cleaned list with numbers restored

        """
        # Find numeric/version tokens in original
        numeric = [t for t in original if self._is_numeric_or_version(t)]

        # Add back if removed (preserve position where possible)
        result = list(cleaned)
        for num in numeric:
            if num not in result:
                # Try to insert at original position
                try:
                    orig_idx = original.index(num)
                    # Find best insertion point
                    insert_idx = min(orig_idx, len(result))
                    result.insert(insert_idx, num)
                except (ValueError, IndexError):
                    result.append(num)

        return result

    def _is_numeric_or_version(self, token: str) -> bool:
        """Check if token is numeric or version number.

        Args:
            token: Token to check

        Returns:
            True if numeric or version

        """
        # Version number (X.Y or X.Y.Z)
        if re.match(r"^\d+\.\d+(\.\d+)?$", token):
            return True

        # Contains digits
        return bool(any(c.isdigit() for c in token))

    def _remove_stop_words(self, tokens: list[str]) -> list[str]:
        """Remove stop words while preserving important ones.

        Args:
            tokens: List of tokens

        Returns:
            Filtered list

        """
        result = []
        for i, token in enumerate(tokens):
            token_lower = token.lower()

            # Preserve boolean/negation words
            if (
                token_lower in self.PRESERVE_WORDS
                or token_lower not in self.STOP_WORDS
                or i == 0
                or i == len(tokens) - 1
            ):
                result.append(token)

        return result

    def _adaptive_max_segments(self, original_length: int) -> int:
        """Calculate adaptive max segments based on key length.

        Args:
            original_length: Length of original key

        Returns:
            Max segments

        """
        if original_length > 60:
            return min(4, self.max_segments + 1)
        elif original_length > 40:
            return self.max_segments
        else:
            return max(2, self.max_segments - 1)

    def _resolve_collisions(self, simplified: dict[str, str]) -> dict[str, str]:
        """Resolve collisions where multiple keys map to same simplified name.

        Args:
            simplified: Dict of original -> simplified mappings

        Returns:
            Dict with collisions resolved

        """
        from collections import defaultdict

        # Find collisions
        reverse_map = defaultdict(list)
        for orig, simp in simplified.items():
            reverse_map[simp].append(orig)

        result = {}
        for simp, origs in reverse_map.items():
            if len(origs) == 1:
                # No collision
                result[origs[0]] = simp
            else:
                # Collision - add differentiator
                # Find unique tokens for each original key
                for i, orig in enumerate(origs):
                    # Find unique token not in simplified AND not shared with other collision keys
                    orig_tokens = self._tokenize(orig)
                    simp_tokens_lower = {t.lower() for t in self._tokenize(simp)}

                    # Find tokens unique to this key vs other collision keys
                    other_origs = [o for o in origs if o != orig]
                    unique_to_this = []

                    for token in orig_tokens:
                        token_lower = token.lower()
                        if token_lower in simp_tokens_lower:
                            continue  # Already in simplified

                        # Check if unique vs other collision keys
                        is_unique = True
                        for other in other_origs:
                            other_tokens_lower = {t.lower() for t in self._tokenize(other)}
                            if token_lower in other_tokens_lower:
                                is_unique = False
                                break

                        if is_unique:
                            unique_to_this.append(token)

                    if unique_to_this:
                        # Add first unique token in parentheses
                        result[orig] = f"{simp} ({unique_to_this[0]})"
                    else:
                        # Fallback: add index
                        result[orig] = f"{simp} ({i + 1})"

        return result
