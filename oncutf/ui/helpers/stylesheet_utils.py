"""Module: stylesheet_utils.py.

Author: Michael Economou
Date: 2026-01-11

Stylesheet utility functions for dynamic font configuration.

Provides helper functions to generate CSS/QSS strings that respect
the DEFAULT_UI_FONT configuration for easy font switching.
"""


def get_font_family_css(widget_type: str | None = None) -> str:
    """Get font-family CSS value based on configuration.

    Args:
        widget_type: Optional widget type (e.g., 'table', 'tree') for specialized fonts

    Returns:
        CSS font-family string with appropriate fallbacks

    Example:
        >>> get_font_family_css()  # Uses DEFAULT_UI_FONT (inter)
        '"Inter", "Segoe UI", Arial, sans-serif'
        >>> get_font_family_css('table')  # Uses monospace for tables
        '"JetBrains Mono", "Courier New", monospace'

    """
    from oncutf.config.ui import get_ui_font_family

    return get_ui_font_family(widget_type)


def inject_font_family(qss_string: str, widget_type: str | None = None) -> str:
    """Replace hardcoded font-family with dynamic value in QSS string.

    This function replaces the common Inter fallback chain with the
    configured default UI font, optionally using widget-specific fonts.

    Args:
        qss_string: QSS stylesheet string with hardcoded Inter font
        widget_type: Optional widget type (e.g., 'table', 'tree') for specialized fonts

    Returns:
        QSS string with dynamic font-family

    Example:
        >>> qss = 'QWidget { font-family: "Inter", "Segoe UI", Arial, sans-serif; }'
        >>> inject_font_family(qss)  # Uses DEFAULT_UI_FONT (inter)
        'QWidget { font-family: "Inter", "Segoe UI", Arial, sans-serif; }'
        >>> inject_font_family(qss, 'table')  # Uses monospace for tables
        'QWidget { font-family: "JetBrains Mono", "Courier New", monospace; }'

    """
    # Replace common Inter font chain
    result = qss_string.replace(
        '"Inter", "Segoe UI", Arial, sans-serif', get_font_family_css(widget_type)
    )
    return result

