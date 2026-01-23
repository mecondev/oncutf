"""Combo box popup sizing helper.

Author: Michael Economou
Date: December 28, 2025

Utility to fix QComboBox popup sizing issues:
- Prevents internal scroller (white bars + chevrons) for small item counts
- Removes frame borders that cause white lines
- Computes proper height based on actual row metrics (DPI-aware)

This is Qt-specific workaround logic extracted from widgets to avoid copy-paste.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import QComboBox, QFrame

from oncutf.core.theme_manager import get_theme_manager
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


def prepare_combo_popup(combo: QComboBox) -> None:
    """Prepare combo box popup BEFORE showing to prevent visual artifacts.

    Must be called BEFORE combo.showPopup() or super().showPopup() to:
    - Remove frame borders (prevents white line at top)
    - Set up frameless container

    Args:
        combo: QComboBox instance to prepare

    """
    view = combo.view()
    if not view:
        return

    # CRITICAL: Remove view frame BEFORE showing popup
    # This prevents the white line artifact at popup top
    view.setFrameShape(QFrame.Shape.NoFrame)
    view.setLineWidth(0)

    # Also ensure the popup container (parent window) has no frame
    container = view.window()
    if container and hasattr(container, 'setFrameShape'):
        container.setFrameShape(QFrame.Shape.NoFrame)

    logger.debug("Combo popup prepared: frameless container set")


def apply_combo_popup_metrics(combo: QComboBox, *, pre_show: bool = False) -> None:
    """Apply proper sizing to combo popup to prevent internal scroller.

    Qt can show an internal popup scroller (white bars + chevrons) when the
    popup height is even slightly smaller than the real row heights. Using
    a theme constant is often not enough due to font metrics / DPI / delegate
    size hints. We compute row height from the actual view.

    Call this twice:
    1. BEFORE super().showPopup() with pre_show=True (optional pre-sizing)
    2. AFTER super().showPopup() with pre_show=False (final adjustment)

    Args:
        combo: QComboBox instance to size
        pre_show: Whether this is called before or after popup is shown

    """
    try:
        count = combo.count()
        if count <= 0:
            return

        theme = get_theme_manager()
        fallback_item_h = int(theme.get_constant("combo_item_height"))

        max_visible = max(1, int(combo.maxVisibleItems()))
        visible_rows = min(count, max_visible)

        view = combo.view()
        if view is None:
            return

        # --- Compute real row height (prefer sizeHintForRow) ---
        row_h = int(view.sizeHintForRow(0))
        if row_h <= 0:
            # Fallback if view isn't polished yet (before first show)
            fm = QFontMetrics(view.font())
            # 1.35 multiplier accounts for row padding + delegate spacing
            row_h = int(fm.height() * 1.35)

        row_h = max(row_h, fallback_item_h)

        # Include view frame + content margins (critical for accurate height!)
        m = view.contentsMargins()
        frame_extra = int(getattr(view, "frameWidth", lambda: 0)()) * 2
        extra_h = frame_extra + m.top() + m.bottom()

        if count <= max_visible:
            # Short list: show all items without scrolling
            view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

            desired_view_h = (visible_rows * row_h) + extra_h

            # +2px safety buffer prevents scroller on some Qt styles/DPI combos
            desired_view_h += 2

            view.setMinimumHeight(desired_view_h)
            view.setMaximumHeight(desired_view_h)

            # Avoid over-constraining the container
            # Let it size to the view; only set bounds
            container = view.window()
            if container is not None:
                container.setMinimumHeight(desired_view_h)
                container.setMaximumHeight(desired_view_h)
        else:
            # Long list: enable scrolling for items beyond max_visible
            view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

            desired_view_h = (max_visible * row_h) + extra_h
            desired_view_h += 2
            view.setMaximumHeight(desired_view_h)

        logger.debug(
            "Combo popup metrics: pre_show=%s, count=%d, visible=%d, row_h=%d, extra=%d, total=%d",
            pre_show, count, visible_rows, row_h, extra_h, desired_view_h
        )
    except Exception as e:
        logger.warning("Failed to apply combo popup metrics: %s", e)
