"""UI Services package.

UI-specific service layer for dialog management, utilities, etc.
Previously in core/ but moved here for better separation of concerns.
"""

from oncutf.ui.services.dialog_manager import DialogManager
from oncutf.ui.services.utility_manager import UtilityManager

__all__ = [
    "DialogManager",
    "UtilityManager",
]
