"""Shared utilities package.

Generic utilities like timers, external tools, time formatting, etc.
"""

# Re-exports for backward compatibility
from oncutf.utils.shared.external_tools import (
    ToolName,
    get_tool_path,
    get_tool_version,
    is_tool_available,
)
from oncutf.utils.shared.timer_manager import schedule_scroll_adjust

__all__ = [
    "ToolName",
    "get_tool_path",
    "get_tool_version",
    "is_tool_available",
    "schedule_scroll_adjust",
]
