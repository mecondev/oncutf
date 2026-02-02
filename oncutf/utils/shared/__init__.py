"""Shared utilities package.

Generic utilities like external tools, time formatting, etc.
Note: timer_manager moved to oncutf.ui.helpers.timer_manager
"""

# Re-exports for backward compatibility
from oncutf.utils.shared.external_tools import (
    ToolName,
    get_tool_path,
    get_tool_version,
    is_tool_available,
)

__all__ = [
    "ToolName",
    "get_tool_path",
    "get_tool_version",
    "is_tool_available",
]
