"""Integration tests for metadata key simplification workflow.

Tests the complete workflow from file loading to simplified key display:
- FileItem with metadata
- MetadataSimplificationService integration
- SimplifiedMetadata wrapper behavior
- Semantic alias resolution

Author: Michael Economou
Date: 2026-01-15
"""

from datetime import datetime

from oncutf.app.services import get_metadata_simplification_service
from oncutf.models.file_item import FileItem


class TestMetadataSimplificationWorkflow:
    """Integration tests for metadata simplification workflow."""

    def test_mp4_file_simplified_keys(self):
        """Test MP4 file with long metadata keys gets simplified."""
        # Create FileItem with typical MP4 metadata
        file_item = FileItem(
            "/test/video.mp4",
            "mp4",
            datetime.now()
        )

        # Simulate metadata loading (typical MP4 structure)
        file_item.metadata = {
            "Audio Format Audio Rec Port Audio Codec": "AAC",
            "Video Format Info Codec": "H264",
            "QuickTime:Duration": "120.5",
            "QuickTime:VideoFrameRate": "30",
            "File:FileSize": "1024000",
            "__extended__": False
        }

        # Get simplified metadata
        service = get_metadata_simplification_service()
        simplified = service.get_simplified_metadata(file_item)

        assert simplified is not None

        # Check algorithmic simplification
        assert "Audio Codec" in simplified or "Audio Format Codec" in simplified

        # Check we can access with simplified key
        simplified_keys = [k for k, _ in simplified.items_simplified()]
        assert any("Audio" in k and "Codec" in k for k in simplified_keys)
        assert any("Video" in k and "Codec" in k for k in simplified_keys)

    def test_semantic_alias_resolution_across_formats(self):
        """Test semantic aliases work across JPG, MP4, MOV formats."""
        service = get_metadata_simplification_service()

        # JPG file with EXIF
        jpg_file = FileItem("/test/photo.jpg", "jpg", datetime.now())
        jpg_file.metadata = {
            "EXIF:DateTimeOriginal": "2026:01:15 10:30:00",
            "EXIF:Model": "Canon EOS R5",
            "EXIF:Make": "Canon"
        }

        # MP4 file with QuickTime
        mp4_file = FileItem("/test/video.mp4", "mp4", datetime.now())
        mp4_file.metadata = {
            "QuickTime:CreateDate": "2026:01:15 11:00:00",
            "QuickTime:Duration": "60.0"
        }

        # Test semantic alias "Creation Date" resolves correctly
        jpg_creation = service.get_metadata_value(
            jpg_file, "Creation Date", use_semantic_fallback=True
        )
        mp4_creation = service.get_metadata_value(
            mp4_file, "Creation Date", use_semantic_fallback=True
        )

        assert jpg_creation == "2026:01:15 10:30:00"
        assert mp4_creation == "2026:01:15 11:00:00"

        # Test semantic alias "Camera Model" resolves
        jpg_model = service.get_metadata_value(
            jpg_file, "Camera Model", use_semantic_fallback=True
        )
        assert jpg_model == "Canon EOS R5"

    def test_simplified_keys_list_generation(self):
        """Test generation of simplified keys list for UI dropdowns."""
        file_item = FileItem("/test/photo.jpg", "jpg", datetime.now())
        file_item.metadata = {
            "EXIF:DateTimeOriginal": "2026:01:15",
            "EXIF:Model": "Canon",
            "EXIF:ISO": "400",
            "File:FileSize": "2048000"
        }

        service = get_metadata_simplification_service()
        keys_list = service.get_simplified_keys(file_item)

        # Should return list of (simplified, original) tuples
        assert isinstance(keys_list, list)
        assert all(isinstance(item, tuple) and len(item) == 2 for item in keys_list)

        # Check we have simplified versions
        simplified_only = [s for s, _ in keys_list]
        originals_only = [o for _, o in keys_list]

        assert "EXIF:DateTimeOriginal" in originals_only
        assert len(simplified_only) == len(originals_only)

    def test_simplify_single_key_semantic_alias(self):
        """Test single key simplification with semantic aliases."""
        service = get_metadata_simplification_service()

        # Test semantic alias resolution
        result = service.simplify_single_key("EXIF:DateTimeOriginal")
        assert result == "Creation Date"

        result = service.simplify_single_key("EXIF:Model")
        assert result == "Camera Model"

        result = service.simplify_single_key("QuickTime:Duration")
        assert result == "Duration"

    def test_simplify_single_key_algorithmic(self):
        """Test single key simplification with algorithm."""
        service = get_metadata_simplification_service()

        # Test algorithmic simplification
        result = service.simplify_single_key("Audio Format Audio Rec Port Audio Codec")
        assert "Audio" in result and "Codec" in result
        assert len(result) < len("Audio Format Audio Rec Port Audio Codec")

        # Test unprefixed key (should apply camelCase splitting)
        result = service.simplify_single_key("ImageWidth")
        assert "Image" in result and "Width" in result

    def test_user_override_workflow(self):
        """Test user override creation and persistence."""
        service = get_metadata_simplification_service()

        # Add user override
        service.add_user_override(
            "CustomKey", "My Custom Name"
        )

        # Verify override applied
        result = service.simplify_single_key("CustomKey")
        assert result == "My Custom Name"

        # Test undo
        success = service.undo_override()
        assert success is True

        # After undo, should fall back
        result = service.simplify_single_key("CustomKey")
        assert result != "My Custom Name"

        # Test redo
        success = service.redo_override()
        assert success is True

        result = service.simplify_single_key("CustomKey")
        assert result == "My Custom Name"

    def test_export_import_workflow(self, tmp_path):
        """Test export and import of user overrides."""
        service = get_metadata_simplification_service()

        # Add some overrides
        service.add_user_override("Key1", "Custom1")
        service.add_user_override("Key2", "Custom2")

        # Export to file
        export_file = tmp_path / "test_overrides.json"
        service.export_user_overrides(str(export_file))

        assert export_file.exists()

        # Create new service instance (simulate restart)
        from oncutf.app.services import MetadataSimplificationService

        new_service = MetadataSimplificationService()

        # Import overrides
        new_service.import_user_overrides(str(export_file), merge=True)

        # Verify overrides loaded
        result = new_service.simplify_single_key("Key1")
        assert result == "Custom1"

    def test_semantic_aliases_file_path(self):
        """Test getting semantic aliases file path."""
        service = get_metadata_simplification_service()

        path = service.get_aliases_file_path()

        assert isinstance(path, str)
        assert "semantic_metadata_aliases.json" in path
        assert ".local/share/oncutf" in path or "oncutf" in path

    def test_reload_semantic_aliases(self):
        """Test reloading semantic aliases after manual edit."""
        service = get_metadata_simplification_service()

        # Initial load
        result1 = service.simplify_single_key("EXIF:DateTimeOriginal")
        assert result1 == "Creation Date"

        # Reload (should not crash even if file unchanged)
        service.reload_semantic_aliases()

        # Should still work
        result2 = service.simplify_single_key("EXIF:DateTimeOriginal")
        assert result2 == "Creation Date"

    def test_no_metadata_handling(self):
        """Test handling of files without metadata."""
        file_item = FileItem("/test/empty.txt", "txt", datetime.now())
        # No metadata loaded

        service = get_metadata_simplification_service()

        # Should return None
        simplified = service.get_simplified_metadata(file_item)
        assert simplified is None

        # Should return None for value access
        value = service.get_metadata_value(file_item, "AnyKey")
        assert value is None

        # Should return empty list
        keys = service.get_simplified_keys(file_item)
        assert keys == []

    def test_internal_flags_excluded(self):
        """Test that __extended__ and __companion__ flags are excluded."""
        file_item = FileItem("/test/file.jpg", "jpg", datetime.now())
        file_item.metadata = {
            "EXIF:Model": "Canon",
            "__extended__": True,
            "__companion__": False
        }

        service = get_metadata_simplification_service()
        simplified = service.get_simplified_metadata(file_item)

        # Internal flags should not appear in simplified view
        all_keys = [k for k, _ in simplified.items_simplified()]
        assert "__extended__" not in all_keys
        assert "__companion__" not in all_keys

        # But actual metadata should be there
        assert any("Model" in k or "Camera Model" in k for k in all_keys)
