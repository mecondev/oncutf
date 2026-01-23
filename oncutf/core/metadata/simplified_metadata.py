"""SimplifiedMetadata wrapper for bidirectional key mapping.

Provides access to metadata using both original (long) and simplified (short) keys,
maintaining bidirectional mapping for seamless integration with existing code.

Author: Michael Economou
Date: 2026-01-15
"""

from collections.abc import Iterator

from oncutf.core.metadata.key_simplifier import SmartKeySimplifier
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class SimplifiedMetadata:
    """Wrapper providing bidirectional access to metadata with simplified keys.

    This class wraps original metadata dictionaries and provides transparent access
    using either original (long) keys or simplified (short) keys. It maintains
    bidirectional mappings and handles collision scenarios.

    Example:
        >>> original = {"Audio Format Audio Rec Port Audio Codec": "AAC"}
        >>> meta = SimplifiedMetadata(original)
        >>> meta["Audio Codec"]  # Access with simplified key
        'AAC'
        >>> meta["Audio Format Audio Rec Port Audio Codec"]  # Original still works
        'AAC'
        >>> meta.get_original_key("Audio Codec")
        'Audio Format Audio Rec Port Audio Codec'

    Attributes:
        _original_metadata: Original metadata dictionary
        _simplifier: SmartKeySimplifier instance for key transformation
        _simplified_to_original: Mapping from simplified keys to original keys
        _original_to_simplified: Mapping from original keys to simplified keys
        _user_overrides: User-defined simplified key overrides

    """

    def __init__(
        self,
        original_metadata: dict[str, str],
        simplifier: SmartKeySimplifier | None = None,
    ):
        """Initialize SimplifiedMetadata wrapper.

        Args:
            original_metadata: Original metadata dictionary with long keys
            simplifier: Optional SmartKeySimplifier instance (creates default if None)

        """
        self._original_metadata = original_metadata
        self._simplifier = simplifier or SmartKeySimplifier()
        self._user_overrides: dict[str, str] = {}

        # Build bidirectional mappings
        self._simplified_to_original: dict[str, str] = {}
        self._original_to_simplified: dict[str, str] = {}
        self._build_mappings()

    def _build_mappings(self) -> None:
        """Build bidirectional mappings between original and simplified keys."""
        # Get simplified keys from simplifier (pass list of keys)
        original_keys = list(self._original_metadata.keys())
        simplified_dict = self._simplifier.simplify_keys(original_keys)

        # Build bidirectional mappings
        for original_key, _value in self._original_metadata.items():
            simplified_key = simplified_dict.get(original_key, original_key)
            self._original_to_simplified[original_key] = simplified_key
            self._simplified_to_original[simplified_key] = original_key

        logger.debug(
            "Built mappings for %d metadata keys (%d simplified)",
            len(self._original_metadata),
            len(self._simplified_to_original),
        )

    def __getitem__(self, key: str) -> str:
        """Get metadata value using either original or simplified key.

        Args:
            key: Either original (long) or simplified (short) key

        Returns:
            Metadata value

        Raises:
            KeyError: If key not found in either mapping

        """
        # Try direct access first (original key)
        if key in self._original_metadata:
            return self._original_metadata[key]

        # Try as simplified key
        if key in self._simplified_to_original:
            original_key = self._simplified_to_original[key]
            return self._original_metadata[original_key]

        raise KeyError(f"Metadata key not found: {key}")

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get metadata value with default fallback.

        Args:
            key: Either original or simplified key
            default: Default value if key not found

        Returns:
            Metadata value or default

        """
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: str) -> bool:
        """Check if key exists (original or simplified).

        Args:
            key: Either original or simplified key

        Returns:
            True if key exists in either mapping

        """
        return (
            key in self._original_metadata or key in self._simplified_to_original
        )

    def items_simplified(self) -> Iterator[tuple[str, str]]:
        """Iterate over (simplified_key, value) pairs.

        Yields:
            Tuple of (simplified_key, value)

        """
        for original_key, value in self._original_metadata.items():
            simplified_key = self._original_to_simplified.get(
                original_key, original_key
            )
            yield (simplified_key, value)

    def items_original(self) -> Iterator[tuple[str, str]]:
        """Iterate over (original_key, value) pairs.

        Yields:
            Tuple of (original_key, value)

        """
        return iter(self._original_metadata.items())

    def keys_simplified(self) -> Iterator[str]:
        """Iterate over simplified keys.

        Yields:
            Simplified key strings

        """
        for simplified_key, _ in self.items_simplified():
            yield simplified_key

    def keys_original(self) -> Iterator[str]:
        """Iterate over original keys.

        Yields:
            Original key strings

        """
        return iter(self._original_metadata.keys())

    def get_original_key(self, simplified_key: str) -> str | None:
        """Get original key for a simplified key.

        Args:
            simplified_key: Simplified key to look up

        Returns:
            Original key or None if not found

        """
        return self._simplified_to_original.get(simplified_key)

    def get_simplified_key(self, original_key: str) -> str | None:
        """Get simplified key for an original key.

        Args:
            original_key: Original key to look up

        Returns:
            Simplified key or None if not found

        """
        return self._original_to_simplified.get(original_key)

    def has_collision(self, simplified_key: str) -> bool:
        """Check if simplified key is result of collision resolution.

        A collision occurs when multiple original keys simplify to the same value,
        requiring the simplifier to add differentiating tokens.

        Args:
            simplified_key: Simplified key to check

        Returns:
            True if this key was involved in a collision

        """
        # Check if simplifier reported this as a collision
        original_key = self.get_original_key(simplified_key)
        if not original_key:
            return False

        # Re-simplify just this key to see if it matches
        single_key_result = self._simplifier.simplify_keys([original_key])
        simple_version = single_key_result.get(original_key, "")

        # If they differ, it means collision resolution added tokens
        return simple_version != simplified_key

    def override_simplified(self, original_key: str, new_simplified: str) -> None:
        """Override the simplified key for a specific original key.

        This allows users to customize how specific keys are displayed.

        Args:
            original_key: Original key to override
            new_simplified: New simplified key to use

        Raises:
            ValueError: If original_key not in metadata

        """
        if original_key not in self._original_metadata:
            raise ValueError(f"Original key not found: {original_key}")

        # Remove old simplified mapping
        old_simplified = self._original_to_simplified.get(original_key)
        if old_simplified and old_simplified in self._simplified_to_original:
            del self._simplified_to_original[old_simplified]

        # Add new mapping
        self._original_to_simplified[original_key] = new_simplified
        self._simplified_to_original[new_simplified] = original_key
        self._user_overrides[original_key] = new_simplified

        logger.info(
            "Overrode simplified key: %s -> %s (was: %s)",
            original_key,
            new_simplified,
            old_simplified,
        )

    def get_user_overrides(self) -> dict[str, str]:
        """Get dictionary of user-defined overrides.

        Returns:
            Dictionary mapping original keys to user-defined simplified keys

        """
        return self._user_overrides.copy()

    def __len__(self) -> int:
        """Get number of metadata entries.

        Returns:
            Number of metadata key-value pairs

        """
        return len(self._original_metadata)

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            String representation showing entry count

        """
        return (
            f"SimplifiedMetadata({len(self)} entries, "
            f"{len(self._user_overrides)} overrides)"
        )
