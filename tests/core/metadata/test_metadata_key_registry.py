"""Tests for MetadataKeyRegistry.

Author: Michael Economou
Date: 2026-01-15
"""

import json

from oncutf.core.metadata.metadata_key_registry import (
    KeyMapping,
    MetadataKeyRegistry,
    RegistrySnapshot,
)


class TestKeyMapping:
    """Test KeyMapping dataclass."""

    def test_create_basic_mapping(self):
        """Test creating basic key mapping."""
        mapping = KeyMapping(original="EXIF:DateTimeOriginal", simplified="Date Original")
        assert mapping.original == "EXIF:DateTimeOriginal"
        assert mapping.simplified == "Date Original"
        assert mapping.semantic is None
        assert mapping.priority == 0
        assert mapping.source == "algorithmic"

    def test_create_semantic_mapping(self):
        """Test creating semantic key mapping."""
        mapping = KeyMapping(
            original="EXIF:DateTimeOriginal",
            simplified="Creation Date",
            semantic="Creation Date",
            priority=10,
            source="semantic",
        )
        assert mapping.semantic == "Creation Date"
        assert mapping.priority == 10
        assert mapping.source == "semantic"


class TestRegistrySnapshot:
    """Test RegistrySnapshot dataclass."""

    def test_create_snapshot(self):
        """Test creating registry snapshot."""
        mappings = [
            KeyMapping(original="Key1", simplified="K1"),
            KeyMapping(original="Key2", simplified="K2"),
        ]
        snapshot = RegistrySnapshot(
            mappings=mappings, timestamp=12345.0, description="Test snapshot"
        )
        assert len(snapshot.mappings) == 2
        assert snapshot.timestamp == 12345.0
        assert snapshot.description == "Test snapshot"


class TestMetadataKeyRegistry:
    """Test MetadataKeyRegistry functionality."""

    def test_initialization(self):
        """Test registry initialization."""
        registry = MetadataKeyRegistry(max_history=30)
        assert registry.get_mapping_count() == 0
        assert registry.get_semantic_count() == 0
        assert registry.get_history_count() == 0

    def test_add_mapping(self):
        """Test adding a key mapping."""
        registry = MetadataKeyRegistry()
        registry.add_mapping("EXIF:Model", "Camera Model")

        mapping = registry.get_mapping("EXIF:Model")
        assert mapping is not None
        assert mapping.original == "EXIF:Model"
        assert mapping.simplified == "Camera Model"

    def test_add_semantic_mapping(self):
        """Test adding semantic mapping."""
        registry = MetadataKeyRegistry()
        registry.add_mapping(
            original="EXIF:DateTimeOriginal",
            simplified="Creation Date",
            semantic="Creation Date",
            priority=10,
            source="semantic",
        )

        mapping = registry.get_mapping("EXIF:DateTimeOriginal")
        assert mapping.semantic == "Creation Date"
        assert mapping.priority == 10

    def test_remove_mapping(self):
        """Test removing a mapping."""
        registry = MetadataKeyRegistry()
        registry.add_mapping("Key1", "K1")
        assert registry.get_mapping_count() == 1

        result = registry.remove_mapping("Key1")
        assert result is True
        assert registry.get_mapping_count() == 0

    def test_remove_nonexistent_mapping(self):
        """Test removing non-existent mapping returns False."""
        registry = MetadataKeyRegistry()
        result = registry.remove_mapping("NonExistent")
        assert result is False

    def test_resolve_exact_match(self):
        """Test resolving key with exact match."""
        registry = MetadataKeyRegistry()
        available = ["EXIF:Model", "EXIF:Make"]

        result = registry.resolve_key_with_fallback("EXIF:Model", available)
        assert result == "EXIF:Model"

    def test_resolve_semantic_alias(self):
        """Test resolving semantic alias to original key."""
        registry = MetadataKeyRegistry()
        registry.load_semantic_aliases()

        available = ["EXIF:DateTimeOriginal", "EXIF:Model"]
        result = registry.resolve_key_with_fallback("Creation Date", available)
        assert result == "EXIF:DateTimeOriginal"

    def test_resolve_semantic_alias_priority(self):
        """Test semantic alias resolution respects priority."""
        registry = MetadataKeyRegistry()
        # Add two mappings for same semantic with different priorities
        registry.add_mapping(
            "XMP:CreateDate",
            "Creation Date",
            semantic="Creation Date",
            priority=5,
            source="semantic",
        )
        registry.add_mapping(
            "EXIF:DateTimeOriginal",
            "Creation Date",
            semantic="Creation Date",
            priority=10,
            source="semantic",
        )

        # Both available - should pick higher priority
        available = ["EXIF:DateTimeOriginal", "XMP:CreateDate"]
        result = registry.resolve_key_with_fallback("Creation Date", available)
        assert result == "EXIF:DateTimeOriginal"

        # Only lower priority available
        available = ["XMP:CreateDate"]
        result = registry.resolve_key_with_fallback("Creation Date", available)
        assert result == "XMP:CreateDate"

    def test_resolve_not_found(self):
        """Test resolving non-existent key returns None."""
        registry = MetadataKeyRegistry()
        result = registry.resolve_key_with_fallback("NonExistent", ["Key1", "Key2"])
        assert result is None

    def test_load_default_semantic_aliases(self):
        """Test loading default semantic aliases."""
        registry = MetadataKeyRegistry()
        registry.load_semantic_aliases()

        # Should have loaded many mappings
        assert registry.get_mapping_count() > 0
        assert registry.get_semantic_count() > 0

        # Verify specific alias
        mapping = registry.get_mapping("EXIF:DateTimeOriginal")
        assert mapping is not None
        assert mapping.semantic == "Creation Date"

    def test_load_custom_semantic_aliases(self):
        """Test loading custom semantic aliases."""
        registry = MetadataKeyRegistry()
        custom_aliases = {"Custom Field": ["Custom:Key1", "Custom:Key2"]}

        registry.load_semantic_aliases(custom_aliases=custom_aliases)

        # Should have both default and custom
        assert registry.get_semantic_count() > 1

        # Verify custom alias
        mapping = registry.get_mapping("Custom:Key1")
        assert mapping is not None
        assert mapping.semantic == "Custom Field"

    def test_undo_redo(self):
        """Test undo/redo functionality."""
        registry = MetadataKeyRegistry()

        # Initial state: 0 mappings
        assert registry.get_mapping_count() == 0

        # Add first mapping
        registry.add_mapping("Key1", "K1")
        assert registry.get_mapping_count() == 1

        # Add second mapping
        registry.add_mapping("Key2", "K2")
        assert registry.get_mapping_count() == 2

        # Undo second mapping
        result = registry.undo()
        assert result is True
        assert registry.get_mapping_count() == 1
        assert registry.get_mapping("Key1") is not None
        assert registry.get_mapping("Key2") is None

        # Redo second mapping
        result = registry.redo()
        assert result is True
        assert registry.get_mapping_count() == 2
        assert registry.get_mapping("Key2") is not None

    def test_undo_empty_history(self):
        """Test undo with no history returns False."""
        registry = MetadataKeyRegistry()
        result = registry.undo()
        assert result is False

    def test_redo_empty_future(self):
        """Test redo with no future returns False."""
        registry = MetadataKeyRegistry()
        result = registry.redo()
        assert result is False

    def test_undo_clears_future_on_new_change(self):
        """Test that new changes clear redo stack."""
        registry = MetadataKeyRegistry()

        # Add and remove mapping
        registry.add_mapping("Key1", "K1")
        registry.remove_mapping("Key1")

        # Undo once
        registry.undo()
        assert registry.can_redo()

        # Make new change - should clear redo
        registry.add_mapping("Key2", "K2")
        assert not registry.can_redo()

    def test_can_undo_can_redo(self):
        """Test can_undo and can_redo flags."""
        registry = MetadataKeyRegistry()

        assert not registry.can_undo()
        assert not registry.can_redo()

        registry.add_mapping("Key1", "K1")
        assert registry.can_undo()
        assert not registry.can_redo()

        registry.undo()
        assert not registry.can_undo()
        assert registry.can_redo()

    def test_export_import_dict(self):
        """Test export/import to dictionary."""
        registry = MetadataKeyRegistry()
        registry.add_mapping("EXIF:Model", "Camera Model", priority=5, source="user")
        registry.add_mapping("EXIF:Make", "Camera Make", priority=3, source="user")

        # Export
        data = registry.export_to_dict()
        assert "version" in data
        assert "mappings" in data
        assert len(data["mappings"]) == 2

        # Import to new registry
        new_registry = MetadataKeyRegistry()
        new_registry.import_from_dict(data)

        assert new_registry.get_mapping_count() == 2
        mapping = new_registry.get_mapping("EXIF:Model")
        assert mapping.simplified == "Camera Model"
        assert mapping.priority == 5

    def test_export_import_file(self, tmp_path):
        """Test export/import to file."""
        registry = MetadataKeyRegistry()
        registry.add_mapping("Key1", "K1")
        registry.add_mapping("Key2", "K2")

        # Export
        export_path = tmp_path / "registry.json"
        registry.export_to_file(export_path)
        assert export_path.exists()

        # Verify JSON structure
        with open(export_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "mappings" in data
        assert len(data["mappings"]) == 2

        # Import to new registry
        new_registry = MetadataKeyRegistry()
        new_registry.import_from_file(export_path)
        assert new_registry.get_mapping_count() == 2

    def test_import_merge(self):
        """Test import with merge option."""
        registry = MetadataKeyRegistry()
        registry.add_mapping("Key1", "K1")

        # Create data to import
        data = {
            "version": "1.0",
            "mappings": [
                {
                    "original": "Key2",
                    "simplified": "K2",
                    "semantic": None,
                    "priority": 0,
                    "source": "user",
                }
            ],
        }

        # Import with merge
        registry.import_from_dict(data, merge=True)
        assert registry.get_mapping_count() == 2
        assert registry.get_mapping("Key1") is not None
        assert registry.get_mapping("Key2") is not None

    def test_import_replace(self):
        """Test import with replace (not merge)."""
        registry = MetadataKeyRegistry()
        registry.add_mapping("Key1", "K1")

        # Create data to import
        data = {
            "version": "1.0",
            "mappings": [
                {
                    "original": "Key2",
                    "simplified": "K2",
                    "semantic": None,
                    "priority": 0,
                    "source": "user",
                }
            ],
        }

        # Import without merge (replace)
        registry.import_from_dict(data, merge=False)
        assert registry.get_mapping_count() == 1
        assert registry.get_mapping("Key1") is None
        assert registry.get_mapping("Key2") is not None

    def test_import_nonexistent_file(self, tmp_path):
        """Test importing non-existent file logs warning."""
        registry = MetadataKeyRegistry()
        nonexistent = tmp_path / "nonexistent.json"

        # Should not raise, just log warning
        registry.import_from_file(nonexistent)
        assert registry.get_mapping_count() == 0

    def test_max_history_limit(self):
        """Test history is limited to max_history."""
        registry = MetadataKeyRegistry(max_history=3)

        # Add more than max_history changes
        for i in range(5):
            registry.add_mapping(f"Key{i}", f"K{i}")

        # Should only keep last 3
        assert registry.get_history_count() <= 3

    def test_repr(self):
        """Test string representation."""
        registry = MetadataKeyRegistry()
        registry.add_mapping("Key1", "K1")
        registry.add_mapping("Key2", "K2", semantic="Semantic2")

        repr_str = repr(registry)
        assert "MetadataKeyRegistry" in repr_str
        assert "2 mappings" in repr_str

    def test_semantic_index_cleanup(self):
        """Test semantic index is cleaned up when mapping removed."""
        registry = MetadataKeyRegistry()
        registry.add_mapping("Key1", "K1", semantic="Semantic1", source="semantic")

        assert registry.get_semantic_count() == 1

        # Remove mapping should clean up semantic index
        registry.remove_mapping("Key1")
        assert registry.get_semantic_count() == 0


class TestEdgeCases:
    """Test edge cases for MetadataKeyRegistry."""

    def test_empty_available_keys(self):
        """Test resolve with empty available keys."""
        registry = MetadataKeyRegistry()
        registry.load_semantic_aliases()

        result = registry.resolve_key_with_fallback("Creation Date", [])
        assert result is None

    def test_none_available_keys(self):
        """Test resolve with None available keys."""
        registry = MetadataKeyRegistry()
        result = registry.resolve_key_with_fallback("Key", None)
        assert result is None

    def test_duplicate_mapping_updates(self):
        """Test adding same key twice updates mapping."""
        registry = MetadataKeyRegistry()
        registry.add_mapping("Key1", "K1")
        registry.add_mapping("Key1", "K1_Updated")

        mapping = registry.get_mapping("Key1")
        assert mapping.simplified == "K1_Updated"

    def test_multiple_keys_same_semantic(self):
        """Test multiple keys mapping to same semantic alias."""
        registry = MetadataKeyRegistry()

        registry.add_mapping(
            "EXIF:DateTimeOriginal",
            "Creation Date",
            semantic="Creation Date",
        )
        registry.add_mapping("XMP:CreateDate", "Creation Date", semantic="Creation Date")

        assert registry.get_semantic_count() == 1
        assert len(registry._semantic_index["Creation Date"]) == 2

    def test_unicode_keys(self):
        """Test with unicode characters in keys."""
        registry = MetadataKeyRegistry()
        registry.add_mapping("Καλλιτέχνης", "Artist")

        mapping = registry.get_mapping("Καλλιτέχνης")
        assert mapping is not None
        assert mapping.simplified == "Artist"

    def test_export_unicode_to_file(self, tmp_path):
        """Test exporting unicode keys to file."""
        registry = MetadataKeyRegistry()
        registry.add_mapping("Καλλιτέχνης", "Καλλιτέχνης")

        export_path = tmp_path / "unicode.json"
        registry.export_to_file(export_path)

        # Verify file is valid JSON with unicode
        with open(export_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["mappings"][0]["original"] == "Καλλιτέχνης"
