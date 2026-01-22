"""Application services - Orchestration layer.

This package contains services that orchestrate domain logic without
depending on Qt or infrastructure details. Services use ports to
interact with external systems.

Author: Michael Economou
Date: 2026-01-22
"""

from oncutf.app.services.cursor import force_restore_cursor, wait_cursor
from oncutf.app.services.progress import (
    create_file_loading_dialog,
    create_hash_dialog,
    create_metadata_dialog,
    create_progress_dialog,
)
from oncutf.app.services.user_interaction import (
    get_dialog_adapter,
    show_error_message,
    show_info_message,
    show_question_message,
    show_warning_message,
)

__all__ = [
    # Dialog services
    "show_info_message",
    "show_error_message",
    "show_warning_message",
    "show_question_message",
    "get_dialog_adapter",
    # Cursor services
    "wait_cursor",
    "force_restore_cursor",
    # Progress services
    "create_progress_dialog",
    "create_metadata_dialog",
    "create_hash_dialog",
    "create_file_loading_dialog",
]
