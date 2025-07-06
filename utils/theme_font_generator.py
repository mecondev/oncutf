"""
Module: theme_font_generator.py

Author: Michael Economou
Date: 2025-07-06

theme_font_generator.py
Generates CSS font styles with DPI-aware sizing for cross-platform consistency.
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)


def generate_dpi_aware_css() -> str:
    """
    Generate CSS with DPI-aware font sizes for all UI elements.

    Returns:
        CSS string with properly scaled font sizes
    """
    try:
        from utils.dpi_helper import get_font_sizes
        font_sizes = get_font_sizes()
    except ImportError:
        logger.warning("[Theme] DPI helper not available, using default font sizes")
        font_sizes = {
            'small': 8,
            'normal': 9,
            'medium': 10,
            'large': 11,
            'tree': 9,
            'table': 9,
        }

    css_template = f"""
/* DPI-Aware Font Sizes */

/* Tree Views (file tree, metadata tree) */
QTreeView {{
    font-size: {font_sizes['tree']}pt;
}}

QTreeView::item {{
    font-size: {font_sizes['tree']}pt;
    min-height: {max(18, font_sizes['tree'] + 8)}px;
}}

/* Table Views */
QTableView {{
    font-size: {font_sizes['table']}pt;
}}

QTableView::item {{
    font-size: {font_sizes['table']}pt;
    min-height: {max(20, font_sizes['table'] + 10)}px;
}}

/* Headers */
QHeaderView::section {{
    font-size: {font_sizes['normal']}pt;
    font-weight: 500;
    min-height: {max(22, font_sizes['normal'] + 12)}px;
}}

/* Labels */
QLabel {{
    font-size: {font_sizes['normal']}pt;
}}

/* Small labels (status, info) */
QLabel[class="small"] {{
    font-size: {font_sizes['small']}pt;
}}

/* Large labels (titles, headers) */
QLabel[class="large"] {{
    font-size: {font_sizes['large']}pt;
    font-weight: 600;
}}

/* Buttons */
QPushButton {{
    font-size: {font_sizes['medium']}pt;
    font-weight: 500;
    min-height: {max(24, font_sizes['medium'] + 14)}px;
}}

/* ComboBoxes */
QComboBox {{
    font-size: {font_sizes['normal']}pt;
    min-height: {max(20, font_sizes['normal'] + 10)}px;
}}

QComboBox QAbstractItemView {{
    font-size: {font_sizes['normal']}pt;
}}

QComboBox QAbstractItemView::item {{
    font-size: {font_sizes['normal']}pt;
    min-height: {max(18, font_sizes['normal'] + 8)}px;
}}

/* Line Edits */
QLineEdit {{
    font-size: {font_sizes['normal']}pt;
    min-height: {max(20, font_sizes['normal'] + 10)}px;
}}

/* Text Edits */
QTextEdit {{
    font-size: {font_sizes['normal']}pt;
}}

/* Group Boxes */
QGroupBox {{
    font-size: {font_sizes['medium']}pt;
    font-weight: 500;
}}

/* Tooltips */
QToolTip {{
    font-size: {font_sizes['small']}pt;
}}

/* Menu Items */
QMenu {{
    font-size: {font_sizes['normal']}pt;
}}

QMenu::item {{
    font-size: {font_sizes['normal']}pt;
    min-height: {max(18, font_sizes['normal'] + 8)}px;
}}

/* Status Bar */
QStatusBar {{
    font-size: {font_sizes['small']}pt;
}}

/* Tab Widget */
QTabWidget::tab-bar {{
    font-size: {font_sizes['normal']}pt;
}}

QTabBar::tab {{
    font-size: {font_sizes['normal']}pt;
    min-height: {max(22, font_sizes['normal'] + 12)}px;
}}

/* Scroll Bars - adjust size based on DPI */
QScrollBar:vertical {{
    width: {max(12, font_sizes['normal'] + 2)}px;
}}

QScrollBar:horizontal {{
    height: {max(12, font_sizes['normal'] + 2)}px;
}}

/* Progress Bars */
QProgressBar {{
    font-size: {font_sizes['small']}pt;
    /* min-height removed - let widgets control their own height */
}}
"""

    logger.debug(f"[Theme] Generated DPI-aware CSS with font sizes: {font_sizes}")
    return css_template


def get_tree_font_size() -> int:
    """Get the appropriate font size for tree views."""
    try:
        from utils.dpi_helper import get_font_sizes
        return get_font_sizes()['tree']
    except ImportError:
        return 9


def get_table_font_size() -> int:
    """Get the appropriate font size for table views."""
    try:
        from utils.dpi_helper import get_font_sizes
        return get_font_sizes()['table']
    except ImportError:
        return 9


def get_ui_font_sizes() -> Dict[str, int]:
    """Get all UI font sizes for programmatic use."""
    try:
        from utils.dpi_helper import get_font_sizes
        return get_font_sizes()
    except ImportError:
        return {
            'small': 8,
            'normal': 9,
            'medium': 10,
            'large': 11,
            'tree': 9,
            'table': 9,
        }
