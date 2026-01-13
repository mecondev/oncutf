"""Theme and color system configuration.

Author: Michael Economou
Date: 2026-01-13

Color themes, semantic colors, and centralized design tokens.
"""

THEME_NAME = "dark"

PREVIEW_COLORS = {
    "valid": "#2ecc71",
    "duplicate": "#e67e22",
    "invalid": "#c0392b",
    "unchanged": "#777777",
}

FAST_METADATA_COLOR = "#64b5f6"
FAST_METADATA_BG_COLOR = "#0a1a2a"

EXTENDED_METADATA_COLOR = "#fabf65"
EXTENDED_METADATA_BG_COLOR = "#2c1810"

FILE_LOADING_COLOR = "#64b5f6"
FILE_LOADING_BG_COLOR = "#0a1a2a"

HASH_CALCULATION_COLOR = "#a256af"
HASH_CALCULATION_BG_COLOR = "#2a1a2a"

SAVE_COLOR = "#64b5f6"
SAVE_BG_COLOR = "#0a1a2a"

QLABEL_PRIMARY_TEXT = "#f0ebd8"
QLABEL_SECONDARY_TEXT = "#90a4ae"
QLABEL_TERTIARY_TEXT = "#b0bec5"
QLABEL_MUTED_TEXT = "#888888"
QLABEL_INFO_TEXT = "#bbbbbb"
QLABEL_ERROR_TEXT = "#ff4444"
QLABEL_WHITE_TEXT = "white"
QLABEL_BORDER_GRAY = "#3a3a3a"
QLABEL_DARK_BORDER = "#555555"
QLABEL_ERROR_BG = "#3a2222"
QLABEL_DARK_BG = "#181818"

STATUS_COLORS = {
    "ready": "",
    "error": "#ff6b6b",
    "success": "#51cf66",
    "warning": "#ffa726",
    "info": "#74c0fc",
    "loading": "#adb5bd",
    "metadata_skipped": "#adb5bd",
    "metadata_extended": "#ff8a65",
    "metadata_basic": "#74c0fc",
    "action_completed": "#87ceeb",
    "neutral_info": "#d3d3d3",
    "operation_success": "#90ee90",
    "alert_notice": "#ffd700",
    "critical_error": "#ffb6c1",
    "file_cleared": "#87ceeb",
    "no_action": "#d3d3d3",
    "rename_success": "#90ee90",
    "validation_error": "#ffb6c1",
    "drag_action": "#87ceeb",
    "hash_success": "#90ee90",
    "duplicate_found": "#ffd700",
    "metadata_success": "#90ee90",
}

THEME_COLORS = {
    "dark": {
        "background": "#181818",
        "text": "#f0ebd8",
        "text_selected": "#0d1321",
        "alternate_row": "#232323",
        "hover": "#3e5c76",
        "selected": "#748cab",
        "selected_hover": "#8a9bb4",
        "button_bg": "#2a2a2a",
        "button_hover": "#4a6fa5",
        "border": "#3a3b40",
    },
    "light": {
        "background": "#ffffff",
        "text": "#212121",
        "text_selected": "#ffffff",
        "alternate_row": "#f8f8f8",
        "hover": "#e3f2fd",
        "selected": "#1976d2",
        "selected_hover": "#42a5f5",
        "button_bg": "#f5f5f5",
        "button_hover": "#e3f2fd",
        "border": "#cccccc",
    },
}

CONTEXT_MENU_COLORS = {
    "background": "#232323",
    "text": "#f0ebd8",
    "selected_bg": "#748cab",
    "selected_text": "#0d1321",
    "disabled_text": "#888888",
    "separator": "#5a5a5a",
}

THEME_TOKENS = {
    "dark": {
        "background": "#181818",
        "background_alternate": "#232323",
        "background_lighter": "#2a2a2a",
        "background_elevated": "#1e1e1e",
        "text": "#f0ebd8",
        "text_secondary": "#888888",
        "text_tertiary": "#666666",
        "text_disabled": "#555555",
        "disabled_text": "#888888",
        "text_muted": "#888888",
        "metadata_group_text": "#ddd6ba",
        "hover": "#3e5c76",
        "selected": "#748cab",
        "selected_text": "#0d1321",
        "selected_hover": "#8a9bb4",
        "pressed": "#5a7fa0",
        "border": "#3a3b40",
        "border_light": "#4a4b50",
        "separator": "#5a5a5a",
        "outline": "#748cab",
        "success": "#4ade80",
        "warning": "#fbbf24",
        "error": "#ff6b6b",
        "info": "#60a5fa",
        "neutral": "#94a3b8",
        "menu_background": "#232323",
        "menu_text": "#f0ebd8",
        "menu_selected_bg": "#748cab",
        "menu_selected_text": "#0d1321",
        "menu_disabled_text": "#888888",
        "menu_separator": "#5a5a5a",
        "table_background": "#181818",
        "table_alternate": "#232323",
        "table_header_bg": "#2a2a2a",
        "table_header_text": "#f0ebd8",
        "table_selection_bg": "#748cab",
        "table_selection_text": "#0d1321",
        "table_hover_bg": "#3e5c76",
        "table_grid": "#3a3b40",
        "dialog_background": "#1e1e1e",
        "dialog_title_bg": "#252525",
        "dialog_border": "#3a3b40",
        "button_bg": "#2a2a2a",
        "button_text": "#f0ebd8",
        "button_hover_bg": "#3e5c76",
        "button_hover_text": "#f0ebd8",
        "button_pressed_bg": "#748cab",
        "button_pressed_text": "#0d1321",
        "button_disabled_bg": "#1a1a1a",
        "button_disabled_text": "#555555",
        "combo_dropdown_background": "#181818",
        "combo_item_background_hover": "#3e5c76",
        "combo_item_background_selected": "#748cab",
        "input_bg": "#2a2a2a",
        "input_text": "#f0ebd8",
        "input_border": "#3a3b40",
        "input_focus_border": "#748cab",
        "input_placeholder": "#666666",
        "input_hover_bg": "#1f1f1f",
        "input_focus_bg": "#1a1a1a",
        "border_hover": "#555555",
        "border_muted": "#808080",
        "accent": "#748cab",
        "scrollbar_bg": "#1e1e1e",
        "scrollbar_handle": "#4a4a4a",
        "scrollbar_handle_hover": "#5a5a5a",
        "tree_branch": "#3a3b40",
        "tree_indicator": "#748cab",
        "results_header_bg": "#2d2d2d",
        "results_row_hover": "#3a3a3a",
        "results_footer_bg": "#2a2a2a",
        "preview_bg": "#232323",
        "preview_border": "#3a3b40",
        "module_plate_bg": "#2a2a2a",
        "module_plate_border": "#3a3b40",
        "module_drag_handle": "#4a4a4a",
        "module_drag_hover": "#748cab",
        "companion_info_text": "#888888",
        "companion_note_text": "#888888",
        "edit_info_text": "#888888",
        "edit_error_text": "#ff6b6b",
        "history_title_text": "#f0ebd8",
        "history_info_text": "#888888",
        "tooltip_bg": "#2b2b2b",
        "tooltip_text": "#f0ebd8",
        "tooltip_border": "#555555",
        "tooltip_error_bg": "#3d1e1e",
        "tooltip_error_text": "#ffaaaa",
        "tooltip_error_border": "#cc4444",
        "tooltip_warning_bg": "#3d3d1e",
        "tooltip_warning_text": "#ffffaa",
        "tooltip_warning_border": "#cccc44",
        "tooltip_info_bg": "#1e2d3d",
        "tooltip_info_text": "#aaccff",
        "tooltip_info_border": "#4488cc",
        "tooltip_success_bg": "#1e3d1e",
        "tooltip_success_text": "#aaffaa",
        "tooltip_success_border": "#44cc44",
        "table_row_height": "22",
        "button_height": "24",
        "combo_height": "22",
        "combo_item_height": "22",
    },
    "light": {
        "background": "#ffffff",
        "background_alternate": "#f8f8f8",
        "text": "#212121",
        "text_secondary": "#666666",
        "text_muted": "#999999",
        "metadata_group_text": "#6b6b6b",
    },
}

METADATA_ICON_COLORS = {
    "basic": "#e8f4fd",
    "extended": EXTENDED_METADATA_COLOR,
    "invalid": "#ff6b6b",
    "loaded": "#51cf66",
    "modified": "#fffd9c",
    "partial": "#ffd139",
    "hash": "#ce93d8",
    "none": "#404040",
}
