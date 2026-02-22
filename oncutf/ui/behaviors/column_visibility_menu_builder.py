"""Module: column_visibility_menu_builder.py.

Author: Michael Economou
Date: 2026-01-12

Helper for building column visibility context menus.
Extracts column visibility menu logic from InteractiveHeader.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from PyQt5.QtWidgets import QAction, QMenu

from oncutf.config import FILE_TABLE_COLUMN_CONFIG
from oncutf.ui.helpers.icons_loader import get_menu_icon
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_cached_logger(__name__)


class ColumnVisibilityMenuBuilder:
    """Builder for column visibility context menus.

    Encapsulates the logic for creating grouped column visibility menus
    with proper categorization and styling.
    """

    # Column categories for grouping
    COLUMN_CATEGORIES: ClassVar[dict[str, list[str]]] = {
        "File": [
            "color",
            "type",
            "file_size",
            "modified",
            "path",
            "file_hash",
            "duration",
        ],
        "Image": [
            "image_size",
            "rotation",
            "iso",
            "aperture",
            "shutter_speed",
            "white_balance",
            "compression",
            "color_space",
        ],
        "Video": ["video_fps", "video_avg_bitrate", "video_codec", "video_format"],
        "Audio": ["audio_channels", "audio_format"],
        "Metadata": ["artist", "copyright", "owner_name"],
        "Device": [
            "device_manufacturer",
            "device_model",
            "device_serial_no",
            "target_umid",
        ],
    }

    def __init__(self, file_list_view) -> None:
        """Initialize builder with file table view.

        Args:
            file_list_view: File table view with _column_mgmt_behavior attribute.

        """
        self._file_list_view = file_list_view

    def build_menu(
        self,
        parent_menu: QMenu,
        toggle_callback: Callable[[str], None],
    ) -> None:
        """Build and add column visibility submenu to parent menu.

        Args:
            parent_menu: Parent menu to add submenu to.
            toggle_callback: Callback function for toggling column visibility.
                            Receives column_key as argument.

        """
        try:
            # Check if file table view has required behavior
            if not hasattr(self._file_list_view, "_column_mgmt_behavior"):
                logger.warning("File table view missing _column_mgmt_behavior")
                return

            # Create submenu
            columns_menu = QMenu("Show Columns", parent_menu)
            columns_menu.setIcon(get_menu_icon("view_column"))

            # Get current visible columns
            visible_columns_list = (
                self._file_list_view._column_mgmt_behavior.get_visible_columns_list()
            )

            # Build grouped columns
            column_groups = self._build_column_groups()

            # Add grouped columns to menu
            self._populate_menu(columns_menu, column_groups, visible_columns_list, toggle_callback)

            # Add submenu to parent
            parent_menu.addMenu(columns_menu)

        except Exception as e:
            logger.warning("Failed to build column visibility menu: %s", e)

    def _build_column_groups(self) -> dict[str, list[tuple[str, dict]]]:
        """Build column groups by category.

        Returns:
            Dictionary mapping category name to list of (column_key, column_config) tuples.

        """
        # Initialize groups
        column_groups: dict[str, list[tuple[str, dict]]] = {
            "File": [],
            "Image": [],
            "Video": [],
            "Audio": [],
            "Metadata": [],
            "Device": [],
            "Other": [],
        }

        # Categorize columns
        for column_key, column_config in FILE_TABLE_COLUMN_CONFIG.items():
            if not column_config.get("removable", True):
                continue  # Skip non-removable columns like filename

            # Find category
            category = "Other"
            for cat_name, cat_columns in self.COLUMN_CATEGORIES.items():
                if column_key in cat_columns:
                    category = cat_name
                    break

            column_groups[category].append((column_key, column_config))

        return column_groups

    def _populate_menu(
        self,
        menu: QMenu,
        column_groups: dict[str, list[tuple[str, dict]]],
        visible_columns_list: list[str],
        toggle_callback: Callable[[str], None],
    ) -> None:
        """Populate menu with grouped columns.

        Args:
            menu: Menu to populate.
            column_groups: Dictionary of column groups.
            visible_columns_list: List of currently visible column keys.
            toggle_callback: Callback for toggling column visibility.

        """
        first_group = True
        for group_name in [
            "File",
            "Image",
            "Video",
            "Audio",
            "Metadata",
            "Device",
            "Other",
        ]:
            group_columns = column_groups[group_name]
            if not group_columns:
                continue

            # Add separator between groups (except before first group)
            if not first_group:
                menu.addSeparator()
            first_group = False

            # Sort columns within group alphabetically
            from typing import cast

            group_columns.sort(key=lambda x: cast("str", x[1]["title"]))

            # Add group columns
            for column_key, column_config in group_columns:
                # Always use full title in menu
                action = QAction(column_config["title"], menu)

                # Get visibility state
                is_visible = column_key in visible_columns_list

                # Set icon based on visibility
                if is_visible:
                    action.setIcon(get_menu_icon("toggle_on"))
                else:
                    action.setIcon(get_menu_icon("toggle_off"))

                # Connect toggle action
                action.triggered.connect(
                    lambda _checked=False, key=column_key: toggle_callback(key)
                )
                menu.addAction(action)
