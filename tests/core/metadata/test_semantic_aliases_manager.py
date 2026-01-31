"""Tests for SemanticAliasesManager.

Author: Michael Economou
Date: 2026-01-15
"""

import json
from pathlib import Path
from unittest.mock import patch

from oncutf.core.metadata.metadata_key_registry import MetadataKeyRegistry
from oncutf.core.metadata.semantic_aliases_manager import (
    SemanticAliasesManager,
)


class TestSemanticAliasesManager:
    """Test SemanticAliasesManager functionality."""

    def test_initialization(self, tmp_path):
        """Test manager initialization."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()
            assert manager.get_aliases_file_path() == tmp_path / "semantic_metadata_aliases.json"

    def test_load_aliases_auto_creates_file(self, tmp_path):
        """Test loading aliases auto-creates file with defaults."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()
            assert not manager.file_exists()

            aliases = manager.load_aliases(auto_create=True)

            assert manager.file_exists()
            assert len(aliases) > 0
            assert "Creation Date" in aliases

    def test_load_aliases_no_auto_create(self, tmp_path):
        """Test loading without auto-create returns defaults."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()

            aliases = manager.load_aliases(auto_create=False)

            assert not manager.file_exists()
            assert len(aliases) > 0  # Still returns defaults
            assert "Creation Date" in aliases

    def test_load_existing_file(self, tmp_path):
        """Test loading from existing file."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            # Create a custom aliases file
            custom_aliases = {
                "Custom Field": ["Custom:Key1", "Custom:Key2"],
                "Another Field": ["Another:Key"],
            }
            aliases_file = tmp_path / "semantic_metadata_aliases.json"
            with aliases_file.open("w", encoding="utf-8") as f:
                json.dump(custom_aliases, f)

            manager = SemanticAliasesManager()
            loaded = manager.load_aliases()

            assert loaded == custom_aliases

    def test_save_aliases(self, tmp_path):
        """Test saving aliases to file."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()

            test_aliases = {"Test Field": ["Test:Key1", "Test:Key2"]}
            result = manager.save_aliases(test_aliases)

            assert result is True
            assert manager.file_exists()

            # Verify file contents
            with manager.get_aliases_file_path().open(encoding="utf-8") as f:
                saved = json.load(f)
            assert saved == test_aliases

    def test_reload_aliases(self, tmp_path):
        """Test reloading aliases from file."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()

            # Create initial file
            initial = {"Field1": ["Key1"]}
            manager.save_aliases(initial)

            # Manually modify file
            modified = {"Field2": ["Key2"]}
            with manager.get_aliases_file_path().open("w", encoding="utf-8") as f:
                json.dump(modified, f)

            # Reload should get modified version
            reloaded = manager.reload_aliases()
            assert reloaded == modified

    def test_add_alias(self, tmp_path):
        """Test adding a new semantic alias."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()

            result = manager.add_alias("New Field", ["New:Key1", "New:Key2"])
            assert result is True

            aliases = manager.load_aliases()
            assert "New Field" in aliases
            assert aliases["New Field"] == ["New:Key1", "New:Key2"]

    def test_update_existing_alias(self, tmp_path):
        """Test updating an existing alias."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()

            # Add initial alias
            manager.add_alias("Field", ["Key1"])

            # Update it
            manager.add_alias("Field", ["Key1", "Key2"])

            aliases = manager.load_aliases()
            assert aliases["Field"] == ["Key1", "Key2"]

    def test_remove_alias(self, tmp_path):
        """Test removing a semantic alias."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()

            # Add alias
            manager.add_alias("Field", ["Key1"])
            assert "Field" in manager.load_aliases()

            # Remove it
            result = manager.remove_alias("Field")
            assert result is True

            aliases = manager.load_aliases()
            assert "Field" not in aliases

    def test_remove_nonexistent_alias(self, tmp_path):
        """Test removing non-existent alias returns False."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()
            result = manager.remove_alias("NonExistent")
            assert result is False

    def test_reset_to_defaults(self, tmp_path):
        """Test resetting to default aliases."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()

            # Add custom alias
            manager.add_alias("Custom", ["Custom:Key"])

            # Reset
            result = manager.reset_to_defaults()
            assert result is True

            aliases = manager.load_aliases()
            assert "Custom" not in aliases
            assert "Creation Date" in aliases  # Default exists

    def test_file_exists(self, tmp_path):
        """Test file_exists method."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()

            assert not manager.file_exists()

            manager.save_aliases({"Test": ["Key"]})
            assert manager.file_exists()

    def test_get_aliases_file_path(self, tmp_path):
        """Test getting aliases file path."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()
            path = manager.get_aliases_file_path()

            assert isinstance(path, Path)
            assert path.name == "semantic_metadata_aliases.json"
            assert path.parent == tmp_path

    def test_repr(self, tmp_path):
        """Test string representation."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()

            repr_str = repr(manager)
            assert "SemanticAliasesManager" in repr_str
            assert str(tmp_path) in repr_str


class TestCorruptedFileHandling:
    """Test handling of corrupted alias files."""

    def test_load_corrupted_json(self, tmp_path):
        """Test loading corrupted JSON file."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()

            # Create corrupted JSON file
            aliases_file = manager.get_aliases_file_path()
            aliases_file.parent.mkdir(parents=True, exist_ok=True)
            with aliases_file.open("w", encoding="utf-8") as f:
                f.write("{invalid json content")

            # Should return defaults and backup corrupted file
            aliases = manager.load_aliases()

            assert len(aliases) > 0  # Got defaults
            assert "Creation Date" in aliases

            # Check if backup was created
            backup_files = list(tmp_path.glob("semantic_metadata_aliases.json.corrupted_*"))
            assert len(backup_files) == 1

    def test_load_invalid_structure_not_dict(self, tmp_path):
        """Test loading file with invalid structure (not a dict)."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()

            # Create file with array instead of object
            aliases_file = manager.get_aliases_file_path()
            aliases_file.parent.mkdir(parents=True, exist_ok=True)
            with aliases_file.open("w", encoding="utf-8") as f:
                json.dump(["not", "an", "object"], f)

            # Should return defaults
            aliases = manager.load_aliases()
            assert len(aliases) > 0

    def test_load_invalid_structure_values_not_lists(self, tmp_path):
        """Test loading file with non-list values."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()

            # Create file with string value instead of list
            aliases_file = manager.get_aliases_file_path()
            aliases_file.parent.mkdir(parents=True, exist_ok=True)
            with aliases_file.open("w", encoding="utf-8") as f:
                json.dump({"Field": "should be a list"}, f)

            # Should return defaults
            aliases = manager.load_aliases()
            assert len(aliases) > 0


class TestUnicodeHandling:
    """Test unicode character handling."""

    def test_save_load_unicode_aliases(self, tmp_path):
        """Test saving and loading unicode aliases."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()

            unicode_aliases = {
                "Καλλιτέχνης": ["EXIF:Artist", "XMP:Creator"],
                "Τίτλος": ["XMP:Title", "IPTC:ObjectName"],
            }

            manager.save_aliases(unicode_aliases)
            loaded = manager.load_aliases()

            assert loaded == unicode_aliases

    def test_unicode_in_keys(self, tmp_path):
        """Test unicode in original keys."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()

            aliases = {"Field": ["Κλειδί:Τιμή", "日本語:キー"]}
            manager.save_aliases(aliases)
            loaded = manager.load_aliases()

            assert loaded == aliases


class TestIntegration:
    """Integration tests with MetadataKeyRegistry."""

    def test_load_into_registry(self, tmp_path):
        """Test loading aliases into registry."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()
            registry = MetadataKeyRegistry()

            # Load aliases from manager
            aliases = manager.load_aliases(auto_create=True)

            # Load into registry
            registry.load_semantic_aliases(custom_aliases=aliases)

            # Verify registry has the aliases
            assert registry.get_semantic_count() > 0

            # Test resolution
            available = ["EXIF:DateTimeOriginal"]
            result = registry.resolve_key_with_fallback("Creation Date", available)
            assert result == "EXIF:DateTimeOriginal"

    def test_custom_aliases_in_registry(self, tmp_path):
        """Test custom aliases work with registry."""
        with patch(
            "oncutf.core.metadata.semantic_aliases_manager.AppPaths.get_user_data_dir",
            return_value=tmp_path,
        ):
            manager = SemanticAliasesManager()
            registry = MetadataKeyRegistry()

            # Add custom alias
            manager.add_alias("My Custom Field", ["Custom:Key1", "Custom:Key2"])

            # Load into registry
            aliases = manager.load_aliases()
            registry.load_semantic_aliases(custom_aliases=aliases)

            # Test resolution of custom alias
            available = ["Custom:Key2", "Other:Key"]
            result = registry.resolve_key_with_fallback("My Custom Field", available)
            assert result == "Custom:Key2"
