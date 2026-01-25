"""Module: column_manager.py.

Author: Michael Economou
Date: 2026-01-02 (Refactored)

LEGACY ADAPTER: Thin adapter for UnifiedColumnService

This module provides backward compatibility for Qt-specific column management.
All business logic delegates to UnifiedColumnService.

MIGRATION NOTE: This class is now a thin adapter (~150 lines) that delegates
business logic to UnifiedColumnService while handling Qt-specific integration.

Classes:
    ColumnManager: Qt integration adapter for column management
"""

import contextlib
from typing import Any

from oncutf.core.pyqt_imports import QHeaderView, QTableView, QTreeView, QWidget
from oncutf.core.ui_managers.column_service import get_column_service
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ColumnManager:
    """Qt integration adapter for column management.

    This class handles Qt-specific operations and delegates business logic
    to UnifiedColumnService.

    Responsibilities:
    - Qt signal connection and handling
    - Scrollbar detection and management
    - Splitter integration
    - Header configuration

    Delegates to UnifiedColumnService:
    - Column configuration loading
    - Width calculation and validation
    - User preferences
    - Visibility management
    """

    def __init__(self, main_window: QWidget) -> None:
        """Initialize the ColumnManager adapter.

        Args:
            main_window: Reference to the main window for accessing components

        """
        self.main_window = main_window
        self._service = get_column_service()
        self._programmatic_resize_active = False

    def configure_table_columns(self, table_view: QTableView | QTreeView, table_type: str) -> None:
        """Configure columns for a specific table view.

        Args:
            table_view: The table/tree view to configure
            table_type: Type identifier ('file_table', 'metadata_tree', 'preview_old', 'preview_new')

        """
        # Skip preview tables as they auto-regulate
        if table_type in ["preview_old", "preview_new"]:
            logger.debug(
                "[ColumnManager] Skipping auto-regulating table type: %s",
                table_type,
                extra={"dev_only": True},
            )
            return

        # TEMPORARILY skip file_table to avoid conflicts with FileTableView column management
        if table_type == "file_table":
            logger.debug(
                "[ColumnManager] Skipping file_table - managed by FileTableView directly",
                extra={"dev_only": True},
            )
            return

        if not table_view.model():
            logger.warning("[ColumnManager] No model set for table type: %s", table_type)
            return

        # Get header - QTableView has horizontalHeader(), QTreeView has header()
        header = self._get_header(table_view)
        if not header:
            logger.warning("[ColumnManager] No header found for table type: %s", table_type)
            return

        # Get visible column configs from service
        visible_configs = self._service.get_visible_column_configs()

        logger.debug(
            "[ColumnManager] Configuring %d columns for %s",
            len(visible_configs),
            table_type,
            extra={"dev_only": True},
        )

        # Apply Qt-specific configuration
        for i, config in enumerate(visible_configs):
            column_index = i + 1  # Skip column 0 (status)

            if column_index >= table_view.model().columnCount():
                logger.debug(
                    "[ColumnManager] Skipping column %d - exceeds model column count",
                    column_index,
                    extra={"dev_only": True},
                )
                continue

            # Set resize mode (always interactive for user control)
            header.setSectionResizeMode(column_index, QHeaderView.Interactive)

            # Get width from service
            width = self._service.get_column_width(config.key)
            table_view.setColumnWidth(column_index, width)

        # Connect resize signals for user preference tracking
        self._connect_resize_signals(table_view, table_type)

        # Ensure horizontal scrollbar state is correct
        if isinstance(table_view, QTableView):
            self.ensure_horizontal_scrollbar_state(table_view)

        logger.debug(
            "[ColumnManager] Configured columns for table type: %s",
            table_type,
            extra={"dev_only": True},
        )

    def _get_header(self, table_view: QTableView | QTreeView) -> QHeaderView | None:
        """Get header from table view (handles both QTableView and QTreeView).

        Args:
            table_view: The table/tree view

        Returns:
            QHeaderView or None if not found

        """
        if isinstance(table_view, QTableView):
            return table_view.horizontalHeader()
        elif isinstance(table_view, QTreeView):
            return table_view.header()
        return None

    def ensure_horizontal_scrollbar_state(self, table_view: QTableView) -> None:
        """Ensure horizontal scrollbar appears when needed and hides when not.

        Args:
            table_view: The table view to adjust

        """
        # This is Qt-specific logic - keep in adapter
        try:
            # Calculate total width needed
            total_width_needed = sum(
                table_view.columnWidth(i) for i in range(table_view.model().columnCount())
            )

            # Get viewport width
            viewport_width = table_view.viewport().width()

            # Add scrollbar if content wider than viewport
            from PyQt5.QtCore import Qt

            if total_width_needed > viewport_width:
                table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            else:
                table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        except Exception as e:
            logger.warning("[ColumnManager] Error adjusting scrollbar state: %s", e)

    def _connect_resize_signals(self, table_view: QTableView | QTreeView, table_type: str) -> None:
        """Connect to resize signals for tracking user preferences.

        Args:
            table_view: The table/tree view
            table_type: Type identifier

        """
        header = self._get_header(table_view)
        if not header:
            return

        # Disconnect existing signals to avoid duplicates
        with contextlib.suppress(TypeError):
            # No connections existed
            header.sectionResized.disconnect()

        # Connect to resize signal
        header.sectionResized.connect(
            lambda logical_index, old_size, new_size: self._on_column_resized(
                table_view, table_type, logical_index, old_size, new_size
            )
        )

    def _on_column_resized(
        self,
        table_view: QTableView | QTreeView,
        table_type: str,
        logical_index: int,
        old_size: int,
        new_size: int,
    ) -> None:
        """Handle column resize event.

        Args:
            table_view: The table/tree view
            table_type: Type identifier
            logical_index: Column index
            old_size: Previous width
            new_size: New width

        """
        # Ignore programmatic resizes
        if self._programmatic_resize_active:
            return

        # Ignore column 0 (status column)
        if logical_index == 0:
            return

        # Get column key from service
        column_mapping = self._service.get_column_mapping()
        column_key = column_mapping.get(logical_index)

        if not column_key:
            return

        # Validate and save width via service
        validated_width = self._service.validate_column_width(column_key, new_size)
        self._service.set_column_width(column_key, validated_width)

        logger.debug(
            "[ColumnManager] User resized %s column %d from %d to %d",
            table_type,
            logical_index,
            old_size,
            validated_width,
            extra={"dev_only": True},
        )

    def adjust_columns_for_splitter_change(
        self, table_view: QTableView | QTreeView, table_type: str
    ) -> None:
        """Adjust columns when splitter position changes.

        Args:
            table_view: The table/tree view to adjust
            table_type: Type identifier

        """
        # For now, this is mostly handled by FileTableView
        # Could add smart resize logic here if needed
        if isinstance(table_view, QTableView):
            self.ensure_horizontal_scrollbar_state(table_view)

    def reset_user_preferences(self, table_type: str, column_index: int | None = None) -> None:
        """Reset user preferences for columns to allow auto-sizing.

        Args:
            table_type: Type identifier
            column_index: Specific column to reset, or None for all columns

        """
        # Delegate to service
        if column_index is not None:
            # Get column key from mapping
            column_mapping = self._service.get_column_mapping()
            column_key = column_mapping.get(column_index)
            if column_key:
                self._service.reset_column_width(column_key)
                logger.debug(
                    "[ColumnManager] Reset width for column: %s",
                    column_key,
                    extra={"dev_only": True},
                )
        else:
            # Reset all
            self._service.reset_all_widths()
            logger.debug(
                "[ColumnManager] Reset all column widths",
                extra={"dev_only": True},
            )

    # Legacy compatibility methods - delegate to service

    def save_column_state(self, table_type: str) -> dict[str, Any]:
        """Save current column state for persistence (LEGACY).

        This is maintained for backward compatibility but delegates to service.

        Args:
            table_type: Type identifier

        Returns:
            Dictionary containing column state data

        """
        # Service handles persistence automatically, so this is mostly a no-op
        logger.debug(
            "[ColumnManager] save_column_state called (handled by service)",
            extra={"dev_only": True},
        )
        return {}

    def load_column_state(self, table_type: str, state_data: dict[str, Any]) -> None:
        """Load column state from persistence (LEGACY).

        This is maintained for backward compatibility but delegates to service.

        Args:
            table_type: Type identifier
            state_data: Dictionary containing column state data

        """
        # Service loads from config automatically, so this is mostly a no-op
        logger.debug(
            "[ColumnManager] load_column_state called (handled by service)",
            extra={"dev_only": True},
        )

