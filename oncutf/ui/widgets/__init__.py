"""Module: __init__.py.

Author: Michael Economou
Date: 2025-05-09

widgets package initialization
This package contains all custom widgets used in the oncutf application.

NOTE: Dialog imports removed to fix circular import issue.
Import dialogs directly from oncutf.ui.dialogs instead.
"""

from .base_validated_input import BaseValidatedInput
from .custom_file_system_model import CustomFileSystemModel
from .custom_splash_screen import CustomSplashScreen
from .file_table import FileTableView
from .file_tree import FileTreeView
from .final_transform_container import FinalTransformContainer
from .interactive_header import InteractiveHeader
from .metadata_tree.view import MetadataTreeView
from .metadata_tree.worker import MetadataWorker
from .metadata_widget import MetadataWidget
from .name_transform_widget import NameTransformWidget
from .original_name_widget import OriginalNameWidget
from .preview_tables_view import PreviewTablesView
from .progress_manager import ProgressManager
from .progress_widget import ProgressWidget
from .rename_module_widget import RenameModuleWidget
from .rename_modules_area import RenameModulesArea
from .styled_combo_box import StyledComboBox
from .validated_line_edit import ValidatedLineEdit

__all__ = [
    "BaseValidatedInput",
    "ComboBoxItemDelegate",
    "CustomFileSystemModel",
    "CustomSplashScreen",
    "FileTableHoverDelegate",
    "FileTableView",
    "FileTreeView",
    "FinalTransformContainer",
    "InteractiveHeader",
    "MetadataTreeView",
    "MetadataWidget",
    "MetadataWorker",
    "NameTransformWidget",
    "OriginalNameWidget",
    "PreviewTablesView",
    "ProgressManager",
    "ProgressWidget",
    "RenameModuleWidget",
    "RenameModulesArea",
    "StyledComboBox",
    "ValidatedLineEdit",
]
