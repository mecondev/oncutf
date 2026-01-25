"""oncutf.models.file_table.column_manager.

Column visibility and mapping management for file table model.

This module provides the ColumnManager class that handles dynamic column
configuration, visibility changes, and efficient column add/remove operations.

Author: Michael Economou
Date: 2026-01-01
"""

from typing import Any

from PyQt5.QtCore import QModelIndex

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ColumnManager:
    """Manages column visibility and mapping for file table display.

    Responsibilities:
        - Track visible columns and their order
        - Create mapping from column index to column key
        - Handle efficient column addition/removal with Qt signals
        - Provide fallback to model reset for complex changes
    """

    def __init__(self, model: Any) -> None:
        """Initialize the ColumnManager.

        Args:
            model: Reference to FileTableModel (for Qt signal methods)

        """
        self.model = model
        self._visible_columns = self._load_default_visible_columns()
        self._column_mapping = self._create_column_mapping()

    def _load_default_visible_columns(self) -> list[str]:
        """Load default visible columns configuration using UnifiedColumnService."""
        from oncutf.core.ui_managers import get_column_service

        service = get_column_service()
        return service.get_visible_columns()

    def _create_column_mapping(self) -> dict[int, str]:
        """Create mapping from column index to column key based on internal visible columns.

        Column 0 is reserved for status column, so visible columns start at index 1.
        """
        mapping = {}
        for i, column_key in enumerate(self._visible_columns):
            mapping[i + 1] = column_key
        logger.debug(
            "[ColumnMapping] Created mapping from visible columns: %s",
            mapping,
            extra={"dev_only": True},
        )
        return mapping

    def get_visible_columns(self) -> list[str]:
        """Get the current list of visible column keys.

        Returns:
            Copy of the visible columns list

        """
        return self._visible_columns.copy()

    def get_column_mapping(self) -> dict[int, str]:
        """Get the current column mapping.

        Returns:
            Dict mapping column index to column key

        """
        return self._column_mapping.copy()

    def get_column_key(self, column_index: int) -> str | None:
        """Get column key for a given column index.

        Args:
            column_index: Column index (0 = status, 1+ = data columns)

        Returns:
            Column key or None if not found

        """
        return self._column_mapping.get(column_index)

    def get_column_count(self) -> int:
        """Get total column count (visible columns + status column).

        Returns:
            Total number of columns

        """
        return len(self._visible_columns) + 1  # +1 for status column

    def update_visible_columns(self, visible_columns: list[str]) -> None:
        """Update the list of visible columns and refresh the model.

        Args:
            visible_columns: List of column keys to display (e.g., ['filename', 'extension'])

        """
        logger.debug(
            "[ColumnManager] update_visible_columns called with: %s",
            visible_columns,
            extra={"dev_only": True},
        )

        # Invalidate UnifiedColumnService cache when columns change
        from oncutf.core.ui_managers import get_column_service

        service = get_column_service()
        service.invalidate_cache()
        logger.debug("[ColumnManager] Invalidated UnifiedColumnService cache")

        if visible_columns != self._visible_columns:
            old_column_count = len(self._visible_columns) + 1
            new_column_count = len(visible_columns) + 1

            logger.debug(
                "[ColumnManager] Column count changing from %d to %d",
                old_column_count,
                new_column_count,
            )

            # Debug state before changes
            logger.debug("[ColumnManager] STATE BEFORE UPDATE:", extra={"dev_only": True})
            self.debug_column_state()

            # Find which columns are being added or removed
            old_columns = set(self._visible_columns)
            new_columns = set(visible_columns)

            added_columns = new_columns - old_columns
            removed_columns = old_columns - new_columns

            logger.debug(
                "[ColumnManager] Added columns: %s",
                added_columns,
                extra={"dev_only": True},
            )
            logger.debug(
                "[ColumnManager] Removed columns: %s",
                removed_columns,
                extra={"dev_only": True},
            )

            # Since we always add/remove one column at a time, use the optimized methods
            # with fallback to reset if something goes wrong
            try:
                if len(added_columns) == 1 and len(removed_columns) == 0:
                    # Single column addition
                    logger.debug(
                        "[ColumnManager] Single column addition - using insertColumns",
                        extra={"dev_only": True},
                    )
                    self._handle_single_column_addition(visible_columns, next(iter(added_columns)))
                elif len(added_columns) == 0 and len(removed_columns) == 1:
                    # Single column removal
                    logger.debug(
                        "[ColumnManager] Single column removal - using removeColumns",
                        extra={"dev_only": True},
                    )
                    self._handle_single_column_removal(visible_columns, next(iter(removed_columns)))
                else:
                    # Should not happen in normal use, but handle gracefully
                    logger.warning(
                        "[ColumnManager] Unexpected column change pattern: +%d, -%d",
                        len(added_columns),
                        len(removed_columns),
                    )
                    self._handle_reset_model(visible_columns)
            except Exception:
                logger.warning(
                    "[ColumnManager] Column operation failed, falling back to reset",
                    exc_info=True,
                )
                self._handle_reset_model(visible_columns)

            # Debug state after changes
            logger.debug("[ColumnManager] STATE AFTER UPDATE:", extra={"dev_only": True})
            self.debug_column_state()

            # Update view for column changes
            if hasattr(self.model, "_table_view_ref") and self.model._table_view_ref:
                logger.debug(
                    "[ColumnManager] Calling table view refresh methods", extra={"dev_only": True}
                )
                if hasattr(self.model._table_view_ref, "refresh_columns_after_model_change"):
                    logger.debug(
                        "[ColumnManager] Calling refresh_columns_after_model_change after visible columns update",
                        extra={"dev_only": True},
                    )
                    self.model._table_view_ref.refresh_columns_after_model_change()
                if hasattr(self.model._table_view_ref, "_update_scrollbar_visibility"):
                    logger.debug(
                        "[ColumnManager] Forcing horizontal scrollbar update after visible columns update",
                        extra={"dev_only": True},
                    )
                    self.model._table_view_ref._update_scrollbar_visibility()
        else:
            logger.debug(
                "[ColumnManager] No column changes needed - visible columns are the same",
                extra={"dev_only": True},
            )

    def _handle_reset_model(self, visible_columns: list[str]) -> None:
        """Handle column changes using resetModel - safe but less efficient."""
        logger.debug("[ColumnManager] Using resetModel for column changes")

        # Store current files to preserve them
        current_files = self.model.files.copy() if self.model.files else []
        logger.debug(
            "[ColumnManager] Storing %d files before reset",
            len(current_files),
            extra={"dev_only": True},
        )

        self.model.beginResetModel()

        # Update the visible columns and mapping
        self._visible_columns = visible_columns.copy()
        self._column_mapping = self._create_column_mapping()

        # Always restore files after reset (they should be preserved)
        self.model.files = current_files
        logger.debug(
            "[ColumnManager] Restored %d files after reset",
            len(self.model.files),
            extra={"dev_only": True},
        )

        self.model.endResetModel()

    def _handle_single_column_addition(
        self, new_visible_columns: list[str], added_column: str
    ) -> None:
        """Handle adding a single column efficiently."""
        logger.debug("[ColumnManager] Adding single column: %s", added_column)

        try:
            # Find where this column should be inserted
            new_index = new_visible_columns.index(added_column)
            # Convert to actual column index (+1 for status column)
            insert_position = new_index + 1

            logger.debug(
                "[ColumnManager] Inserting column '%s' at position %d",
                added_column,
                insert_position,
                extra={"dev_only": True},
            )

            # Signal that we're inserting a column
            self.model.beginInsertColumns(QModelIndex(), insert_position, insert_position)

            # Update internal state
            self._visible_columns = new_visible_columns.copy()
            self._column_mapping = self._create_column_mapping()

            logger.debug(
                "[ColumnManager] Updated column mapping: %s",
                self._column_mapping,
                extra={"dev_only": True},
            )

            self.model.endInsertColumns()

            logger.debug(
                "[ColumnManager] Single column addition completed successfully",
                extra={"dev_only": True},
            )

        except Exception:
            logger.exception("[ColumnManager] Error in _handle_single_column_addition")
            raise  # Re-raise to trigger fallback

    def _handle_single_column_removal(
        self, new_visible_columns: list[str], removed_column: str
    ) -> None:
        """Handle removing a single column efficiently."""
        logger.debug("[ColumnManager] Removing single column: %s", removed_column)

        try:
            # Find where this column currently is
            if removed_column in self._visible_columns:
                old_index = self._visible_columns.index(removed_column)
                # Convert to actual column index (+1 for status column)
                remove_position = old_index + 1

                logger.debug(
                    "[ColumnManager] Removing column '%s' from position %d",
                    removed_column,
                    remove_position,
                    extra={"dev_only": True},
                )

                # Signal that we're removing a column
                self.model.beginRemoveColumns(QModelIndex(), remove_position, remove_position)

                # Update internal state
                self._visible_columns = new_visible_columns.copy()
                self._column_mapping = self._create_column_mapping()

                logger.debug(
                    "[ColumnManager] Updated column mapping: %s",
                    self._column_mapping,
                    extra={"dev_only": True},
                )

                self.model.endRemoveColumns()

                logger.debug(
                    "[ColumnManager] Single column removal completed successfully",
                    extra={"dev_only": True},
                )
            else:
                logger.warning(
                    "[ColumnManager] Column '%s' not found in current visible columns",
                    removed_column,
                )
                raise ValueError(f"Column '{removed_column}' not found in current visible columns")

        except Exception:
            logger.exception("[ColumnManager] Error in _handle_single_column_removal")
            raise  # Re-raise to trigger fallback

    def debug_column_state(self) -> None:
        """Debug method to print current column state."""
        logger.debug("[ColumnDebug] === ColumnManager State ===", extra={"dev_only": True})
        logger.debug(
            "[ColumnDebug] Visible columns: %s",
            self._visible_columns,
            extra={"dev_only": True},
        )
        logger.debug(
            "[ColumnDebug] Column mapping: %s",
            self._column_mapping,
            extra={"dev_only": True},
        )
        logger.debug(
            "[ColumnDebug] Column count: %d",
            self.get_column_count(),
            extra={"dev_only": True},
        )
        logger.debug("[ColumnDebug] =========================================", extra={"dev_only": True})
