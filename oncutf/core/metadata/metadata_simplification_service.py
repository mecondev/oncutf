"""Metadata simplification service for UI integration.

Provides simplified metadata access for FileItem objects, integrating
SmartKeySimplifier, SimplifiedMetadata wrapper, and MetadataKeyRegistry
with semantic aliases.

Author: Michael Economou
Date: 2026-01-15
"""

from typing import Any

from oncutf.core.metadata.key_simplifier import SmartKeySimplifier
from oncutf.core.metadata.metadata_key_registry import MetadataKeyRegistry
from oncutf.core.metadata.semantic_aliases_manager import (
    SemanticAliasesManager,
)
from oncutf.core.metadata.simplified_metadata import SimplifiedMetadata
from oncutf.models.file_item import FileItem
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataSimplificationService:
    """Service for simplifying metadata keys in FileItem objects.

    Integrates all metadata key simplification components:
    - SmartKeySimplifier for algorithmic simplification
    - SimplifiedMetadata for bidirectional mapping
    - MetadataKeyRegistry for semantic aliases and undo/redo
    - SemanticAliasesManager for persistent configuration

    This service is used by UI components (metadata viewer, rename modules)
    to display and work with simplified metadata keys.

    Example:
        >>> service = MetadataSimplificationService()
        >>> simplified = service.get_simplified_metadata(file_item)
        >>> # Access with simplified key
        >>> value = simplified["Audio Codec"]
        >>> # Or with semantic alias
        >>> value = service.get_metadata_value(file_item, "Creation Date")

    Attributes:
        _simplifier: SmartKeySimplifier instance
        _registry: MetadataKeyRegistry instance
        _aliases_manager: SemanticAliasesManager instance
        _initialized: Whether semantic aliases have been loaded
    """

    def __init__(self):
        """Initialize metadata simplification service."""
        self._simplifier = SmartKeySimplifier()
        self._registry = MetadataKeyRegistry()
        self._aliases_manager = SemanticAliasesManager()
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure semantic aliases are loaded (lazy initialization)."""
        if not self._initialized:
            aliases = self._aliases_manager.load_aliases(auto_create=True)
            self._registry.load_semantic_aliases(custom_aliases=aliases)
            self._initialized = True
            logger.info(
                "Metadata simplification service initialized with %d semantic aliases",
                self._registry.get_semantic_count(),
            )

    def get_simplified_metadata(
        self, file_item: FileItem
    ) -> SimplifiedMetadata | None:
        """Get SimplifiedMetadata wrapper for FileItem's metadata.

        Args:
            file_item: FileItem with loaded metadata

        Returns:
            SimplifiedMetadata wrapper or None if no metadata
        """
        if not file_item.has_metadata:
            return None

        original_metadata = file_item.metadata.copy()

        # Remove internal flags
        original_metadata.pop("__extended__", None)
        original_metadata.pop("__companion__", None)

        return SimplifiedMetadata(
            original_metadata=original_metadata, simplifier=self._simplifier
        )

    def get_metadata_value(
        self,
        file_item: FileItem,
        key: str,
        use_semantic_fallback: bool = True,
    ) -> Any | None:
        """Get metadata value with semantic alias fallback.

        Tries to resolve the key using semantic aliases if available,
        then falls back to direct key access.

        Args:
            file_item: FileItem with loaded metadata
            key: Metadata key (can be semantic alias, simplified, or original)
            use_semantic_fallback: Whether to use semantic alias resolution

        Returns:
            Metadata value or None if not found
        """
        if not file_item.has_metadata:
            return None

        # Ensure semantic aliases loaded if needed
        if use_semantic_fallback:
            self._ensure_initialized()

        original_metadata = file_item.metadata.copy()
        original_metadata.pop("__extended__", None)
        original_metadata.pop("__companion__", None)

        # Try semantic alias resolution
        if use_semantic_fallback:
            available_keys = list(original_metadata.keys())
            resolved_key = self._registry.resolve_key_with_fallback(
                key, available_keys
            )
            if resolved_key:
                return original_metadata.get(resolved_key)

        # Fallback to direct access via SimplifiedMetadata
        simplified = SimplifiedMetadata(
            original_metadata=original_metadata, simplifier=self._simplifier
        )
        try:
            return simplified[key]
        except KeyError:
            return None

    def get_simplified_keys(
        self, file_item: FileItem
    ) -> list[tuple[str, str]]:
        """Get list of (simplified_key, original_key) tuples.

        Args:
            file_item: FileItem with loaded metadata

        Returns:
            List of (simplified, original) key pairs
        """
        if not file_item.has_metadata:
            return []

        original_metadata = file_item.metadata.copy()
        original_metadata.pop("__extended__", None)
        original_metadata.pop("__companion__", None)

        simplified = SimplifiedMetadata(
            original_metadata=original_metadata, simplifier=self._simplifier
        )

        result = []
        for simplified_key, _ in simplified.items_simplified():
            original_key = simplified.get_original_key(simplified_key)
            if original_key:
                result.append((simplified_key, original_key))

        return result

    def simplify_single_key(self, key: str) -> str:
        """Simplify a single metadata key with semantic alias resolution.

        Applies the following simplification strategy:
        1. Check for semantic alias match in registry
        2. Check for user override in registry
        3. Apply algorithmic simplification
        4. Return original key if no simplification possible

        Args:
            key: Original metadata key to simplify

        Returns:
            Simplified key (or original if no simplification available)

        Example:
            >>> service.simplify_single_key("EXIF:DateTimeOriginal")
            "Creation Date"  # semantic alias
            >>> service.simplify_single_key("Audio Format Audio Rec Port Audio Codec")
            "Audio Codec"  # algorithmic simplification
        """
        self._ensure_initialized()

        # Try semantic alias resolution first
        resolved = self._registry.resolve_key_with_fallback(key, [key])
        if resolved and resolved != key:
            # Found semantic alias
            semantic_name = self._registry.get_semantic_name_for_key(key)
            if semantic_name:
                return semantic_name

        # Try registry override
        mapping = self._registry.get_mapping(key)
        if mapping and mapping.simplified != key:
            return mapping.simplified

        # Apply algorithmic simplification
        simplified_keys = self._simplifier.simplify_keys([key])
        if simplified_keys and key in simplified_keys:
            simplified = simplified_keys[key]
            if simplified != key:
                return simplified

        # No simplification possible
        return key

    def get_semantic_groups(
        self, file_item: FileItem
    ) -> dict[str, list[tuple[str, str, Any]]]:
        """Group metadata by semantic categories.

        Returns metadata organized into:
        - "Common Fields" - semantic aliases available in this file
        - "File-Specific" - other metadata fields

        Args:
            file_item: FileItem with loaded metadata

        Returns:
            Dictionary with "common" and "specific" lists of (display_key, original_key, value)
        """
        self._ensure_initialized()

        if not file_item.has_metadata:
            return {"common": [], "specific": []}

        original_metadata = file_item.metadata.copy()
        original_metadata.pop("__extended__", None)
        original_metadata.pop("__companion__", None)

        available_keys = list(original_metadata.keys())
        common_fields = []
        specific_fields = []

        # Collect all semantic aliases that resolve to available keys
        for (
            semantic_name,
            _original_keys_list,
        ) in self._registry._semantic_index.items():
            resolved = self._registry.resolve_key_with_fallback(
                semantic_name, available_keys
            )
            if resolved:
                value = original_metadata.get(resolved)
                common_fields.append((semantic_name, resolved, value))

        # Get remaining keys that weren't matched by semantic aliases
        matched_originals = {field[1] for field in common_fields}
        simplified = SimplifiedMetadata(
            original_metadata=original_metadata, simplifier=self._simplifier
        )

        for simplified_key, value in simplified.items_simplified():
            original_key = simplified.get_original_key(simplified_key)
            if original_key and original_key not in matched_originals:
                specific_fields.append((simplified_key, original_key, value))

        return {"common": common_fields, "specific": specific_fields}

    def reload_semantic_aliases(self) -> None:
        """Reload semantic aliases from file (for manual edits).

        Use this when user has manually edited the semantic_metadata_aliases.json
        file and wants to refresh without restarting.
        """
        aliases = self._aliases_manager.reload_aliases()
        self._registry.load_semantic_aliases(custom_aliases=aliases)
        self._initialized = True
        logger.info(
            "Reloaded semantic aliases: %d aliases",
            self._registry.get_semantic_count(),
        )

    def add_user_override(
        self, original_key: str, custom_simplified: str
    ) -> None:
        """Add user override for a specific key's simplified form.

        Args:
            original_key: Original metadata key
            custom_simplified: Custom simplified key to use

        Note:
            This creates a registry mapping, not a persistent alias.
            For persistent aliases, edit semantic_metadata_aliases.json manually.
        """
        self._ensure_initialized()
        self._registry.add_mapping(
            original=original_key,
            simplified=custom_simplified,
            priority=100,  # User overrides have high priority
            source="user",
        )
        logger.info(
            "Added user override: %s -> %s", original_key, custom_simplified
        )

    def undo_override(self) -> bool:
        """Undo last key mapping override.

        Returns:
            True if undo was successful
        """
        return self._registry.undo()

    def redo_override(self) -> bool:
        """Redo last undone override.

        Returns:
            True if redo was successful
        """
        return self._registry.redo()

    def export_user_overrides(self, filepath: str) -> None:
        """Export user overrides to JSON file.

        Args:
            filepath: Path to export file
        """
        self._ensure_initialized()
        self._registry.export_to_file(filepath)
        logger.info("Exported user overrides to %s", filepath)

    def import_user_overrides(
        self, filepath: str, merge: bool = True
    ) -> None:
        """Import user overrides from JSON file.

        Args:
            filepath: Path to import file
            merge: If True, merge with existing; if False, replace
        """
        self._registry.import_from_file(filepath, merge=merge)
        logger.info(
            "Imported user overrides from %s (merge=%s)", filepath, merge
        )

    def get_aliases_file_path(self) -> str:
        """Get path to semantic aliases configuration file.

        Returns:
            Path to semantic_metadata_aliases.json
        """
        return str(self._aliases_manager.get_aliases_file_path())

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            String with initialization status
        """
        status = "initialized" if self._initialized else "not initialized"
        return f"MetadataSimplificationService({status})"


# Global singleton instance (optional - can also instantiate per-component)
_simplification_service: MetadataSimplificationService | None = None


def get_metadata_simplification_service() -> MetadataSimplificationService:
    """Get global MetadataSimplificationService instance.

    Returns:
        Singleton service instance
    """
    global _simplification_service
    if _simplification_service is None:
        _simplification_service = MetadataSimplificationService()
    return _simplification_service
