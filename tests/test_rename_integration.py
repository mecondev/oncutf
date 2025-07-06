"""
Module: test_rename_integration.py

Author: Michael Economou
Date: 2025-07-06

Integration tests for the enhanced rename workflow with validation
"""
import warnings
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*coroutine.*never awaited')
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)


"""Integration tests for the enhanced rename workflow with validation
"""

from config import INVALID_FILENAME_MARKER
from modules.specified_text_module import SpecifiedTextModule
from tests.mocks import MockFileItem
from utils.filename_validator import is_validation_error_marker


class TestRenameIntegration:
    """Integration tests for the complete rename workflow"""

    def test_valid_input_workflow(self):
        """Test complete workflow with valid input"""
        data = {"type": "specified_text", "text": "valid_prefix"}
        file_item = MockFileItem(filename="test.txt")
        result = SpecifiedTextModule.apply_from_data(data, file_item)
        assert result == "valid_prefix"
        assert not is_validation_error_marker(result)

    def test_invalid_input_workflow(self):
        """Test complete workflow with invalid input"""
        data = {"type": "specified_text", "text": "invalid<text>"}
        file_item = MockFileItem(filename="test.txt")
        result = SpecifiedTextModule.apply_from_data(data, file_item)
        assert is_validation_error_marker(result)
        assert result == INVALID_FILENAME_MARKER

    def test_reserved_filename_workflow(self):
        """Test workflow with Windows reserved names"""
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL']
        for reserved_name in reserved_names:
            data = {"type": "specified_text", "text": reserved_name}
            file_item = MockFileItem(filename="test.txt")
            result = SpecifiedTextModule.apply_from_data(data, file_item)
            assert is_validation_error_marker(result)
