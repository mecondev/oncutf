"""
Widgets module for ONCUTF application.

This module contains all custom widgets used throughout the application.
"""

# Progress widgets
# Utility widgets
from .custom_msgdialog import CustomMessageDialog
from .custom_splash_screen import CustomSplashScreen

# File widgets
from .file_table_view import FileTableView
from .file_tree_view import FileTreeView
from .hover_delegate import HoverItemDelegate
from .interactive_header import InteractiveHeader
from .metadata_edit_dialog import MetadataEditDialog
from .metadata_tree_view import MetadataTreeView

# Metadata widgets
from .metadata_widget import MetadataWidget

# Worker widgets
from .metadata_worker import MetadataWorker
from .name_transform_widget import NameTransformWidget
from .original_name_widget import OriginalNameWidget

# Preview widgets
from .preview_tables_view import PreviewTablesView
from .progress_manager import (
    ProgressManager,
    create_copy_progress_manager,
    create_hash_progress_manager,
    create_metadata_progress_manager,
)
from .progress_widget import (
    ProgressWidget,
    create_basic_progress_widget,
    create_size_based_progress_widget,
)
from .rename_module_widget import RenameModuleWidget

# Rename widgets
from .rename_modules_area import RenameModulesArea
from .validated_line_edit import ValidatedLineEdit

__all__ = [
    # Progress
    'ProgressWidget',
    'ProgressManager',
    'create_basic_progress_widget',
    'create_size_based_progress_widget',
    'create_hash_progress_manager',
    'create_metadata_progress_manager',
    'create_copy_progress_manager',

    # File widgets
    'FileTableView',
    'FileTreeView',

    # Metadata widgets
    'MetadataWidget',
    'MetadataTreeView',
    'MetadataEditDialog',

    # Rename widgets
    'RenameModulesArea',
    'RenameModuleWidget',
    'NameTransformWidget',
    'OriginalNameWidget',

    # Preview widgets
    'PreviewTablesView',

    # Utility widgets
    'CustomMessageDialog',
    'CustomSplashScreen',
    'ValidatedLineEdit',
    'InteractiveHeader',
    'HoverItemDelegate',

    # Worker widgets
    'MetadataWorker',
]
