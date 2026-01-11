"""
FONT SYSTEM QUICKSTART GUIDE
============================

This guide shows how to use the new font system in oncutf.
"""

# ============================================================================
# QUICK START: Switch Between Fonts (One Change)
# ============================================================================

# File: oncutf/config/ui.py (Line 17)
# Current default:
# DEFAULT_UI_FONT = "jetbrains"

# To switch to Inter:
# DEFAULT_UI_FONT = "inter"

# That's it! Everything else adapts automatically.


# ============================================================================
# PATTERN 1: Using Dynamic Fonts in Dialogs
# ============================================================================

from oncutf.core.theme_manager import get_theme_manager
from oncutf.utils.ui.stylesheet_utils import inject_font_family


def create_dialog_with_dynamic_font():
    """Example: Dialog that respects DEFAULT_UI_FONT configuration."""
    from PyQt5.QtWidgets import QDialog

    theme = get_theme_manager()

    dialog_qss = f"""
        QDialog {{
            background-color: {theme.get_color('dialog_background')};
            color: {theme.get_color('text')};
            font-family: "Inter", "Segoe UI", Arial, sans-serif;
            font-size: 10pt;
        }}
        QLabel {{
            color: {theme.get_color('text')};
            font-family: "Inter", "Segoe UI", Arial, sans-serif;
        }}
    """

    dialog = QDialog()
    # BEFORE: Font was hardcoded, always Inter
    # dialog.setStyleSheet(dialog_qss)

    # AFTER: Font is dynamic, respects DEFAULT_UI_FONT
    dialog.setStyleSheet(inject_font_family(dialog_qss))

    # If DEFAULT_UI_FONT = "jetbrains":
    #   → Uses "JetBrains Mono", "Courier New", monospace
    # If DEFAULT_UI_FONT = "inter":
    #   → Uses "Inter", "Segoe UI", Arial, sans-serif


# ============================================================================
# PATTERN 2: Using Dynamic Fonts with QFont Objects
# ============================================================================

from PyQt5.QtWidgets import QLabel

from oncutf.utils.ui.fonts import get_default_ui_font


def create_label_with_dynamic_font():
    """Example: Label that respects DEFAULT_UI_FONT + size adjustment."""
    label = QLabel("Hello World")

    # BEFORE: Fixed to Inter, no size adjustment
    # font = QFont("Inter", 10)
    # label.setFont(font)

    # AFTER: Respects configuration + auto size adjustment
    font = get_default_ui_font(size=10)  # Adjusted to 11pt if using JetBrains
    label.setFont(font)

    # If DEFAULT_UI_FONT = "jetbrains":
    #   → Size is 10 + 1 = 11pt (from FONT_SIZE_ADJUSTMENTS)
    # If DEFAULT_UI_FONT = "inter":
    #   → Size is 10 + 0 = 10pt (no adjustment)


# ============================================================================
# PATTERN 3: Checking Current Font Configuration
# ============================================================================

from oncutf.config.ui import (
    DEFAULT_UI_FONT,
    FONT_FAMILIES,
    FONT_SIZE_ADJUSTMENTS,
    get_ui_font_family,
)


def check_font_config():
    """Example: Inspect current font configuration."""
    from oncutf.utils.logger_factory import get_cached_logger

    logger = get_cached_logger(__name__)
    logger.info("Current font: %s", DEFAULT_UI_FONT)
    # Output: "jetbrains" or "inter"

    logger.info("Available fonts: %s", list(FONT_FAMILIES.keys()))
    # Output: ['inter', 'jetbrains']

    logger.info("Size adjustment: +%dpt", FONT_SIZE_ADJUSTMENTS[DEFAULT_UI_FONT])
    # Output: +1pt (if jetbrains) or +0pt (if inter)

    logger.info("CSS string: %s", get_ui_font_family())
    # Output: "JetBrains Mono", "Courier New", monospace  (if jetbrains)
    # Output: "Inter", "Segoe UI", Arial, sans-serif      (if inter)


# ============================================================================
# PATTERN 4: Testing Font Switching Programmatically
# ============================================================================

def test_font_switching():
    """Example: Test that fonts switch correctly."""
    from oncutf.utils.ui.stylesheet_utils import inject_font_family

    test_qss = 'QWidget { font-family: "Inter", "Segoe UI", Arial, sans-serif; }'

    import oncutf.config.ui as ui_config

    # Test with JetBrains
    ui_config.DEFAULT_UI_FONT = "jetbrains"
    result = inject_font_family(test_qss)
    assert "JetBrains Mono" in result, "Should use JetBrains font"

    # Test with Inter
    ui_config.DEFAULT_UI_FONT = "inter"
    result = inject_font_family(test_qss)
    assert "Inter" in result, "Should use Inter font"


# ============================================================================
# PATTERN 5: Creating New Fonts (Future Extension)
# ============================================================================

def add_fira_font_example():
    """Example: How to add a new font in the future."""

    # Step 1: Add to config (oncutf/config/ui.py)
    # FONT_SIZE_ADJUSTMENTS["fira"] = 0
    # FONT_FAMILIES["fira"] = '"Fira Mono", "Courier New", monospace'

    # Step 2: Create loader (oncutf/utils/ui/fonts.py)
    # class FiraFonts:
    #     def __init__(self):
    #         self.fonts = {}
    #     def get_font(self, style, size):
    #         # Load from filesystem or QRC
    #         return QFont("Fira Mono", size)

    # Step 3: Register singleton (main.py)
    # _get_fira_fonts()

    # Step 4: Switch font (oncutf/config/ui.py line 17)
    # DEFAULT_UI_FONT = "fira"

    # Result: UI automatically uses Fira font everywhere!
    # No changes needed to dialogs, menus, or stylesheets.


# ============================================================================
# QUICK REFERENCE
# ============================================================================

"""
SWITCH FONTS:
   Edit oncutf/config/ui.py line 17:
   DEFAULT_UI_FONT = "jetbrains"  # or "inter"

USE IN DIALOGS:
   from oncutf.utils.ui.stylesheet_utils import inject_font_family
   dialog.setStyleSheet(inject_font_family(qss_string))

USE IN QFont:
   from oncutf.utils.ui.fonts import get_default_ui_font
   font = get_default_ui_font(size=10)
   widget.setFont(font)

CHECK CONFIG:
   from oncutf.config.ui import DEFAULT_UI_FONT, get_ui_font_family
   print(f"Font: {DEFAULT_UI_FONT}")
   print(f"CSS: {get_ui_font_family()}")

ADD NEW FONT:
   1. Update FONT_FAMILIES in config
   2. Create loader class
   3. Register in main.py
   4. Change DEFAULT_UI_FONT
   5. Done! UI updates automatically

CURRENT FONTS:
   - JetBrains Mono (monospace, +1pt adjustment)
   - Inter (sans-serif, no adjustment)

SIZE ADJUSTMENTS:
   JetBrains looks slightly smaller, so +1pt is added
   This makes both fonts appear visually consistent at same size
"""


# ============================================================================
# TESTING & VERIFICATION
# ============================================================================

def run_all_examples():
    """Run all examples to verify font system works."""
    from oncutf.utils.logger_factory import get_cached_logger

    logger = get_cached_logger(__name__)
    logger.info("Testing font system...")

    logger.info("1. Checking configuration:")
    check_font_config()

    logger.info("2. Testing font switching:")
    test_font_switching()

    logger.info("3. Font extension info:")
    add_fira_font_example()

    logger.info("All examples completed successfully!")


if __name__ == "__main__":
    run_all_examples()
