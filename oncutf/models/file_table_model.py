"""file_table_model.py

Author: Michael Economou
Date: 2025-05-01

This module defines the FileTableModel class, which is a custom QAbstractTableModel
for displaying file data in a table view. The model manages file items, supports
sorting, and provides metadata status icons.

Classes:
    FileTableModel: Custom table model for file management.
"""

from datetime import datetime
from typing import Any

from oncutf.core.application_context import get_app_context
from oncutf.core.pyqt_imports import (
    QAbstractTableModel,
    QColor,
    QIcon,
    QItemSelection,
    QItemSelectionModel,
    QItemSelectionRange,
    QModelIndex,
    QPainter,
    QPixmap,
    Qt,
    QVariant,
    pyqtSignal,
)
from oncutf.models.file_item import FileItem
from oncutf.utils.filesystem.file_status_helpers import get_hash_for_file, has_hash

# initialize logger
from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.ui.icons_loader import load_metadata_icons

logger = get_cached_logger(__name__)


class FileTableModel(QAbstractTableModel):
    """Table model for displaying and managing a list of FileItem objects
    in a QTableView. Supports row selection (blue highlighting), sorting, and preview updates.
    Now supports displaying both metadata and hash icons in column 0.
    """

    sort_changed = pyqtSignal()  # Emitted when sort() is called

    def __init__(self, parent_window: Any = None) -> None:
        super().__init__()
        logger.debug("FileTableModel __init__ called", extra={"dev_only": True})
        self.parent_window: Any = parent_window
        self.files: list[FileItem] = []
        self._direct_loader = None

        # Load icons for metadata status using the correct functions
        self.metadata_icons = load_metadata_icons()

        # Dynamic columns support
        self._visible_columns = self._load_default_visible_columns()
        self._column_mapping = self._create_column_mapping()

        # Tooltip cache to avoid repeated get_entry() calls on hover
        self._tooltip_cache: dict[str, str] = {}  # full_path -> tooltip

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

    def update_visible_columns(self, visible_columns: list[str]) -> None:
        logger.debug(
            "[FileTableModel] update_visible_columns called with: %s",
            visible_columns,
            extra={"dev_only": True},
        )

        # Invalidate UnifiedColumnService cache when columns change
        from oncutf.core.ui_managers import get_column_service

        service = get_column_service()
        service.invalidate_cache()
        logger.debug("[FileTableModel] Invalidated UnifiedColumnService cache")

        if visible_columns != self._visible_columns:
            old_column_count = len(self._visible_columns) + 1
            new_column_count = len(visible_columns) + 1

            logger.debug(
                "[FileTableModel] Column count changing from %d to %d",
                old_column_count,
                new_column_count,
            )

            # Debug state before changes
            logger.debug("[FileTableModel] STATE BEFORE UPDATE:", extra={"dev_only": True})
            self.debug_column_state()

            # Find which columns are being added or removed
            old_columns = set(self._visible_columns)
            new_columns = set(visible_columns)

            added_columns = new_columns - old_columns
            removed_columns = old_columns - new_columns

            logger.debug(
                "[FileTableModel] Added columns: %s",
                added_columns,
                extra={"dev_only": True},
            )
            logger.debug(
                "[FileTableModel] Removed columns: %s",
                removed_columns,
                extra={"dev_only": True},
            )

            # Since we always add/remove one column at a time, use the optimized methods
            # with fallback to reset if something goes wrong
            try:
                if len(added_columns) == 1 and len(removed_columns) == 0:
                    # Single column addition
                    logger.debug(
                        "[FileTableModel] Single column addition - using insertColumns",
                        extra={"dev_only": True},
                    )
                    self._handle_single_column_addition(visible_columns, list(added_columns)[0])
                elif len(added_columns) == 0 and len(removed_columns) == 1:
                    # Single column removal
                    logger.debug(
                        "[FileTableModel] Single column removal - using removeColumns",
                        extra={"dev_only": True},
                    )
                    self._handle_single_column_removal(visible_columns, list(removed_columns)[0])
                else:
                    # Should not happen in normal use, but handle gracefully
                    logger.warning(
                        "[FileTableModel] Unexpected column change pattern: +%d, -%d",
                        len(added_columns),
                        len(removed_columns),
                    )
                    self._handle_reset_model(visible_columns)
            except Exception:
                logger.warning(
                    "[FileTableModel] Column operation failed, falling back to reset",
                    exc_info=True,
                )
                self._handle_reset_model(visible_columns)

            # Debug state after changes
            logger.debug("[FileTableModel] STATE AFTER UPDATE:", extra={"dev_only": True})
            self.debug_column_state()

            # Update view for column changes
            if hasattr(self, "_table_view_ref") and self._table_view_ref:
                logger.debug(
                    "[FileTableModel] Calling table view refresh methods", extra={"dev_only": True}
                )
                if hasattr(self._table_view_ref, "refresh_columns_after_model_change"):
                    logger.debug(
                        "[FileTableModel] Calling refresh_columns_after_model_change after visible columns update",
                        extra={"dev_only": True},
                    )
                    self._table_view_ref.refresh_columns_after_model_change()
                if hasattr(self._table_view_ref, "_update_scrollbar_visibility"):
                    logger.debug(
                        "[FileTableModel] Forcing horizontal scrollbar update after visible columns update",
                        extra={"dev_only": True},
                    )
                    self._table_view_ref._update_scrollbar_visibility()
        else:
            logger.debug(
                "[FileTableModel] No column changes needed - visible columns are the same",
                extra={"dev_only": True},
            )

    def _handle_reset_model(self, visible_columns: list[str]) -> None:
        """Handle column changes using resetModel - safe but less efficient."""
        logger.debug("[FileTableModel] Using resetModel for column changes")

        # Store current files to preserve them
        current_files = self.files.copy() if self.files else []
        logger.debug(
            "[FileTableModel] Storing %d files before reset",
            len(current_files),
            extra={"dev_only": True},
        )

        self.beginResetModel()

        # Update the visible columns and mapping
        self._visible_columns = visible_columns.copy()
        self._column_mapping = self._create_column_mapping()

        # Always restore files after reset (they should be preserved)
        self.files = current_files
        logger.debug(
            "[FileTableModel] Restored %d files after reset",
            len(self.files),
            extra={"dev_only": True},
        )

        self.endResetModel()

    def _handle_single_column_addition(
        self, new_visible_columns: list[str], added_column: str
    ) -> None:
        """Handle adding a single column efficiently."""
        logger.debug("[FileTableModel] Adding single column: %s", added_column)

        try:
            # Find where this column should be inserted
            new_index = new_visible_columns.index(added_column)
            # Convert to actual column index (+1 for status column)
            insert_position = new_index + 1

            logger.debug(
                "[FileTableModel] Inserting column '%s' at position %d",
                added_column,
                insert_position,
                extra={"dev_only": True},
            )

            # Signal that we're inserting a column
            self.beginInsertColumns(QModelIndex(), insert_position, insert_position)

            # Update internal state
            self._visible_columns = new_visible_columns.copy()
            self._column_mapping = self._create_column_mapping()

            logger.debug(
                "[FileTableModel] Updated column mapping: %s",
                self._column_mapping,
                extra={"dev_only": True},
            )

            self.endInsertColumns()

            logger.debug(
                "[FileTableModel] Single column addition completed successfully",
                extra={"dev_only": True},
            )

        except Exception:
            logger.exception("[FileTableModel] Error in _handle_single_column_addition")
            raise  # Re-raise to trigger fallback

    def _handle_single_column_removal(
        self, new_visible_columns: list[str], removed_column: str
    ) -> None:
        """Handle removing a single column efficiently."""
        logger.debug("[FileTableModel] Removing single column: %s", removed_column)

        try:
            # Find where this column currently is
            if removed_column in self._visible_columns:
                old_index = self._visible_columns.index(removed_column)
                # Convert to actual column index (+1 for status column)
                remove_position = old_index + 1

                logger.debug(
                    "[FileTableModel] Removing column '%s' from position %d",
                    removed_column,
                    remove_position,
                    extra={"dev_only": True},
                )

                # Signal that we're removing a column
                self.beginRemoveColumns(QModelIndex(), remove_position, remove_position)

                # Update internal state
                self._visible_columns = new_visible_columns.copy()
                self._column_mapping = self._create_column_mapping()

                logger.debug(
                    "[FileTableModel] Updated column mapping: %s",
                    self._column_mapping,
                    extra={"dev_only": True},
                )

                self.endRemoveColumns()

                logger.debug(
                    "[FileTableModel] Single column removal completed successfully",
                    extra={"dev_only": True},
                )
            else:
                logger.warning(
                    "[FileTableModel] Column '%s' not found in current visible columns",
                    removed_column,
                )
                raise ValueError(f"Column '{removed_column}' not found in current visible columns")

        except Exception:
            logger.exception("[FileTableModel] Error in _handle_single_column_removal")
            raise  # Re-raise to trigger fallback

    def get_visible_columns(self) -> list[str]:
        return self._visible_columns.copy()

    def debug_column_state(self) -> None:
        """Debug method to print current column state."""
        logger.debug("[ColumnDebug] === FileTableModel Column State ===", extra={"dev_only": True})
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
            self.columnCount(),
            extra={"dev_only": True},
        )
        logger.debug(
            "[ColumnDebug] Row count: %d",
            self.rowCount(),
            extra={"dev_only": True},
        )
        logger.debug(
            "[ColumnDebug] Files loaded: %d",
            len(self.files),
            extra={"dev_only": True},
        )
        logger.debug(
            "[ColumnDebug] =========================================", extra={"dev_only": True}
        )

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: ARG002
        count = len(self._visible_columns) + 1  # +1 for status column
        return count

    def _has_hash_cached(self, file_path: str) -> bool:
        """Check if a file has a hash stored in the persistent cache.

        Args:
            file_path: Full path to the file

        Returns:
            bool: True if file has a cached hash, False otherwise

        """
        return has_hash(file_path)

    def _get_hash_value(self, file_path: str) -> str:
        """Get the hash value for a file from the persistent cache.

        Args:
            file_path: Full path to the file

        Returns:
            str: Hash value if found, empty string otherwise

        """
        hash_value = get_hash_for_file(file_path)
        return hash_value if hash_value else ""

    def _get_unified_tooltip(self, file: Any) -> str:
        """Get unified tooltip for all columns showing metadata and hash status.

        Uses tooltip cache to avoid repeated get_entry() calls on hover events.
        Cache is invalidated when metadata/hash changes.
        """
        # Check cache first
        cached_tooltip = self._tooltip_cache.get(file.full_path)
        if cached_tooltip is not None:
            return cached_tooltip

        tooltip_parts = []

        # Add metadata status
        if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
            entry = self.parent_window.metadata_cache.get_entry(file.full_path)
            if entry and hasattr(entry, "data") and entry.data:
                field_count = len(entry.data)
                # Check the is_extended property of the MetadataEntry object
                if hasattr(entry, "is_extended") and entry.is_extended:
                    tooltip_parts.append(f"{field_count} extended metadata")
                else:
                    tooltip_parts.append(f"{field_count} metadata")
            else:
                tooltip_parts.append("no metadata")

        # Add hash status
        if self._has_hash_cached(file.full_path):
            hash_value = self._get_hash_value(file.full_path)
            if hash_value:
                # Show full hash value
                tooltip_parts.append(f"hash {hash_value}")
            else:
                tooltip_parts.append("hash available")
        else:
            tooltip_parts.append("no hash")

        tooltip = "\n".join(tooltip_parts)

        # Cache the result
        self._tooltip_cache[file.full_path] = tooltip

        return tooltip

    def _create_combined_icon(self, metadata_status: str, hash_status: str) -> QIcon:
        """Create a combined icon showing metadata status (left) and hash status (right).
        Always shows both icons - uses grayout color for missing states.

        Args:
            metadata_status: Status of metadata ('loaded', 'extended', 'modified', 'invalid', 'none')
            hash_status: Status of hash ('hash' for available, 'none' for not available)

        Returns:
            QIcon: Combined icon with metadata and hash status

        """
        # Use hardcoded width for status column (column 0)
        combined_width = 50  # Fixed width for status column
        combined_height = 16
        combined_pixmap = QPixmap(combined_width, combined_height)
        combined_pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(combined_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get metadata icon
        metadata_icon = self.metadata_icons.get(metadata_status)
        if metadata_icon:
            # Draw metadata icon on the left (2px from left edge)
            painter.drawPixmap(2, 0, metadata_icon)

        # Get hash icon
        hash_icon = self.metadata_icons.get(hash_status)
        if hash_icon:
            # Draw hash icon on the right (32px from left = 50-16-2 for 2px right margin)
            painter.drawPixmap(32, 0, hash_icon)

        painter.end()
        return QIcon(combined_pixmap)

    def _create_color_icon(self, hex_color: str) -> QIcon:
        """Create a color swatch icon for the color column.

        Args:
            hex_color: Hex color string (e.g., "#ff0000")

        Returns:
            QIcon with colored rectangle swatch

        """
        # Create 22x30 pixmap for color swatch (fits 24px row height)
        width = 18
        height = 16
        pixmap = QPixmap(width + 2, height)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw filled rounded rectangle
        color = QColor(hex_color)
        painter.setBrush(color)
        painter.setPen(QColor(0, 0, 0, 50))  # Light border for visibility
        painter.drawRoundedRect(2, 2, width - 2, height - 2, 2, 2)
        painter.end()

        return QIcon(pixmap)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: ARG002
        count = len(self.files)
        return count

    def _get_column_data(self, file: Any, column_key: str, role: int) -> Any:
        """Get data for a specific column key."""
        if role == Qt.DisplayRole:
            if column_key == "filename":
                return str(file.filename)
            elif column_key == "color":
                # Color column shows no text, only icon
                return ""
            elif column_key == "file_size":
                return str(file.get_human_readable_size())
            elif column_key == "type":
                return str(file.extension)
            elif column_key == "modified":
                if isinstance(file.modified, datetime):
                    return file.modified.strftime("%Y-%m-%d %H:%M:%S")
                return str(file.modified)
            elif column_key == "file_hash":
                return self._get_hash_value(file.full_path)
            # For metadata columns, try to get from metadata cache
            else:
                # Try to get metadata value from cache
                if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
                    try:
                        entry = self.parent_window.metadata_cache.get_entry(file.full_path)
                        if entry and hasattr(entry, "data") and entry.data:
                            # Use centralized metadata field mapper
                            from oncutf.core.metadata.field_mapper import (
                                MetadataFieldMapper,
                            )

                            value = MetadataFieldMapper.get_metadata_value(entry.data, column_key)
                            return value
                    except Exception:
                        logger.debug(
                            "Error accessing metadata cache for %s",
                            column_key,
                            exc_info=True,
                            extra={"dev_only": True},
                        )

                # Fallback: try to get from file item metadata directly
                if hasattr(file, "metadata") and file.metadata:
                    try:
                        # Use centralized metadata field mapper for fallback too
                        from oncutf.core.metadata.field_mapper import MetadataFieldMapper

                        value = MetadataFieldMapper.get_metadata_value(file.metadata, column_key)
                        if value:
                            return value
                    except Exception:
                        logger.debug(
                            "Error accessing file metadata for %s",
                            column_key,
                            exc_info=True,
                            extra={"dev_only": True},
                        )

                return ""  # Empty string for missing metadata

        elif role == Qt.DecorationRole:
            # Show color swatch for color column
            if column_key == "color":
                color_value = getattr(file, "color", "none")
                if color_value and color_value != "none":
                    return self._create_color_icon(color_value)
                return QVariant()
            return QVariant()

        elif role == Qt.TextAlignmentRole:
            # Get alignment from UnifiedColumnService
            from oncutf.core.ui_managers import get_column_service

            service = get_column_service()
            config = service.get_column_config(column_key)
            if config:
                return config.qt_alignment
            # Default fallback
            return Qt.AlignLeft | Qt.AlignVCenter

        return QVariant()

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self.files):
            return QVariant()
        if index.column() == 0:
            # Status column logic...
            file = self.files[index.row()]
            if role == Qt.DisplayRole:
                return QVariant()
            if role == Qt.DecorationRole:
                # Determine metadata status
                metadata_status = "none"

                # Check staging manager for modified status
                is_modified = False
                try:
                    from oncutf.core.metadata import get_metadata_staging_manager

                    staging_manager = get_metadata_staging_manager()
                    if staging_manager and staging_manager.has_staged_changes(file.full_path):
                        is_modified = True
                except Exception:
                    pass

                if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
                    entry = self.parent_window.metadata_cache.get_entry(file.full_path)
                    if entry and hasattr(entry, "data") and entry.data:
                        # Check modified status first
                        if is_modified or (hasattr(entry, "modified") and entry.modified):
                            metadata_status = "modified"
                        elif hasattr(entry, "is_extended") and entry.is_extended:
                            metadata_status = "extended"
                        else:
                            metadata_status = "loaded"

                # Determine hash status
                hash_status = "hash" if self._has_hash_cached(file.full_path) else "none"

                # Create and return combined icon (return directly, not wrapped in QVariant)
                icon = self._create_combined_icon(metadata_status, hash_status)
                return icon
            if role == Qt.CheckStateRole:
                return Qt.Checked if file.checked else Qt.Unchecked
            if role == Qt.ToolTipRole:
                return self._get_unified_tooltip(file)
            return None
        col_key = self._column_mapping.get(index.column())
        if not col_key:
            return None
        file = self.files[index.row()]
        if role == Qt.ToolTipRole:
            # Return unified tooltip for all columns
            return self._get_unified_tooltip(file)
        result = self._get_column_data(file, col_key, role)
        return result

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if not index.isValid() or not self.files:
            return False

        row = index.row()
        col = index.column()
        file = self.files[row]

        # Handle checkbox in status column (column 0)
        if role == Qt.CheckStateRole and col == 0:
            new_checked = value == Qt.Checked
            if file.checked == new_checked:
                return False  # Don't do anything if it didn't change
            file.checked = new_checked

            self.dataChanged.emit(index, index, [Qt.CheckStateRole])

            # Try to update UI through ApplicationContext, fallback to parent_window
            try:
                get_app_context()
                # For now, we still need to access parent window for UI updates
                # This will be improved when we migrate UI update handling to context
                import sys

                if hasattr(sys, "_getframe"):
                    # Try to get parent window from current widget hierarchy
                    # This is a transitional approach
                    pass

                # Use legacy approach for now until we fully migrate UI updates
                if self.parent_window:
                    self.parent_window.header.update_state(self.files)
                    self.parent_window.update_files_label()
                    self.parent_window.request_preview_update()
            except RuntimeError:
                # ApplicationContext not ready yet, use legacy approach
                if self.parent_window:
                    self.parent_window.header.update_state(self.files)
                    self.parent_window.update_files_label()
                    self.parent_window.request_preview_update()

            return True

        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid() or not self.files:
            return Qt.ItemFlags(Qt.NoItemFlags)

        base_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable

        # Enable checkbox only in status column (column 0)
        if index.column() == 0:
            base_flags |= Qt.ItemIsUserCheckable

        return base_flags

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return ""  # Don't display title in status column

            col_key = self._column_mapping.get(section)
            if col_key:
                # Get the proper title from configuration
                from oncutf.config import FILE_TABLE_COLUMN_CONFIG

                title = FILE_TABLE_COLUMN_CONFIG.get(col_key, {}).get("title", col_key)
                logger.debug(
                    "[HeaderData] Section %d -> column '%s' -> title '%s'",
                    section,
                    col_key,
                    title,
                    extra={"dev_only": True},
                )
                return title
            else:
                logger.warning(
                    "[HeaderData] No column mapping found for section %d",
                    section,
                )
                logger.debug(
                    "[HeaderData] Available mappings: %s",
                    self._column_mapping,
                    extra={"dev_only": True},
                )
                return ""
        return super().headerData(section, orientation, role)

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:
        if not self.files:
            return

        # Get column key from mapping
        column_key = self._column_mapping.get(column)
        if not column_key:
            return

        # Try to get selection model from ApplicationContext, fallback to parent_window
        selection_model = None
        try:
            get_app_context()
            # For now, we still need to access parent window for selection model
            # This will be improved when we migrate selection handling to context
            if self.parent_window:
                selection_model = self.parent_window.file_table_view.selectionModel()
        except RuntimeError:
            # ApplicationContext not ready yet, use legacy approach
            if self.parent_window:
                selection_model = self.parent_window.file_table_view.selectionModel()

        if not selection_model:
            return

        selected_items = [self.files[i.row()] for i in selection_model.selectedRows()]

        reverse = order == Qt.DescendingOrder

        # Sort based on column key
        if column_key == "filename":
            self.files.sort(key=lambda f: f.filename.lower(), reverse=reverse)
        elif column_key == "file_size":
            self.files.sort(key=lambda f: f.size if hasattr(f, "size") else 0, reverse=reverse)
        elif column_key == "type":
            self.files.sort(key=lambda f: f.extension.lower(), reverse=reverse)
        elif column_key == "modified":
            self.files.sort(key=lambda f: f.modified, reverse=reverse)
        elif column_key == "file_hash":
            self.files.sort(key=lambda f: self._get_hash_value(f.full_path), reverse=reverse)
        elif column_key == "color":
            # Sort by color: "none" first, then alphabetically by hex value
            self.files.sort(key=lambda f: (f.color != "none", f.color.lower()), reverse=reverse)
        else:
            # For metadata columns, sort by the metadata value
            def get_metadata_sort_key(file):
                if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
                    entry = self.parent_window.metadata_cache.get_entry(file.full_path)
                    if entry and hasattr(entry, "data") and entry.data:
                        # Map column keys to metadata keys (using actual EXIF/QuickTime keys)
                        # Use centralized metadata field mapper for sorting
                        from oncutf.core.metadata.field_mapper import MetadataFieldMapper

                        # Get possible metadata keys for this column
                        possible_keys = MetadataFieldMapper.get_metadata_keys_for_field(column_key)

                        # Find the first available key in the metadata
                        found_value = None
                        for key in possible_keys:
                            if key in entry.data:
                                found_value = entry.data[key]
                                break

                        if found_value is not None:
                            # Special handling for image size (sort by width)
                            if column_key == "image_size":
                                try:
                                    # Extract width from "widthxheight" format
                                    if "x" in str(found_value):
                                        width = str(found_value).split("x")[0]
                                        return int(width)
                                    else:
                                        return int(found_value)
                                except (ValueError, TypeError):
                                    return 0
                            # For numeric values, try to convert to int/float for proper sorting
                            elif column_key in [
                                "iso",
                                "video_fps",
                                "video_avg_bitrate",
                                "rotation",
                            ]:
                                try:
                                    # Extract numeric part from strings like "100" or "100.0"
                                    numeric_str = str(found_value).split()[0]  # Take first word
                                    if "." in numeric_str:
                                        return float(numeric_str)
                                    else:
                                        return int(numeric_str)
                                except (ValueError, TypeError):
                                    return 0
                            else:
                                return str(found_value).lower()  # String sorting (case-insensitive)

                # Return appropriate default value based on column type
                if column_key in [
                    "iso",
                    "video_fps",
                    "video_avg_bitrate",
                    "rotation",
                    "image_size",
                ]:
                    return 0  # Default numeric value for numeric columns
                else:
                    return ""  # Default string value for text columns

            self.files.sort(key=get_metadata_sort_key, reverse=reverse)

        self.layoutChanged.emit()
        self.sort_changed.emit()

        # Store current sort state in parent window for post-rename consistency
        if self.parent_window:
            self.parent_window.current_sort_column = column
            self.parent_window.current_sort_order = order
            logger.debug(
                "[Model] Stored sort state: column=%d, order=%s",
                column,
                order,
                extra={"dev_only": True},
            )

        selection_model.clearSelection()
        selection = QItemSelection()

        for row, file in enumerate(self.files):
            if file in selected_items:
                top_left = self.index(row, 0)
                bottom_right = self.index(row, self.columnCount() - 1)
                selection_range = QItemSelectionRange(top_left, bottom_right)
                selection.append(selection_range)
                logger.debug(
                    "[Model] dataChanged.emit() for row %d",
                    row,
                    extra={"dev_only": True},
                )

        selection_model.select(selection, QItemSelectionModel.Select)

        # Try to refresh metadata tree through ApplicationContext, fallback to parent_window
        try:
            get_app_context()
            # For now, we still need to access parent window for metadata tree
            # This will be improved when we migrate metadata tree handling to context
            if self.parent_window:
                self.parent_window.metadata_tree_view.refresh_metadata_from_selection()
        except RuntimeError:
            # ApplicationContext not ready yet, use legacy approach
            if self.parent_window:
                self.parent_window.metadata_tree_view.refresh_metadata_from_selection()

    def clear(self):
        self.beginResetModel()
        self.files = []
        self.endResetModel()

    def set_files(self, files: list[FileItem]) -> None:
        """Set the files to be displayed in the table."""
        logger.debug(
            "set_files called with %d files",
            len(files),
            extra={"dev_only": True},
        )
        self.beginResetModel()
        self.files = files
        # self._update_column_mapping()  # Removed because it's not needed and causes error

        # Clear tooltip cache when new files are loaded
        self._tooltip_cache.clear()

        self._update_icons_immediately()
        self.endResetModel()
        logger.debug(
            "set_files finished, now self.files has %d files",
            len(self.files),
            extra={"dev_only": True},
        )
        # Update custom tooltips for new files
        if hasattr(self, "_table_view_ref") and self._table_view_ref:
            self.setup_custom_tooltips(self._table_view_ref)
            # Ensure columns are reconfigured after model reset
            if hasattr(self._table_view_ref, "refresh_columns_after_model_change"):
                logger.debug(
                    "Calling refresh_columns_after_model_change, files in model: %d",
                    len(self.files),
                )
                self._table_view_ref.refresh_columns_after_model_change()

    def _update_icons_immediately(self) -> None:
        """Updates icons immediately for all files that have cached data."""
        if not self.files:
            return

        # Simple icon refresh like the old system
        top_left = self.index(0, 0)
        bottom_right = self.index(len(self.files) - 1, 0)
        self.dataChanged.emit(top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole])
        logger.debug(
            "[FileTableModel] Updated icons immediately for %d files",
            len(self.files),
            extra={"dev_only": True},
        )

    def _delayed_icon_update(self) -> None:
        """Delayed icon update to ensure all cached data is available."""
        # This method is no longer needed - removed for performance improvement
        # The _update_icons_immediately() does all the work

    def add_files(self, new_files: list[FileItem]) -> None:
        """Adds new files to the existing file list and updates the model.

        Args:
            new_files (list[FileItem]): List of new FileItem objects to add

        """
        if not new_files:
            return

        # Start row insertion
        start_row = len(self.files)
        self.beginInsertRows(QModelIndex(), start_row, start_row + len(new_files) - 1)

        # Add the new files to our list
        self.files.extend(new_files)

        # End row insertion
        self.endInsertRows()

        # Emit signal to update any views
        self.layoutChanged.emit()

        # Optionally notify parent window
        try:
            get_app_context()
            # For now, we still need to access parent window for UI updates
            # This will be improved when we migrate UI update handling to context
            if self.parent_window:
                self.parent_window.update_files_label()
        except RuntimeError:
            # ApplicationContext not ready yet, use legacy approach
            if self.parent_window:
                self.parent_window.update_files_label()

    def refresh_icons(self):
        """Refresh all icons in column 0.
        Call this after hash operations to update hash icon display.
        """
        if not self.files:
            return

        # Clear tooltip cache to force regeneration with new metadata/hash status
        self._tooltip_cache.clear()

        # Emit dataChanged for the entire first column to refresh icons and tooltips
        top_left = self.index(0, 0)
        bottom_right = self.index(len(self.files) - 1, 0)
        self.dataChanged.emit(top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole])
        logger.debug(
            "[FileTableModel] Refreshed icons for %d files",
            len(self.files),
            extra={"dev_only": True},
        )

    def refresh_icon_for_file(self, file_path: str):
        """Refresh icon for a specific file by path.
        More efficient than refreshing all icons.
        """
        if not self.files:
            return

        # Invalidate tooltip cache for this specific file
        self._tooltip_cache.pop(file_path, None)

        # Find the file in our list
        for i, file_item in enumerate(self.files):
            if file_item.full_path == file_path:
                index = self.index(i, 0)
                self.dataChanged.emit(index, index, [Qt.DecorationRole, Qt.ToolTipRole])
                logger.debug(
                    "[FileTableModel] Refreshed icon for %s",
                    file_item.filename,
                    extra={"dev_only": True},
                )
                return

        logger.debug(
            "[FileTableModel] File not found for icon refresh: %s",
            file_path,
            extra={"dev_only": True},
        )

    def get_checked_files(self) -> list[FileItem]:
        """Returns a list of all checked files.

        Returns:
            list[FileItem]: List of checked FileItem objects

        """
        return [f for f in self.files if f.checked]

    def setup_custom_tooltips(self, table_view) -> None:
        """Setup custom tooltips for all cells in the table view."""
        # This method is no longer needed - tooltips are now handled through Qt.ToolTipRole in data() method
        # Keep method for backward compatibility but make it a no-op
        if not table_view:
            return

        # Store reference to table view for future updates
        self._table_view_ref = table_view

        logger.debug(
            "Custom tooltips are now handled through Qt.ToolTipRole in data() method",
            extra={"dev_only": True},
        )

    def update_file_metadata(self, file_item: FileItem) -> None:
        """Update the row for the given file item.
        Emits dataChanged for the corresponding row.
        """
        try:
            # Find the row index for the file item
            # Note: This is O(N), consider optimizing with a dict if performance becomes an issue
            row = self.files.index(file_item)

            top_left = self.index(row, 0)
            bottom_right = self.index(row, self.columnCount() - 1)

            # Emit dataChanged for all roles that might be affected by metadata update
            self.dataChanged.emit(
                top_left, bottom_right, [Qt.DecorationRole, Qt.ToolTipRole, Qt.DisplayRole]
            )
        except ValueError:
            # File item not found in the model
            pass
