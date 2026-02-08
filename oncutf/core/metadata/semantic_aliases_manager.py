"""Semantic metadata aliases configuration manager.

Manages loading, saving, and auto-creation of semantic metadata aliases
from user configuration directory. Semantic aliases provide unified field
names across different file formats (Lightroom-style).

Author: Michael Economou
Date: 2026-01-15
"""

import json
from pathlib import Path
from typing import cast

from oncutf.core.metadata.metadata_key_registry import MetadataKeyRegistry
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.paths import AppPaths

logger = get_cached_logger(__name__)


class SemanticAliasesManager:
    """Manager for semantic metadata aliases configuration.

    Handles auto-creation, loading, and saving of semantic aliases
    from user configuration directory. NOT editable from UI - advanced
    users can manually edit the JSON file.

    Example:
        >>> manager = SemanticAliasesManager()
        >>> aliases = manager.load_aliases()
        >>> # Returns default aliases on first run, auto-creates file
        >>> # On subsequent runs, loads from ~/.oncutf/semantic_metadata_aliases.json

    Attributes:
        _aliases_file: Path to semantic aliases JSON file

    """

    ALIASES_FILENAME = "semantic_metadata_aliases.json"

    def __init__(self) -> None:
        """Initialize semantic aliases manager."""
        self._aliases_file = self._get_aliases_path()

    def _get_aliases_path(self) -> Path:
        """Get path to semantic aliases configuration file.

        Returns:
            Path to semantic_metadata_aliases.json in user data directory

        """
        return AppPaths.get_user_data_dir() / self.ALIASES_FILENAME

    def load_aliases(self, auto_create: bool = True) -> dict[str, list[str]]:
        """Load semantic aliases from file or create with defaults.

        Args:
            auto_create: If True, create file with defaults if not exists

        Returns:
            Dictionary mapping semantic names to lists of original keys

        """
        if not self._aliases_file.exists():
            if auto_create:
                logger.info(
                    "Semantic aliases file not found, creating with defaults: %s",
                    self._aliases_file,
                )
                self._create_default_file()
                return self._load_from_file()
            logger.warning("Semantic aliases file not found: %s", self._aliases_file)
            return MetadataKeyRegistry.DEFAULT_SEMANTIC_ALIASES.copy()

        return self._load_from_file()

    def _load_from_file(self) -> dict[str, list[str]]:
        """Load semantic aliases from JSON file.

        Returns:
            Dictionary of semantic aliases

        Raises:
            ValueError: If file is corrupted or invalid JSON

        """

        def _raise_invalid_structure() -> None:
            raise TypeError("Aliases file must contain a JSON object")

        def _raise_invalid_alias(key: str) -> None:
            raise TypeError(f"Alias '{key}' must map to a list of keys")

        try:
            with self._aliases_file.open(encoding="utf-8") as f:
                data = json.load(f)

            # Validate structure
            if not isinstance(data, dict):
                _raise_invalid_structure()

            for key, value in data.items():
                if not isinstance(value, list):
                    _raise_invalid_alias(key)

            logger.debug(
                "Loaded %d semantic aliases from %s",
                len(data),
                self._aliases_file,
            )
        except json.JSONDecodeError:
            logger.exception(
                "Failed to parse semantic aliases file: %s",
                self._aliases_file,
            )
            # Backup corrupted file and return defaults
            self._backup_corrupted_file()
            return MetadataKeyRegistry.DEFAULT_SEMANTIC_ALIASES.copy()
        except Exception:
            logger.exception("Error loading semantic aliases")
            return MetadataKeyRegistry.DEFAULT_SEMANTIC_ALIASES.copy()
        else:
            return cast("dict[str, list[str]]", data)

    def _create_default_file(self) -> None:
        """Create semantic aliases file with default values."""
        defaults = MetadataKeyRegistry.DEFAULT_SEMANTIC_ALIASES.copy()
        self.save_aliases(defaults)
        logger.info(
            "Created semantic aliases file with %d defaults: %s",
            len(defaults),
            self._aliases_file,
        )

    def save_aliases(self, aliases: dict[str, list[str]]) -> bool:
        """Save semantic aliases to file.

        Args:
            aliases: Dictionary mapping semantic names to original keys

        Returns:
            True if saved successfully, False otherwise

        """
        try:
            # Ensure directory exists
            self._aliases_file.parent.mkdir(parents=True, exist_ok=True)

            # Write with pretty formatting
            with self._aliases_file.open("w", encoding="utf-8") as f:
                json.dump(
                    aliases,
                    f,
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True,
                )

            logger.info("Saved semantic aliases to %s", self._aliases_file)
        except Exception:
            logger.exception("Failed to save semantic aliases")
            return False
        else:
            return True

    def reload_aliases(self) -> dict[str, list[str]]:
        """Reload aliases from file (for manual edits).

        Returns:
            Reloaded semantic aliases dictionary

        """
        logger.info("Reloading semantic aliases from file")
        return self.load_aliases(auto_create=False)

    def _backup_corrupted_file(self) -> None:
        """Backup corrupted aliases file for recovery."""
        if not self._aliases_file.exists():
            return

        from datetime import UTC, datetime

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.ALIASES_FILENAME}.corrupted_{timestamp}"
        backup_path = self._aliases_file.parent / backup_name

        try:
            import shutil

            shutil.copy2(self._aliases_file, backup_path)
            logger.warning("Backed up corrupted aliases file to %s", backup_path)
        except Exception:
            logger.exception("Failed to backup corrupted file")

    def get_aliases_file_path(self) -> Path:
        """Get path to semantic aliases file.

        Returns:
            Path to semantic_metadata_aliases.json

        """
        return self._aliases_file

    def file_exists(self) -> bool:
        """Check if semantic aliases file exists.

        Returns:
            True if file exists

        """
        return self._aliases_file.exists()

    def reset_to_defaults(self) -> bool:
        """Reset semantic aliases to default values.

        Returns:
            True if reset successful

        """
        logger.warning("Resetting semantic aliases to defaults")
        defaults = MetadataKeyRegistry.DEFAULT_SEMANTIC_ALIASES.copy()
        return self.save_aliases(defaults)

    def add_alias(self, semantic_name: str, original_keys: list[str]) -> bool:
        """Add or update a semantic alias.

        Args:
            semantic_name: Unified semantic name
            original_keys: List of original metadata keys

        Returns:
            True if saved successfully

        """
        aliases = self.load_aliases(auto_create=True)
        aliases[semantic_name] = original_keys
        return self.save_aliases(aliases)

    def remove_alias(self, semantic_name: str) -> bool:
        """Remove a semantic alias.

        Args:
            semantic_name: Semantic name to remove

        Returns:
            True if removed and saved successfully

        """
        aliases = self.load_aliases(auto_create=True)
        if semantic_name in aliases:
            del aliases[semantic_name]
            return self.save_aliases(aliases)
        return False

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            String with file path and status

        """
        exists_str = "exists" if self.file_exists() else "not created"
        return f"SemanticAliasesManager({self._aliases_file}, {exists_str})"
