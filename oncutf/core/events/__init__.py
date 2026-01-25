"""Module: events/__init__.py.

Author: Michael Economou
Date: 2025-12-20

Event handling subpackage - organizes event handlers by domain.
Extracted from event_handler_manager.py for better separation of concerns.

NOTE: ContextMenuHandlers is NOT exported from here to avoid core→ui violation.
Import directly from oncutf.ui.events.context_menu instead.
"""

from oncutf.core.events.file_event_handlers import FileEventHandlers
from oncutf.core.events.ui_event_handlers import UIEventHandlers

__all__ = [
    "FileEventHandlers",
    "UIEventHandlers",
]
