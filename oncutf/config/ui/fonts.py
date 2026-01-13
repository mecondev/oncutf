"""Font system configuration.

Author: Michael Economou
Date: 2026-01-13

Font families, sizes, and widget-specific overrides.
"""

USE_EMBEDDED_FONTS = False

DEFAULT_UI_FONT = "inter"
DEFAULT_DATA_FONT = "jetbrains"

FONT_SIZE_ADJUSTMENTS = {
    "inter": 0,
    "jetbrains": 1,
}

FONT_FAMILIES = {
    "inter": '"Inter", "Segoe UI", Arial, sans-serif',
    "jetbrains": '"JetBrains Mono", "Courier New", monospace',
}

WIDGET_FONTS = {
    "table": "jetbrains",
    "tree": "jetbrains",
    "list": "jetbrains",
    "text_edit": "jetbrains",
    "line_edit": "jetbrains",
    "spin_box": "jetbrains",
    "time_edit": "jetbrains",
    "date_edit": "jetbrains",
    "datetime_edit": "jetbrains",
    "combo_box": "inter",
    "label": "inter",
    "button": "inter",
    "dialog": "inter",
    "menu": "inter",
    "context_menu": "inter",
    "status_bar": "inter",
    "file_table_header": "inter",
    "metadata_tree_header": "inter",
}


def get_ui_font_family(widget_type: str | None = None) -> str:
    """Get CSS font-family string based on widget type or current configuration.

    Args:
        widget_type: Widget type (e.g., 'table', 'tree', 'dialog'). If None, uses DEFAULT_UI_FONT.

    Returns:
        CSS font-family string with appropriate fallbacks
    """
    if widget_type and widget_type in WIDGET_FONTS:
        font_key = WIDGET_FONTS[widget_type]
        return FONT_FAMILIES.get(font_key, FONT_FAMILIES["inter"])
    return FONT_FAMILIES.get(DEFAULT_UI_FONT, FONT_FAMILIES["inter"])
