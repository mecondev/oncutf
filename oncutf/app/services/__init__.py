"""Application services - Orchestration layer.

This package contains services that orchestrate domain logic without
depending on Qt or infrastructure details. Services use ports to
interact with external systems.

Author: Michael Economou
Date: 2026-01-22
"""

from oncutf.app.services.batch_service import BatchService, get_batch_service
from oncutf.app.services.cache_service import CacheService, get_cache_service
from oncutf.app.services.cursor import force_restore_cursor, wait_cursor
from oncutf.app.services.database_service import DatabaseService, get_database_service
from oncutf.app.services.metadata_service import MetadataService, get_metadata_service
from oncutf.app.services.metadata_simplification_service import (
    MetadataSimplificationService,
    get_metadata_simplification_service,
)
from oncutf.app.services.progress import (
    create_file_loading_dialog,
    create_hash_dialog,
    create_metadata_dialog,
    create_progress_dialog,
)
from oncutf.app.services.rename_history_service import (
    RenameBatch,
    RenameHistoryManager,
    RenameOperation,
    get_rename_history_manager,
)
from oncutf.app.services.user_interaction import (
    get_dialog_adapter,
    show_error_message,
    show_info_message,
    show_question_message,
    show_warning_message,
)
from oncutf.app.services.validation_service import ValidationService, get_validation_service

# Re-export metadata command manager (has Qt dependencies, kept in core)
from oncutf.core.metadata import MetadataCommandManager, get_metadata_command_manager

__all__ = [
    "BatchService",
    "CacheService",
    "DatabaseService",
    "MetadataCommandManager",
    "MetadataService",
    "MetadataSimplificationService",
    "RenameBatch",
    "RenameHistoryManager",
    "RenameOperation",
    "ValidationService",
    "create_file_loading_dialog",
    "create_hash_dialog",
    "create_metadata_dialog",
    "create_progress_dialog",
    "force_restore_cursor",
    "get_batch_service",
    "get_cache_service",
    "get_database_service",
    "get_dialog_adapter",
    "get_metadata_command_manager",
    "get_metadata_service",
    "get_metadata_simplification_service",
    "get_rename_history_manager",
    "get_validation_service",
    "show_error_message",
    "show_info_message",
    "show_question_message",
    "show_warning_message",
    "wait_cursor",
]
