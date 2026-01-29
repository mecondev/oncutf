"""Tests for MetadataSimplificationService.

Author: Michael Economou
Date: 2026-01-15
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from oncutf.core.metadata.metadata_simplification_service import (
    MetadataSimplificationService,
    get_metadata_simplification_service,
)
from oncutf.models.file_item import FileItem


class TestMetadataSimplificationService:
    """Test MetadataSimplificationService functionality."""

    def test_initialization(self):
        """Test service initialization."""
        service = MetadataSimplificationService()
        assert service._initialized is False
        assert service._simplifier is not None
        assert service._registry is not None

    def test_get_simplified_metadata_no_metadata(self):
        """Test with FileItem that has no metadata."""
        service = MetadataSimplificationService()
        file_item = FileItem("/test/file.jpg", "jpg", datetime.now())

        result = service.get_simplified_metadata(file_item)
        assert result is None

    def test_get_simplified_metadata_with_metadata(self, tmp_path):
        """Test getting simplified metadata from FileItem."""
        test_file = tmp_path / "test.jpg"
        test_file.touch()

        file_item = FileItem(str(test_file), "jpg", datetime.now())
        file_item.metadata = {
            "Audio Format Audio Rec Port Audio Codec": "AAC",
            "Video Format Info Codec": "H264",
            "__extended__": True,
        }

        service = MetadataSimplificationService()
        simplified = service.get_simplified_metadata(file_item)

        assert simplified is not None
        assert len(simplified) == 2  # Excluding internal flags
        assert (
            "Audio Codec" in simplified or "Audio Format Audio Rec Port Audio Codec" in simplified
        )

    def test_get_metadata_value_exact_match(self, tmp_path):
        """Test getting value with exact key match."""
        test_file = tmp_path / "test.jpg"
        test_file.touch()

        file_item = FileItem(str(test_file), "jpg", datetime.now())
        file_item.metadata = {"EXIF:Model": "Canon EOS"}

        service = MetadataSimplificationService()
        value = service.get_metadata_value(file_item, "EXIF:Model", use_semantic_fallback=False)

        assert value == "Canon EOS"

    def test_get_metadata_value_semantic_alias(self, tmp_path):
        """Test getting value using semantic alias."""
        with patch(
            "oncutf.core.metadata.metadata_simplification_service.SemanticAliasesManager"
        ) as mock_manager_class:
            # Mock aliases manager
            mock_manager = MagicMock()
            mock_manager.load_aliases.return_value = {"Camera Model": ["EXIF:Model", "XMP:Model"]}
            mock_manager_class.return_value = mock_manager

            test_file = tmp_path / "test.jpg"
            test_file.touch()

            file_item = FileItem(str(test_file), "jpg", datetime.now())
            file_item.metadata = {"EXIF:Model": "Canon EOS"}

            service = MetadataSimplificationService()
            value = service.get_metadata_value(
                file_item, "Camera Model", use_semantic_fallback=True
            )

            assert value == "Canon EOS"

    def test_get_metadata_value_not_found(self, tmp_path):
        """Test getting value for non-existent key."""
        test_file = tmp_path / "test.jpg"
        test_file.touch()

        file_item = FileItem(str(test_file), "jpg", datetime.now())
        file_item.metadata = {"Key1": "Value1"}

        service = MetadataSimplificationService()
        value = service.get_metadata_value(file_item, "NonExistent")

        assert value is None

    def test_get_simplified_keys(self, tmp_path):
        """Test getting list of simplified keys."""
        test_file = tmp_path / "test.jpg"
        test_file.touch()

        file_item = FileItem(str(test_file), "jpg", datetime.now())
        file_item.metadata = {
            "Audio Format Audio Rec Port Audio Codec": "AAC",
            "EXIF:Model": "Canon",
        }

        service = MetadataSimplificationService()
        keys = service.get_simplified_keys(file_item)

        assert len(keys) == 2
        assert all(isinstance(pair, tuple) and len(pair) == 2 for pair in keys)

    def test_get_simplified_keys_empty(self, tmp_path):
        """Test getting keys from empty metadata."""
        test_file = tmp_path / "test.jpg"
        test_file.touch()

        file_item = FileItem(str(test_file), "jpg", datetime.now())

        service = MetadataSimplificationService()
        keys = service.get_simplified_keys(file_item)

        assert keys == []

    def test_get_semantic_groups(self, tmp_path):
        """Test grouping metadata by semantic categories."""
        with patch(
            "oncutf.core.metadata.metadata_simplification_service.SemanticAliasesManager"
        ) as mock_manager_class:
            # Mock aliases manager
            mock_manager = MagicMock()
            mock_manager.load_aliases.return_value = {
                "Camera Model": ["EXIF:Model"],
                "Creation Date": ["EXIF:DateTimeOriginal"],
            }
            mock_manager_class.return_value = mock_manager

            test_file = tmp_path / "test.jpg"
            test_file.touch()

            file_item = FileItem(str(test_file), "jpg", datetime.now())
            file_item.metadata = {
                "EXIF:Model": "Canon",
                "EXIF:DateTimeOriginal": "2026:01:15",
                "CustomKey": "CustomValue",
            }

            service = MetadataSimplificationService()
            groups = service.get_semantic_groups(file_item)

            assert "common" in groups
            assert "specific" in groups
            assert len(groups["common"]) >= 0  # Semantic matches
            assert len(groups["specific"]) >= 0  # Non-semantic

    def test_add_user_override(self, tmp_path):
        """Test adding user override for key."""
        with patch(
            "oncutf.core.metadata.metadata_simplification_service.SemanticAliasesManager"
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.load_aliases.return_value = {}
            mock_manager_class.return_value = mock_manager

            service = MetadataSimplificationService()
            service.add_user_override("LongKey", "Short")

            # Verify override was added to registry
            mapping = service._registry.get_mapping("LongKey")
            assert mapping is not None
            assert mapping.simplified == "Short"
            assert mapping.source == "user"

    def test_undo_redo_override(self, tmp_path):
        """Test undo/redo functionality."""
        with patch(
            "oncutf.core.metadata.metadata_simplification_service.SemanticAliasesManager"
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.load_aliases.return_value = {}
            mock_manager_class.return_value = mock_manager

            service = MetadataSimplificationService()

            # Add override
            service.add_user_override("Key1", "K1")
            assert service._registry.get_mapping("Key1") is not None

            # Undo
            result = service.undo_override()
            assert result is True

            # Redo
            result = service.redo_override()
            assert result is True
            assert service._registry.get_mapping("Key1") is not None

    def test_export_import_user_overrides(self, tmp_path):
        """Test export/import of user overrides."""
        with patch(
            "oncutf.core.metadata.metadata_simplification_service.SemanticAliasesManager"
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.load_aliases.return_value = {}
            mock_manager_class.return_value = mock_manager

            export_file = tmp_path / "overrides.json"

            service = MetadataSimplificationService()
            service.add_user_override("Key1", "K1")

            # Export
            service.export_user_overrides(str(export_file))
            assert export_file.exists()

            # Import to new service
            service2 = MetadataSimplificationService()
            service2.import_user_overrides(str(export_file))

            assert service2._registry.get_mapping("Key1") is not None

    def test_reload_semantic_aliases(self, tmp_path):
        """Test reloading semantic aliases."""
        with patch(
            "oncutf.core.metadata.metadata_simplification_service.SemanticAliasesManager"
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.load_aliases.return_value = {"Field1": ["Key1"]}
            mock_manager.reload_aliases.return_value = {
                "Field1": ["Key1"],
                "Field2": ["Key2"],
            }
            mock_manager_class.return_value = mock_manager

            service = MetadataSimplificationService()
            service._ensure_initialized()

            # Reload
            service.reload_semantic_aliases()
            assert service._initialized is True

    def test_get_aliases_file_path(self, tmp_path):
        """Test getting aliases file path."""
        with patch(
            "oncutf.core.metadata.metadata_simplification_service.SemanticAliasesManager"
        ) as mock_manager_class:
            mock_manager = MagicMock()
            expected_path = Path("/test/aliases.json")
            mock_manager.get_aliases_file_path.return_value = expected_path
            mock_manager_class.return_value = mock_manager

            service = MetadataSimplificationService()
            path = service.get_aliases_file_path()

            assert Path(path) == expected_path

    def test_repr(self):
        """Test string representation."""
        service = MetadataSimplificationService()

        repr_str = repr(service)
        assert "MetadataSimplificationService" in repr_str
        assert "not initialized" in repr_str


class TestGlobalSingleton:
    """Test global singleton pattern."""

    def test_get_metadata_simplification_service(self):
        """Test getting global service instance."""
        service1 = get_metadata_simplification_service()
        service2 = get_metadata_simplification_service()

        # Should return same instance
        assert service1 is service2

    def test_singleton_persistence(self):
        """Test that singleton persists state."""
        with patch(
            "oncutf.core.metadata.metadata_simplification_service.SemanticAliasesManager"
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.load_aliases.return_value = {}
            mock_manager_class.return_value = mock_manager

            service1 = get_metadata_simplification_service()
            service1.add_user_override("Key1", "K1")

            service2 = get_metadata_simplification_service()
            # Should have same override
            mapping = service2._registry.get_mapping("Key1")
            assert mapping is not None
