"""Metadata context menu behavior for MetadataTreeView.

This behavior handles all context menu operations including:
- Context menu creation and display
- Column visibility management (add/remove to file view)
- Menu icon loading
- Metadata key to column mapping

Extracted from MetadataContextMenuMixin as part of composition-based refactoring.

Author: Michael Economou
Date: December 28, 2025
Updated: January 1, 2026 - Removed MetadataCacheHelper dependency
"""

from typing import Any, Protocol

from PyQt5.QtCore import QModelIndex, QPoint
from PyQt5.QtWidgets import QAction, QMenu, QWidget

from oncutf.utils.filesystem.file_status_helpers import get_metadata_value
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ContextMenuWidget(Protocol):
    """Protocol defining the interface required for metadata context menu behavior.

    This protocol specifies what methods a widget must provide to use
    MetadataContextMenuBehavior for context menu operations.
    """

    # From MetadataTreeView
    _current_menu: QMenu | None
    _current_file_path: str | None
    _is_placeholder_mode: bool

    def indexAt(self, pos: QPoint) -> QModelIndex:
        """Get the model index at the given position.

        Args:
            pos: Position in widget coordinates

        Returns:
            QModelIndex: Model index at position

        """
        ...

    def mapToGlobal(self, pos: QPoint) -> QPoint:
        """Map widget position to global screen coordinates.

        Args:
            pos: Position in widget coordinates

        Returns:
            QPoint: Global screen position

        """
        ...

    def property(self, name: str) -> Any:
        """Get widget property value.

        Args:
            name: Property name

        Returns:
            Any: Property value

        """
        ...

    def parent(self) -> QWidget | None:
        """Get parent widget.

        Returns:
            QWidget | None: Parent widget

        """
        ...

    def get_key_path(self, index: QModelIndex) -> str:
        """Get metadata key path from model index.

        Args:
            index: Model index

        Returns:
            str: Key path (e.g., "EXIF:Make")

        """
        ...

    def _get_current_selection(self) -> list[Any]:
        """Get the currently selected file items.

        Returns:
            list[Any]: List of selected FileItem objects

        """
        ...

    def _get_value_from_metadata_dict(
        self, metadata: dict[str, Any], key_path: str
    ) -> Any | None:
        """Extract a value from metadata dictionary using key path.

        Args:
            metadata: Metadata dictionary
            key_path: Key path

        Returns:
            Any | None: Value if found

        """
        ...

    def _is_editable_metadata_field(self, key_path: str) -> bool:
        """Check if a metadata field can be edited.

        Args:
            key_path: Metadata key path

        Returns:
            bool: True if field is editable

        """
        ...

    def _normalize_metadata_field_name(self, key_path: str) -> str:
        """Normalize metadata field name for consistency.

        Args:
            key_path: Metadata key path

        Returns:
            str: Normalized key path

        """
        ...

    def edit_value(self, key_path: str, current_value: str) -> None:
        """Edit a metadata value (from MetadataEditMixin).

        Args:
            key_path: Metadata key path
            current_value: Current value

        """
        ...

    def reset_value(self, key_path: str) -> None:
        """Reset a metadata value (from MetadataEditMixin).

        Args:
            key_path: Metadata key path

        """
        ...

    def set_rotation_to_zero(self, key_path: str) -> None:
        """Set rotation to 0 degrees (from MetadataEditMixin).

        Args:
            key_path: Metadata key path

        """
        ...

    def copy_value(self, value: str) -> None:
        """Copy value to clipboard (from MetadataEditMixin).

        Args:
            value: Value to copy

        """
        ...

    def _undo_metadata_operation(self) -> None:
        """Undo last metadata operation (from MetadataEditMixin)."""
        ...

    def _redo_metadata_operation(self) -> None:
        """Redo last undone metadata operation (from MetadataEditMixin)."""
        ...

    def _show_history_dialog(self) -> None:
        """Show metadata history dialog (from MetadataEditMixin)."""
        ...


class MetadataContextMenuBehavior:
    """Behavior for metadata context menu operations in tree views.

    This behavior encapsulates all logic related to context menus:
    - Creating and displaying context menus
    - Managing column visibility in file view
    - Mapping metadata keys to file table columns
    - Loading menu icons

    The behavior delegates to helper methods on the host widget for access to
    metadata values, selection state, and edit operations.
    """

    def __init__(self, widget: ContextMenuWidget) -> None:
        """Initialize the metadata context menu behavior.

        Args:
            widget: The host widget that provides menu operations

        """
        self._widget = widget

    # =====================================
    # Context Menu Display
    # =====================================

    def show_context_menu(self, position: QPoint) -> None:
        """Display context menu with available options.

        Args:
            position: Position where the context menu should appear

        """
        if self._widget._is_placeholder_mode or self._widget.property("placeholder"):
            return

        index = self._widget.indexAt(position)
        if not index.isValid():
            return

        # Close any existing menu
        if self._widget._current_menu:
            self._widget._current_menu.close()
            self._widget._current_menu = None

        key_path = self._widget.get_key_path(index)
        value = index.sibling(index.row(), 1).data()
        selected_files = self._widget._get_current_selection()
        has_multiple_selection = len(selected_files) > 1

        # Check if this field can be edited (standard metadata fields)
        is_editable_field = self._widget._is_editable_metadata_field(key_path)

        # Debug logging
        from oncutf.utils.logging.logger_factory import get_cached_logger
        logger = get_cached_logger(__name__)
        logger.debug(
            "[MetadataMenu] key_path=%s, is_editable=%s, has_multi_sel=%s",
            key_path,
            is_editable_field,
            has_multiple_selection,
            extra={"dev_only": True}
        )

        # Check if current file has modifications for this field
        has_modifications = False
        current_field_value = None
        if self._widget._current_file_path:
            # Normalize key path for standard metadata fields
            normalized_key_path = self._widget._normalize_metadata_field_name(key_path)

            # Check staging manager
            from oncutf.core.metadata import get_metadata_staging_manager

            staging_manager = get_metadata_staging_manager()
            if staging_manager:
                staged_changes = staging_manager.get_staged_changes(
                    self._widget._current_file_path
                )
                has_modifications = normalized_key_path in staged_changes

            # Get current field value
            if selected_files:
                file_item = selected_files[0]
                # Get value from cache using file_status_helpers
                current_field_value = get_metadata_value(
                    file_item.full_path, normalized_key_path
                )

                # Fallback to file item metadata if not in cache
                if (
                    current_field_value is None
                    and hasattr(file_item, "metadata")
                    and file_item.metadata
                ):
                    current_field_value = self._widget._get_value_from_metadata_dict(
                        file_item.metadata, key_path
                    )

                # Default to empty string if no value found
                if current_field_value is None:
                    current_field_value = ""

        # Create menu
        menu = QMenu(self._widget)  # type: ignore[arg-type]
        self._widget._current_menu = menu

        # Apply theme styling
        from oncutf.core.theme_manager import get_theme_manager

        theme = get_theme_manager()
        menu.setStyleSheet(theme.get_context_menu_stylesheet())

        # Edit action - enabled for editable metadata fields with single selection
        edit_action = QAction("Edit Value", menu)
        edit_action.setIcon(self._get_menu_icon("edit"))
        edit_action.triggered.connect(lambda: self._widget.edit_value(key_path, value))
        edit_action.setEnabled(not has_multiple_selection and is_editable_field)

        # Add tooltip to explain why it's disabled
        if has_multiple_selection:
            edit_action.setToolTip("Edit disabled: Multiple files selected")
        elif not is_editable_field:
            edit_action.setToolTip(f"Edit disabled: Field '{key_path}' is not editable")
        else:
            edit_action.setToolTip("Edit this metadata value")

        menu.addAction(edit_action)

        # Reset action - enabled for editable fields with modifications
        reset_action = QAction("Reset Value", menu)
        reset_action.setIcon(self._get_menu_icon("rotate-ccw"))
        reset_action.triggered.connect(lambda: self._widget.reset_value(key_path))
        reset_action.setEnabled(
            not has_multiple_selection and is_editable_field and has_modifications
        )
        menu.addAction(reset_action)

        # Special action for rotation fields - Set to 0°
        is_rotation_field = "rotation" in key_path.lower()
        if is_rotation_field:
            set_zero_action = QAction("Set Rotation to 0°", menu)
            set_zero_action.setIcon(self._get_menu_icon("rotate-ccw"))
            set_zero_action.triggered.connect(
                lambda: self._widget.set_rotation_to_zero(key_path)
            )

            # Enable only if: single selection + rotation field + current value is not "0"
            # Convert to string and strip whitespace for comparison
            current_value_str = str(current_field_value).strip() if current_field_value is not None else ""
            is_zero_rotation = current_value_str in {"0", ""}

            set_zero_enabled = not has_multiple_selection and not is_zero_rotation
            set_zero_action.setEnabled(set_zero_enabled)

            # Update tooltip based on current state
            if has_multiple_selection:
                set_zero_action.setToolTip("Single file selection required")
            elif is_zero_rotation:
                set_zero_action.setToolTip("Rotation is already set to 0°")
            else:
                set_zero_action.setToolTip(
                    f"Set rotation to 0° (current: {current_field_value}°)"
                )

            menu.addAction(set_zero_action)

        menu.addSeparator()

        # Add/Remove to File View toggle action
        is_column_visible = self._is_column_visible_in_file_view(key_path)

        if is_column_visible:
            file_view_action = QAction("Remove from File View", menu)
            file_view_action.setIcon(self._get_menu_icon("minus-circle"))
            file_view_action.setToolTip(f"Remove '{key_path}' column from file view")
            file_view_action.triggered.connect(
                lambda: self._remove_column_from_file_view(key_path)
            )
        else:
            file_view_action = QAction("Add to File View", menu)
            file_view_action.setIcon(self._get_menu_icon("plus-circle"))
            file_view_action.setToolTip(f"Add '{key_path}' column to file view")
            file_view_action.triggered.connect(lambda: self._add_column_to_file_view(key_path))

        menu.addAction(file_view_action)

        menu.addSeparator()

        # History submenu
        history_menu = QMenu("History", menu)
        history_menu.setIcon(self._get_menu_icon("clock"))

        # Check if undo/redo are available and get descriptions
        try:
            from oncutf.core.metadata import get_metadata_command_manager

            command_manager = get_metadata_command_manager()
            can_undo = command_manager.can_undo()
            can_redo = command_manager.can_redo()
            undo_desc = command_manager.get_undo_description() if can_undo else None
            redo_desc = command_manager.get_redo_description() if can_redo else None
        except Exception as e:
            logger.warning("Error checking command manager status: %s", e)
            can_undo = False
            can_redo = False
            undo_desc = None
            redo_desc = None

        # Undo action with operation description
        undo_text = f"Undo: {undo_desc}\tCtrl+Z" if undo_desc else "Undo\tCtrl+Z"
        undo_action = QAction(undo_text, history_menu)
        undo_action.setIcon(self._get_menu_icon("rotate-ccw"))
        undo_action.setEnabled(can_undo)
        undo_action.triggered.connect(self._widget._undo_metadata_operation)

        # Redo action with operation description
        redo_text = (
            f"Redo: {redo_desc}\tCtrl+Shift+Z" if redo_desc else "Redo\tCtrl+Shift+Z"
        )
        redo_action = QAction(redo_text, history_menu)
        redo_action.setIcon(self._get_menu_icon("rotate-cw"))
        redo_action.setEnabled(can_redo)
        redo_action.triggered.connect(self._widget._redo_metadata_operation)

        history_menu.addAction(undo_action)
        history_menu.addAction(redo_action)

        history_menu.addSeparator()

        # Show History action - opens metadata history dialog
        show_history_action = QAction("Show History\tCtrl+Y", history_menu)
        show_history_action.setIcon(self._get_menu_icon("list"))
        show_history_action.triggered.connect(self._widget._show_history_dialog)
        history_menu.addAction(show_history_action)

        menu.addMenu(history_menu)

        menu.addSeparator()

        # Copy action - always available if there's a value
        copy_action = QAction("Copy", menu)
        copy_action.setIcon(self._get_menu_icon("copy"))
        copy_action.triggered.connect(lambda: self._widget.copy_value(value))
        copy_action.setEnabled(bool(value))
        menu.addAction(copy_action)

        # Use popup() instead of exec_() to avoid blocking
        menu.popup(self._widget.mapToGlobal(position))

        # Connect cleanup to aboutToHide after showing
        menu.aboutToHide.connect(self.cleanup_menu)

    def cleanup_menu(self) -> None:
        """Clean up the current menu reference."""
        self._widget._current_menu = None

    def _get_menu_icon(self, icon_name: str):
        """Get menu icon using the icon loader system.

        Args:
            icon_name: Name of the icon to load

        Returns:
            QIcon or None if icon loading fails

        """
        try:
            from oncutf.utils.ui.icons_loader import get_menu_icon

            return get_menu_icon(icon_name)
        except ImportError:
            return None

    # =====================================
    # Column Visibility Management
    # =====================================

    def _is_column_visible_in_file_view(self, key_path: str) -> bool:
        """Check if a column is already visible in the file view.

        Args:
            key_path: Metadata key path

        Returns:
            bool: True if column is visible, False otherwise

        """
        try:
            # Get the file table view
            file_table_view = self._get_file_table_view()
            if not file_table_view:
                return False

            # Check if column is in visible columns configuration
            visible_columns = getattr(file_table_view, "_visible_columns", {})

            # Map metadata key to column key
            column_key = self._map_metadata_key_to_column_key(key_path)
            if not column_key:
                return False

            # Check if column is visible
            from oncutf.config import FILE_TABLE_COLUMN_CONFIG

            if column_key in FILE_TABLE_COLUMN_CONFIG:
                default_visible = FILE_TABLE_COLUMN_CONFIG[column_key]["default_visible"]
                return visible_columns.get(column_key, default_visible)

        except Exception as e:
            logger.warning("Error checking column visibility: %s", e)

        return False

    def _add_column_to_file_view(self, key_path: str) -> None:
        """Add a metadata column to the file view.

        Args:
            key_path: Metadata key path

        """
        try:
            # Get the file table view
            file_table_view = self._get_file_table_view()
            if not file_table_view:
                return

            # Map metadata key to column key
            column_key = self._map_metadata_key_to_column_key(key_path)
            if not column_key:
                return

            # Update visibility configuration
            if hasattr(file_table_view, "_visible_columns"):
                file_table_view._visible_columns[column_key] = True

                # Save configuration
                if hasattr(file_table_view, "_save_column_visibility_config"):
                    file_table_view._save_column_visibility_config()

                # Update table display
                if hasattr(file_table_view, "_update_table_columns"):
                    file_table_view._update_table_columns()

                logger.info(
                    "Added column '%s' -> '%s' to file view",
                    key_path,
                    column_key,
                )

        except Exception as e:
            logger.exception("Error adding column to file view: %s", e)

    def _remove_column_from_file_view(self, key_path: str) -> None:
        """Remove a metadata column from the file view.

        Args:
            key_path: Metadata key path

        """
        try:
            # Get the file table view
            file_table_view = self._get_file_table_view()
            if not file_table_view:
                return

            # Map metadata key to column key
            column_key = self._map_metadata_key_to_column_key(key_path)
            if not column_key:
                return

            # Update visibility configuration
            if hasattr(file_table_view, "_visible_columns"):
                file_table_view._visible_columns[column_key] = False

                # Save configuration
                if hasattr(file_table_view, "_save_column_visibility_config"):
                    file_table_view._save_column_visibility_config()

                # Update table display
                if hasattr(file_table_view, "_update_table_columns"):
                    file_table_view._update_table_columns()

                logger.info(
                    "Removed column '%s' -> '%s' from file view",
                    key_path,
                    column_key,
                )

        except Exception as e:
            logger.exception("Error removing column from file view: %s", e)

    def _get_file_table_view(self):
        """Get the file table view from the parent hierarchy.

        Returns:
            FileTableView or None if not found

        """
        try:
            # Look for file table view in parent hierarchy
            parent = self._widget.parent()
            while parent:
                if hasattr(parent, "file_table_view"):
                    return parent.file_table_view

                # Check if parent has file_table attribute
                if hasattr(parent, "file_table"):
                    return parent.file_table

                # Check for main window with file table
                if hasattr(parent, "findChild"):
                    from oncutf.ui.widgets.file_table_view import FileTableView

                    file_table = parent.findChild(FileTableView)
                    if file_table:
                        return file_table

                parent = parent.parent()

        except Exception as e:
            logger.warning("Error finding file table view: %s", e)

        return None

    # =====================================
    # Metadata Key Mapping
    # =====================================

    def _map_metadata_key_to_column_key(self, metadata_key: str) -> str | None:
        """Map a metadata key path to a file table column key.

        Args:
            metadata_key: Metadata key path (e.g., "EXIF:Make")

        Returns:
            str | None: Column key if found, None otherwise

        """
        try:
            # Create mapping from metadata keys to column keys
            metadata_to_column_mapping = {
                # Image metadata
                "EXIF:ImageWidth": "image_size",
                "EXIF:ImageHeight": "image_size",
                "EXIF:Orientation": "rotation",
                "EXIF:ISO": "iso",
                "EXIF:FNumber": "aperture",
                "EXIF:ExposureTime": "shutter_speed",
                "EXIF:WhiteBalance": "white_balance",
                "EXIF:Compression": "compression",
                "EXIF:Make": "device_manufacturer",
                "EXIF:Model": "device_model",
                "EXIF:SerialNumber": "device_serial_no",
                # Video metadata
                "QuickTime:Duration": "duration",
                "QuickTime:VideoFrameRate": "video_fps",
                "QuickTime:AvgBitrate": "video_avg_bitrate",
                "QuickTime:VideoCodec": "video_codec",
                "QuickTime:MajorBrand": "video_format",
                # Audio metadata
                "QuickTime:AudioChannels": "audio_channels",
                "QuickTime:AudioFormat": "audio_format",
                # File metadata
                "File:FileSize": "file_size",
                "File:FileType": "type",
                "File:FileModifyDate": "modified",
                "File:MD5": "file_hash",
                "File:SHA1": "file_hash",
                "File:SHA256": "file_hash",
            }

            # Direct mapping
            if metadata_key in metadata_to_column_mapping:
                return metadata_to_column_mapping[metadata_key]

            # Fuzzy matching for common patterns
            key_lower = metadata_key.lower()

            if "rotation" in key_lower or "orientation" in key_lower:
                return "rotation"
            elif "duration" in key_lower:
                return "duration"
            elif "iso" in key_lower:
                return "iso"
            elif "aperture" in key_lower or "fnumber" in key_lower:
                return "aperture"
            elif "shutter" in key_lower or "exposure" in key_lower:
                return "shutter_speed"
            elif "white" in key_lower and "balance" in key_lower:
                return "white_balance"
            elif "compression" in key_lower:
                return "compression"
            elif "make" in key_lower or "manufacturer" in key_lower:
                return "device_manufacturer"
            elif "model" in key_lower:
                return "device_model"
            elif "serial" in key_lower:
                return "device_serial_no"
            elif "framerate" in key_lower or "fps" in key_lower:
                return "video_fps"
            elif "bitrate" in key_lower:
                return "video_avg_bitrate"
            elif "codec" in key_lower:
                return "video_codec"
            elif "format" in key_lower:
                if "audio" in key_lower:
                    return "audio_format"
                elif "video" in key_lower:
                    return "video_format"
            elif "channels" in key_lower and "audio" in key_lower:
                return "audio_channels"
            elif "size" in key_lower and (
                "image" in key_lower or "width" in key_lower or "height" in key_lower
            ):
                return "image_size"
            elif "hash" in key_lower or "md5" in key_lower or "sha" in key_lower:
                return "file_hash"

        except Exception as e:
            logger.warning("Error mapping metadata key to column key: %s", e)

        return None
