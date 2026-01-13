"""Module: view_config.py

Author: Michael Economou
Date: 2025-12-23

View configuration handler for the metadata tree widget.

This module handles all view configuration and styling:
- Placeholder mode vs normal mode configuration
- Header visibility and column management
- Scrollbar policies
- Style updates

The handler operates on a MetadataTreeView instance passed to it.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from oncutf.config import METADATA_TREE_COLUMN_WIDTHS
from oncutf.core.pyqt_imports import (
    QAbstractItemView,
    QHeaderView,
    Qt,
)
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_tree.view import MetadataTreeView

logger = get_cached_logger(__name__)


class MetadataTreeViewConfig:
    """Handler for metadata tree view configuration.

    This class encapsulates all view configuration logic:
    - Initial view setup (edit triggers, row heights, etc.)
    - Placeholder mode configuration (empty state)
    - Normal mode configuration (with content)
    - Header visibility management
    - Column resize handling
    - Scrollbar policy management

    Usage:
        config = MetadataTreeViewConfig(tree_view)
        config.setup_tree_view_properties()
        config.configure_placeholder_mode(model)
    """

    def __init__(self, tree_view: MetadataTreeView) -> None:
        """Initialize the view configuration handler.

        Args:
            tree_view: The MetadataTreeView instance this handler configures

        """
        self._tree_view = tree_view
        # Runtime column width tracking (preserved across file selection changes)
        self._runtime_widths: dict[str, int] = {}

    def setup_tree_view_properties(self) -> None:
        """Configure standard tree view properties."""
        view = self._tree_view
        view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        view.setUniformRowHeights(True)
        view.expandToDepth(1)
        view.setRootIsDecorated(True)  # Show expand/collapse arrows for consistency
        view.setItemsExpandable(True)  # Ensure items can be expanded/collapsed
        view.setAcceptDrops(True)
        view.viewport().setAcceptDrops(True)
        view.setDragDropMode(QAbstractItemView.DropOnly)
        view.setAlternatingRowColors(True)

        # Use global theme manager for styling (handled by main.qss)
        # Manual stylesheet injection removed to avoid path resolution issues
        # and conflicts with the global theme manager.

    def detect_placeholder_mode(self, model: Any) -> bool:
        """Detect if the model contains placeholder content.

        Args:
            model: The model to check

        Returns:
            True if the model is in placeholder mode (empty or placeholder text)

        """
        # Check if it's a proxy model and get the source model
        source_model = model
        if hasattr(model, "sourceModel") and callable(model.sourceModel):
            source_model = model.sourceModel()
            if not source_model:
                return True  # No source model = placeholder

        # Empty model (for PNG placeholder) is also placeholder mode
        if source_model.rowCount() == 0:
            return True

        if source_model.rowCount() == 1:
            root = source_model.invisibleRootItem()
            if root and root.rowCount() == 1:
                item = root.child(0, 0)
                if item and "No file" in item.text():
                    return True

        return False

    def configure_placeholder_mode(self, _model: Any) -> None:
        """Configure view for placeholder mode with anti-flickering.

        Args:
            _model: The model (interface parameter for consistency)

        """
        view = self._tree_view

        # Protection against repeated calls to placeholder mode
        if (
            getattr(view, "_is_placeholder_mode", False)
            and view.placeholder_helper
            and view.placeholder_helper.is_visible()
        ):
            return  # Already fully configured for placeholder mode

        # Only reset current file path when entering placeholder mode
        view._current_file_path = None

        # Save current widths to runtime before switching to placeholder
        # This preserves user's column widths when switching between files
        header = view.header()
        if header and header.count() >= 2:
            current_key = view.columnWidth(0)
            current_value = view.columnWidth(1)
            # Save if widths are valid (not placeholder widths)
            if current_key > 0 and current_value > 0:
                # Don't overwrite runtime widths with placeholder widths (140, 250)
                if current_key != METADATA_TREE_COLUMN_WIDTHS["PLACEHOLDER_KEY_WIDTH"] or \
                   current_value != METADATA_TREE_COLUMN_WIDTHS["PLACEHOLDER_VALUE_WIDTH"]:
                    self._runtime_widths["key"] = current_key
                    self._runtime_widths["value"] = current_value

        # Use batch updates to prevent flickering
        view.setUpdatesEnabled(False)

        try:
            # Disconnect resize signal to prevent placeholder widths from being saved
            with contextlib.suppress(AttributeError, RuntimeError, TypeError):
                header.sectionResized.disconnect()

            # Show placeholder using unified helper
            if view.placeholder_helper:
                view.placeholder_helper.show()
            else:
                logger.warning("[MetadataTree] Could not show placeholder - missing helper")

            # Placeholder mode: Fixed columns, no selection, no hover, NO HORIZONTAL SCROLLBAR
            view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # type: ignore[arg-type]

            header.setSectionResizeMode(0, QHeaderView.Fixed)
            header.setSectionResizeMode(1, QHeaderView.Fixed)
            # Use placeholder widths for placeholder mode (won't trigger save due to disconnected signal)
            header.resizeSection(0, METADATA_TREE_COLUMN_WIDTHS["PLACEHOLDER_KEY_WIDTH"])
            header.resizeSection(1, METADATA_TREE_COLUMN_WIDTHS["PLACEHOLDER_VALUE_WIDTH"])

            # Disable header interactions and hide header in placeholder mode
            header.setEnabled(False)
            header.setSectionsClickable(False)
            header.setSortIndicatorShown(False)
            header.hide()

            # Disable tree interactions but keep drag & drop working
            view.setSelectionMode(QAbstractItemView.NoSelection)
            view.setItemsExpandable(False)
            view.setRootIsDecorated(False)
            view.setContextMenuPolicy(Qt.NoContextMenu)
            view.setMouseTracking(False)

            # Set placeholder property for styling
            view.setProperty("placeholder", True)

        finally:
            # Re-enable updates and force a single refresh
            view.setUpdatesEnabled(True)
            if hasattr(view, "viewport") and callable(getattr(view.viewport(), "update", None)):
                view.viewport().update()

    def configure_normal_mode(self) -> None:
        """Configure view for normal content mode with anti-flickering."""
        view = self._tree_view

        # Use batch updates to prevent flickering
        view.setUpdatesEnabled(False)

        try:
            # Hide placeholder when showing normal content
            if view.placeholder_helper:
                view.placeholder_helper.hide()

            # Normal content mode: HORIZONTAL SCROLLBAR enabled but controlled
            self._update_scrollbar_policy_intelligently(Qt.ScrollBarAsNeeded)
            # Also ensure vertical scrollbar is set properly
            view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # type: ignore[arg-type]

            header = view.header()

            # Re-enable header interactions
            header.setEnabled(True)
            header.setSectionsClickable(True)
            header.setSortIndicatorShown(False)

            # Disable hover effect on metadata tree header
            try:
                from oncutf.core.theme_manager import get_theme_manager
                theme = get_theme_manager()
                header_bg = theme.get_color("table_header_bg")
                header_text = theme.get_color("table_header_text")

                # Apply no-hover style to metadata tree header
                header.setStyleSheet(
                    f"QHeaderView::section:hover {{"
                    f"  background-color: {header_bg};"
                    f"  color: {header_text};"
                    f"}}"
                )
            except Exception as e:
                logger.debug("[MetadataTree] Failed to set header no-hover style: %s", e)

            header.show()

            if self._runtime_widths:
                key_width = self._runtime_widths.get("key", METADATA_TREE_COLUMN_WIDTHS["NORMAL_KEY_INITIAL_WIDTH"])
                value_width = self._runtime_widths.get("value", METADATA_TREE_COLUMN_WIDTHS["NORMAL_VALUE_INITIAL_WIDTH"])
            else:
                saved_widths = self._get_saved_column_widths()
                if saved_widths:
                    key_width = saved_widths.get("key", METADATA_TREE_COLUMN_WIDTHS["NORMAL_KEY_INITIAL_WIDTH"])
                    value_width = saved_widths.get("value", METADATA_TREE_COLUMN_WIDTHS["NORMAL_VALUE_INITIAL_WIDTH"])
                    self._runtime_widths["key"] = key_width
                    self._runtime_widths["value"] = value_width
                else:
                    from oncutf.utils.shared.json_config_manager import get_app_config_manager
                    from oncutf.utils.ui.layout_calculators import (
                        get_metadata_tree_widths_from_ratios,
                    )

                    config_manager = get_app_config_manager()
                    window_config = config_manager.get_category("window")
                    ratios = window_config.get("metadata_tree_column_ratios", {"key": 0.38, "value": 0.62})

                    # Add extra pixels to force horizontal scrollbar when content is wide
                    # This makes total width exceed viewport, allowing scroll
                    extra_width_for_scrollbar = 100
                    viewport_width = view.viewport().width() if view.viewport() else 868
                    panel_width = viewport_width + extra_width_for_scrollbar

                    min_widths = {
                        "key": METADATA_TREE_COLUMN_WIDTHS["KEY_MIN_WIDTH"],
                        "value": METADATA_TREE_COLUMN_WIDTHS["VALUE_MIN_WIDTH"],
                    }
                    max_widths = {"key": METADATA_TREE_COLUMN_WIDTHS["KEY_MAX_WIDTH"]}

                    calculated_widths = get_metadata_tree_widths_from_ratios(
                        panel_width, ratios, min_widths, max_widths
                    )
                    key_width = calculated_widths["key"]
                    value_width = calculated_widths["value"]

                    # Log width calculations for debugging
                    logger.info(
                        "Metadata tree column widths - Viewport: %d, Panel: %d, Key: %d, Value: %d, Total: %d",
                        viewport_width, panel_width, key_width, value_width, key_width + value_width
                    )

            # Key column: min 80px, initial width, max 800px
            header.setSectionResizeMode(0, QHeaderView.Interactive)
            header.setMinimumSectionSize(METADATA_TREE_COLUMN_WIDTHS["KEY_MIN_WIDTH"])
            header.resizeSection(0, key_width)

            # Value column: min 250px, initial width, allows wide content without stretching
            header.setSectionResizeMode(1, QHeaderView.Interactive)
            header.resizeSection(1, value_width)

            # Set specific min/max sizes per column
            header.setMinimumSectionSize(METADATA_TREE_COLUMN_WIDTHS["KEY_MIN_WIDTH"])
            header.setMaximumSectionSize(METADATA_TREE_COLUMN_WIDTHS["KEY_MAX_WIDTH"])

            # Connect resize signals to immediately update display
            self._connect_column_resize_signals()

            # Initial scrollbar check after setting column widths
            self._update_scrollbar_after_resize()

            # Re-enable tree interactions
            view.setSelectionMode(QAbstractItemView.SingleSelection)
            view.setItemsExpandable(True)
            view.setRootIsDecorated(True)  # Show expand/collapse arrows for categories
            view.setContextMenuPolicy(Qt.CustomContextMenu)
            view.setMouseTracking(True)

            # Clear placeholder property
            view.setProperty("placeholder", False)
            view.setAttribute(Qt.WA_NoMousePropagation, False)

            # Force style update
            self._force_style_update()

        finally:
            # Re-enable updates and force a single refresh
            view.setUpdatesEnabled(True)
            if hasattr(view, "viewport") and callable(getattr(view.viewport(), "update", None)):
                view.viewport().update()

    def update_header_visibility(self) -> None:
        """Update header visibility based on whether there is content in the model."""
        view = self._tree_view

        if not view.model():
            logger.debug("[MetadataTree] No model - header hidden", extra={"dev_only": True})
            return

        header = view.header()
        if not header:
            logger.debug(
                "[MetadataTree] No header - cannot update visibility", extra={"dev_only": True}
            )
            return

        # Hide header when in placeholder mode, show when there's content
        header.setVisible(not view._is_placeholder_mode)

        logger.debug(
            "[MetadataTree] Header visibility: %s (placeholder_mode: %s)",
            "hidden" if view._is_placeholder_mode else "visible",
            view._is_placeholder_mode,
            extra={"dev_only": True},
        )

    def _connect_column_resize_signals(self) -> None:
        """Connect column resize signals to update display immediately."""
        header = self._tree_view.header()
        if header:
            # Disconnect any existing connections
            with contextlib.suppress(AttributeError, RuntimeError, TypeError):
                header.sectionResized.disconnect()

            # Connect to immediate update
            header.sectionResized.connect(self._on_column_resized)

    def _on_column_resized(self, logical_index: int, _old_size: int, new_size: int) -> None:
        """Handle column resize events to update display immediately and save to config."""
        view = self._tree_view

        # Update runtime widths (preserved across file selection changes)
        column_key = "key" if logical_index == 0 else "value"
        self._runtime_widths[column_key] = new_size

        # Save to config (mark dirty for auto-save)
        try:
            from oncutf.utils.shared.json_config_manager import get_app_config_manager

            config_manager = get_app_config_manager()
            window_config = config_manager.get_category("window")

            # Get current metadata_tree_column_widths or create new dict
            metadata_widths = window_config.get("metadata_tree_column_widths", {})
            metadata_widths[column_key] = new_size

            window_config.set("metadata_tree_column_widths", metadata_widths)
            config_manager.mark_dirty()

            logger.debug(
                "[MetadataTree] Column '%s' resized to %dpx, marked dirty",
                column_key,
                new_size,
                extra={"dev_only": True},
            )
        except Exception as e:
            logger.warning("[MetadataTree] Failed to save column width: %s", e)

        # Update scrollbar policy based on new total width
        self._update_scrollbar_after_resize()

        # Force immediate viewport update
        view.viewport().update()

        # Update the view geometry
        view.updateGeometry()

        # Force a repaint to ensure changes are visible immediately
        view.repaint()

    def _update_scrollbar_after_resize(self) -> None:
        """Update horizontal scrollbar visibility after column resize."""
        view = self._tree_view
        header = view.header()

        # Calculate total column width
        total_width = sum(header.sectionSize(i) for i in range(header.count()))
        viewport_width = view.viewport().width()

        # Show scrollbar if content exceeds viewport
        if total_width > viewport_width:
            view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            logger.debug(
                "[MetadataTree] Scrollbar enabled - Total: %dpx > Viewport: %dpx",
                total_width,
                viewport_width,
                extra={"dev_only": True},
            )
        else:
            # Keep AsNeeded but log when content fits
            logger.debug(
                "[MetadataTree] Scrollbar not needed - Total: %dpx <= Viewport: %dpx",
                total_width,
                viewport_width,
                extra={"dev_only": True},
            )

        # Force Qt to recalculate scrollbar geometries and range
        view.updateGeometries()

        # Also update the horizontal scrollbar range explicitly
        h_scrollbar = view.horizontalScrollBar()
        if h_scrollbar and total_width > viewport_width:
            h_scrollbar.setRange(0, total_width - viewport_width)
            h_scrollbar.setPageStep(viewport_width)

    def _update_scrollbar_policy_intelligently(self, target_policy: int) -> None:
        """Update scrollbar policy only if different from current."""
        view = self._tree_view
        current_policy = view.horizontalScrollBarPolicy()
        if current_policy != target_policy:
            view.setHorizontalScrollBarPolicy(target_policy)

    def _force_style_update(self) -> None:
        """Force Qt style system to update."""
        view = self._tree_view
        view.style().unpolish(view)
        view.style().polish(view)

    @staticmethod
    def make_placeholder_items_non_selectable(model: Any) -> None:
        """Make placeholder items non-selectable.

        Args:
            model: The model containing placeholder items

        """
        root = model.invisibleRootItem()
        item = root.child(0, 0)
        if item:
            item.setSelectable(False)
        value_item = root.child(0, 1)
        if value_item:
            value_item.setSelectable(False)

    def _get_saved_column_widths(self) -> dict[str, int] | None:
        """Load saved column widths from config.

        Returns:
            Dictionary with saved widths or None if not available

        """
        try:
            from oncutf.utils.shared.json_config_manager import ConfigManager

            config_manager = ConfigManager()
            window_config = config_manager.get_category("window")
            saved_widths = window_config.get("metadata_tree_column_widths")

            if saved_widths and isinstance(saved_widths, dict):
                logger.debug(
                    "[MetadataTree] Loaded saved column widths: %s",
                    saved_widths,
                    extra={"dev_only": True},
                )
                return saved_widths
        except Exception as e:
            logger.debug(
                "[MetadataTree] Could not load saved column widths: %s",
                e,
                extra={"dev_only": True},
            )

        return None
