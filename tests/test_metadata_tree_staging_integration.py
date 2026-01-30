import os
from unittest.mock import MagicMock, patch

import pytest

try:
    from PyQt5.QtWidgets import QApplication

    from oncutf.app.state.file_store import FileItem
    from oncutf.core.metadata import MetadataStagingManager
    from oncutf.ui.widgets.metadata_tree.view import MetadataTreeView

    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False


@pytest.mark.skipif(not PYQT5_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.skipif("CI" in os.environ, reason="GUI tests don't work on CI")
class TestMetadataTreeStagingIntegration:

    @pytest.fixture(scope="session")
    def qapp(self):
        if not QApplication.instance():
            app = QApplication([])
            yield app
            app.quit()
        else:
            yield QApplication.instance()

    @pytest.fixture
    def staging_manager(self):
        return MetadataStagingManager()

    @pytest.fixture
    def tree_view(self):
        tree = MetadataTreeView()
        yield tree
        tree.deleteLater()

    def test_staging_integration(self, tree_view, staging_manager):
        # Create a mock metadata service that uses our staging manager
        mock_metadata_service = MagicMock()
        mock_metadata_service.staging_manager = staging_manager

        # Mock both get_metadata_staging_manager and get_metadata_service
        # Note: get_metadata_service is imported inside the method, so patch at source
        with patch(
            "oncutf.core.metadata.get_metadata_staging_manager",
            return_value=staging_manager,
        ), patch(
            "oncutf.core.metadata.metadata_service.get_metadata_service",
            return_value=mock_metadata_service,
        ):

            # Setup file item
            file_item = MagicMock(spec=FileItem)
            file_item.full_path = "/test/file.jpg"
            file_item.filename = "file.jpg"
            file_item.metadata = {"EXIF:Artist": "Original Artist"}

            # Mock selection
            tree_view._get_current_selection = MagicMock(return_value=[file_item])
            tree_view._current_file_path = file_item.full_path

            # 1. Test staging manager stages changes correctly
            staging_manager.stage_change(file_item.full_path, "EXIF/Artist", "New Artist")

            # 2. Verify staged changes are stored
            staged = staging_manager.get_staged_changes(file_item.full_path)
            assert staged.get("EXIF/Artist") == "New Artist"

            # 3. Clear staging
            staging_manager.clear_staged_changes(file_item.full_path)
            staged = staging_manager.get_staged_changes(file_item.full_path)
            assert staged.get("EXIF/Artist") is None

            # 4. Test fallback edit value (stages change)
            # Mock needed methods for _fallback_edit_value to work
            tree_view._cache_behavior._update_file_icon_status = MagicMock()
            tree_view._edit_behavior._update_tree_item_value = MagicMock()
            tree_view.viewport = MagicMock()

            tree_view._edit_behavior._fallback_edit_value(
                "EXIF/Copyright", "New Copyright", "Old", [file_item]
            )

            staged = staging_manager.get_staged_changes(file_item.full_path)
            assert staged.get("EXIF/Copyright") == "New Copyright"
            assert file_item.metadata_status == "modified"
