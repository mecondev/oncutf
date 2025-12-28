"""Metadata editing behavior for MetadataTreeView.

This behavior handles all metadata editing operations including:
- Value editing with dialogs
- Date/time field editing
- Rotation metadata
- Reset operations
- Undo/redo support
- Modified item tracking

Extracted from MetadataEditMixin as part of composition-based refactoring.

Author: Michael Economou
Date: December 28, 2025
"""

from typing import Any, Protocol

from PyQt5.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt5.QtWidgets import QApplication

from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.shared.timer_manager import schedule_ui_update

logger = get_cached_logger(__name__)


class EditableWidget(Protocol):
    """Protocol defining the interface required for metadata edit behavior.

    This protocol specifies what methods a widget must provide to use
    MetadataEditBehavior for editing operations.
    """

    # From MetadataTreeView
    modified_items: set[str]
    _current_file_path: str | None
    _direct_loader: Any | None
    _current_display_data: dict[str, Any] | None

    # Signals
    value_edited: pyqtSignal
    value_reset: pyqtSignal
    value_copied: pyqtSignal

    def model(self) -> Any:
        """Get the tree model.

        Returns:
            QAbstractItemModel: Tree model

        """
        ...

    def setCurrentIndex(self, index: QModelIndex) -> None:
        """Set current index/selection.

        Args:
            index: Model index to select

        """
        ...

    def scrollTo(self, index: QModelIndex) -> None:
        """Scroll to make index visible.

        Args:
            index: Model index to scroll to

        """
        ...

    def viewport(self) -> Any:
        """Get the viewport widget.

        Returns:
            QWidget: Viewport widget

        """
        ...

    def _get_current_selection(self) -> list[Any]:
        """Get the currently selected file items.

        Returns:
            list[Any]: List of selected FileItem objects

        """
        ...

    def _get_cache_helper(self) -> Any | None:
        """Get the MetadataCacheHelper instance.

        Returns:
            MetadataCacheHelper | None: Cache helper if available

        """
        ...

    def _get_metadata_cache(self) -> dict[str, Any] | None:
        """Get metadata cache dictionary.

        Returns:
            dict | None: Metadata cache if available

        """
        ...

    def _get_parent_with_file_table(self) -> Any | None:
        """Find the parent window that has file_table_view attribute.

        Returns:
            QWidget | None: Parent window if found

        """
        ...

    def _update_file_icon_status(self) -> None:
        """Update the file icon in the file table to reflect modified status."""
        ...

    def _get_original_value_from_cache(self, key_path: str) -> Any | None:
        """Get the original value of a metadata field from the cache.

        Args:
            key_path: Metadata key path

        Returns:
            Any | None: Original value if found

        """
        ...

    def _get_original_metadata_value(self, key_path: str) -> Any | None:
        """Get the ORIGINAL metadata value (not staged) for comparison.

        Args:
            key_path: Metadata key path

        Returns:
            Any | None: Original metadata value if found

        """
        ...

    def _update_information_label(self, display_data: dict[str, Any]) -> None:
        """Update information label with display data.

        Args:
            display_data: Display data dictionary

        """
        ...


class MetadataEditBehavior:
    """Behavior for metadata editing operations in tree views.

    This behavior encapsulates all logic related to editing metadata:
    - Opening edit dialogs (text, datetime)
    - Handling edit commands with undo/redo
    - Marking items as modified
    - Resetting values to original
    - Tree navigation and selection restoration

    The behavior delegates to helper methods on the host widget for access to
    metadata values, selection state, and cache operations.
    """

    def __init__(self, widget: EditableWidget) -> None:
        """Initialize the metadata edit behavior.

        Args:
            widget: The host widget that provides edit operations

        """
        self._widget = widget

    # =====================================
    # Field Type Detection
    # =====================================

    def _is_date_time_field(self, key_path: str) -> bool:
        """Check if a metadata field is a date/time field.

        Args:
            key_path: Metadata key path

        Returns:
            bool: True if field is date/time related

        """
        key_lower = key_path.lower()
        date_keywords = [
            "date",
            "time",
            "datetime",
            "timestamp",
            "created",
            "modified",
            "accessed",
            "filemodifydate",
            "filecreatedate",
            "createdate",
            "modifydate",
            "datetimeoriginal",
            "datetimedigitized",
        ]
        return any(keyword in key_lower for keyword in date_keywords)

    def _get_date_type_from_field(self, key_path: str) -> str:
        """Determine date type (created/modified) from field name.

        Args:
            key_path: Metadata key path

        Returns:
            str: "created" or "modified"

        """
        key_lower = key_path.lower()

        # Check for creation date patterns
        if any(keyword in key_lower for keyword in ["create", "dateoriginal", "digitized"]):
            return "created"

        # Check for modification date patterns
        if any(keyword in key_lower for keyword in ["modify", "modified", "change", "changed"]):
            return "modified"

        # Default to modified for generic date/time fields
        return "modified"

    def _is_editable_metadata_field(self, key_path: str) -> bool:
        """Check if a metadata field can be edited directly.

        Standard metadata fields that can be edited:
        - EXIF:Orientation / Rotation
        - EXIF:DateTimeOriginal / Create Date
        - EXIF:ModifyDate / Modify Date
        - XMP:Creator / Author
        - XMP:Title / Title
        - XMP:Description / Description

        Args:
            key_path: Metadata key path

        Returns:
            bool: True if field is editable

        """
        # List of editable metadata fields (case-insensitive)
        editable_fields = {
            # Rotation/Orientation
            "rotation",
            "orientation",
            "exif:orientation",
            # Dates
            "datetimeoriginal",
            "createdate",
            "modifydate",
            "exif:datetimeoriginal",
            "exif:createdate",
            "exif:modifydate",
            "file:filemodifydate",
            # XMP fields
            "xmp:creator",
            "xmp:title",
            "xmp:description",
            "creator",
            "title",
            "description",
        }

        # Normalize key path for comparison
        key_lower = key_path.lower().strip()

        return key_lower in editable_fields

    def _normalize_metadata_field_name(self, key_path: str) -> str:
        """Normalize metadata field name for consistency.

        Maps various field name variants to their canonical form.

        Args:
            key_path: Metadata key path

        Returns:
            str: Normalized key path

        """
        # Mapping of field variants to canonical names
        field_mapping = {
            # Rotation variants
            "rotation": "Rotation",
            "orientation": "Rotation",
            "exif:orientation": "Rotation",
            "exif/orientation": "Rotation",
            # Date variants
            "datetimeoriginal": "EXIF:DateTimeOriginal",
            "exif:datetimeoriginal": "EXIF:DateTimeOriginal",
            "exif/datetimeoriginal": "EXIF:DateTimeOriginal",
            "createdate": "EXIF:CreateDate",
            "exif:createdate": "EXIF:CreateDate",
            "exif/createdate": "EXIF:CreateDate",
            "modifydate": "EXIF:ModifyDate",
            "exif:modifydate": "EXIF:ModifyDate",
            "exif/modifydate": "EXIF:ModifyDate",
            "file:filemodifydate": "File:FileModifyDate",
            "file/filemodifydate": "File:FileModifyDate",
            # XMP variants
            "creator": "XMP:Creator",
            "xmp:creator": "XMP:Creator",
            "xmp/creator": "XMP:Creator",
            "title": "XMP:Title",
            "xmp:title": "XMP:Title",
            "xmp/title": "XMP:Title",
            "description": "XMP:Description",
            "xmp:description": "XMP:Description",
            "xmp/description": "XMP:Description",
        }

        key_lower = key_path.lower().strip()

        # Check for direct mapping
        if key_lower in field_mapping:
            return field_mapping[key_lower]

        # Return original if no mapping found
        return key_path

    # =====================================
    # Tree Navigation
    # =====================================

    def _get_item_path(self, index: QModelIndex) -> list[str]:
        """Get the path from root to the given index.

        Args:
            index: QModelIndex to get path for

        Returns:
            list[str]: List of display texts from root to index

        """
        path = []
        current = index

        while current.isValid():
            text = current.data(Qt.ItemDataRole.DisplayRole)
            path.insert(0, text)
            current = current.parent()

        return path

    def _find_item_by_path(self, path: list[str]) -> QModelIndex | None:
        """Find an item in the tree by its path from root.

        Args:
            path: List of display texts from root to target item

        Returns:
            QModelIndex if found, None otherwise

        """
        if not path:
            return None

        model = self._widget.model()
        if not model:
            return None

        # Start from root
        current_index = QModelIndex()

        for text in path:
            found = False
            row_count = model.rowCount(current_index)

            for row in range(row_count):
                child_index = model.index(row, 0, current_index)
                if child_index.data(Qt.ItemDataRole.DisplayRole) == text:
                    current_index = child_index
                    found = True
                    break

            if not found:
                logger.debug("Path item not found: %s", text)
                return None

        return current_index

    def _find_path_by_key(self, key_path: str) -> list[str] | None:
        """Find the tree path (display names) for a given metadata key path.

        Args:
            key_path: Metadata key like "File:FileName" or "EXIF:Make"

        Returns:
            List of display names from root to item, e.g. ["File Info", "File Name"]
            None if not found

        """
        model = self._widget.model()
        if not model:
            return None

        # Search recursively through the tree
        def search_tree(parent_index: QModelIndex, target_key: str) -> list[str] | None:
            row_count = model.rowCount(parent_index)
            for row in range(row_count):
                index = model.index(row, 0, parent_index)

                # Check if this item's key matches
                item_data = index.data(Qt.ItemDataRole.UserRole)
                if item_data and isinstance(item_data, dict):
                    item_key = item_data.get("key", "")
                    if item_key == target_key:
                        # Found it! Build the path
                        return self._get_item_path(index)

                # Search children recursively
                child_path = search_tree(index, target_key)
                if child_path:
                    return child_path

            return None

        return search_tree(QModelIndex(), key_path)

    def _restore_selection(self, path: list[str]) -> None:
        """Restore selection to the given path.

        Args:
            path: List of display names from root to item

        """
        restored_index = self._find_item_by_path(path)
        if restored_index and restored_index.isValid():
            self._widget.setCurrentIndex(restored_index)
            self._widget.scrollTo(restored_index)
            logger.debug("Restored selection to: %s", " > ".join(path))
        else:
            logger.debug("Could not restore selection, path not found")

    # =====================================
    # Main Edit Operations
    # =====================================

    def edit_value(self, key_path: str, current_value: Any) -> None:
        """Open a dialog to edit the value of a metadata field.

        Args:
            key_path: Metadata key path (e.g., "EXIF:Make")
            current_value: Current value to pre-fill in dialog

        """
        if not key_path:
            return

        # Save current selection path for restoration after edit
        model = self._widget.model()
        if model:
            current_index = model.index(0, 0)
            saved_path = self._get_item_path(current_index) if current_index.isValid() else None
        else:
            saved_path = None

        # Check if this is a date/time field
        if self._is_date_time_field(key_path):
            self._edit_date_time_field(key_path, current_value, saved_path)
            return

        # Get selected files
        selected_files = self._widget._get_current_selection()
        if not selected_files:
            logger.warning("No files selected for editing")
            return

        # Open basic text edit dialog
        from oncutf.ui.dialogs.metadata_edit_dialog import MetadataEditDialog

        dialog = MetadataEditDialog(
            parent=self._widget,  # type: ignore[arg-type]
            title=f"Edit {key_path}",
            field_name=key_path,
            current_value=str(current_value) if current_value else "",
        )

        if dialog.exec_():
            new_value = dialog.get_value()

            # Get metadata cache for command system
            metadata_cache = self._widget._get_metadata_cache()

            # Use command system for undo/redo support
            try:
                from oncutf.core.metadata import get_metadata_command_manager
                from oncutf.core.metadata.commands import EditMetadataFieldCommand

                command_manager = get_metadata_command_manager()

                # Build list of files to modify
                files_to_modify = list(selected_files)

                # Create and execute command
                command = EditMetadataFieldCommand(
                    files=files_to_modify,
                    key_path=key_path,
                    new_value=new_value,
                    old_value=current_value,
                    metadata_cache=metadata_cache,
                )

                command_manager.execute_command(command)

                logger.info(
                    "Edited %s metadata for %d files via command system",
                    key_path,
                    len(files_to_modify),
                )

                # Emit signal
                if hasattr(self._widget, "value_edited"):
                    self._widget.value_edited.emit(
                        key_path, new_value, str(current_value) if current_value else ""
                    )

            except Exception as e:
                logger.warning(
                    "Command system not available or failed, using fallback: %s",
                    e,
                )
                # Fallback to direct method
                files_to_modify = list(selected_files)
                self._fallback_edit_value(key_path, new_value, current_value, files_to_modify)

                # Emit signal
                if hasattr(self._widget, "value_edited"):
                    self._widget.value_edited.emit(
                        key_path, new_value, str(current_value) if current_value else ""
                    )

        # Restore selection if we saved it
        if saved_path:
            self._restore_selection(saved_path)

    def _fallback_edit_value(
        self, key_path: str, new_value: str, _old_value: str, files_to_modify: list
    ) -> None:
        """Fallback method for editing metadata without command system.

        Args:
            key_path: Metadata key path
            new_value: New value to set
            _old_value: Old value (unused in fallback)
            files_to_modify: List of file items to modify

        """
        from oncutf.core.metadata import get_metadata_staging_manager

        staging_manager = get_metadata_staging_manager()

        logger.info(
            "Fallback edit: staging_manager=%s",
            staging_manager,
        )

        if not staging_manager:
            logger.error("Staging manager not available")
            return

        success_count = 0

        for file_item in files_to_modify:
            logger.info(
                "Staging change: %s, %s, %s",
                file_item.full_path,
                key_path,
                new_value,
            )
            staging_manager.stage_change(file_item.full_path, key_path, new_value)
            success_count += 1
            file_item.metadata_status = "modified"

        if success_count == 0:
            logger.warning("No files were successfully updated")
            return

        # Update the file icon status immediately
        self._widget._update_file_icon_status()

        # Update the tree display to show the new value
        self._update_tree_item_value(key_path, new_value)

        # Force viewport update to refresh visual state
        self._widget.viewport().update()

    def _edit_date_time_field(
        self, key_path: str, current_value: Any, saved_path: list[str] | None = None
    ) -> None:
        """Open DateTimeEditDialog to edit a date/time field.

        Args:
            key_path: Metadata key path
            current_value: Current value of the field
            saved_path: Saved selection path for restoration

        """
        from oncutf.ui.dialogs.datetime_edit_dialog import DateTimeEditDialog

        # Get selected files
        selected_files = self._widget._get_current_selection()
        if not selected_files:
            logger.warning("No files selected for date editing")
            return

        # Determine date type from field name
        date_type = self._get_date_type_from_field(key_path)

        # Convert file items to paths
        file_paths = [f.full_path for f in selected_files]

        # Open DateTimeEditDialog
        result_files, new_datetime = DateTimeEditDialog.get_datetime_edit_choice(
            parent=self._widget,  # type: ignore[arg-type]
            selected_files=file_paths,
            date_type=date_type,
        )

        if result_files and new_datetime:
            # Format datetime as string for metadata
            datetime_str = new_datetime.strftime("%Y:%m:%d %H:%M:%S")

            logger.info(
                "Editing %s date for %d files to %s",
                date_type,
                len(result_files),
                datetime_str,
            )

            # Use command system for undo/redo support
            try:
                from oncutf.core.metadata import get_metadata_command_manager
                from oncutf.core.metadata.commands import EditMetadataFieldCommand

                command_manager = get_metadata_command_manager()
                metadata_cache = self._widget._get_metadata_cache()

                # Filter selected files to only those in result_files
                files_to_modify = [f for f in selected_files if f.full_path in result_files]

                if not files_to_modify:
                    logger.warning("No matching files found for date editing")
                    return

                # Create and execute command
                command = EditMetadataFieldCommand(
                    files=files_to_modify,
                    key_path=key_path,
                    new_value=datetime_str,
                    old_value=current_value,
                    metadata_cache=metadata_cache,
                )

                command_manager.execute_command(command)

                logger.info(
                    "Edited %s date for %d files via command system",
                    date_type,
                    len(files_to_modify),
                )

            except Exception as e:
                logger.warning(
                    "Command system not available or failed, using fallback: %s",
                    e,
                )
                # Fallback to direct method
                files_to_modify = [f for f in selected_files if f.full_path in result_files]
                self._fallback_edit_value(key_path, datetime_str, current_value, files_to_modify)

        # Restore selection if we saved it
        if saved_path:
            self._restore_selection(saved_path)

    def set_rotation_to_zero(self, key_path: str) -> None:
        """Set rotation metadata to 0 degrees.

        Args:
            key_path: Metadata key path for rotation field

        """
        if not key_path:
            return

        # Get current file
        selected_files = self._widget._get_current_selection()
        file_item = selected_files[0] if selected_files else None
        if not file_item:
            logger.warning("No file selected for rotation reset")
            return

        # Get current value
        current_value = None
        cache_helper = self._widget._get_cache_helper()
        if cache_helper:
            current_value = cache_helper.get_metadata_value(file_item, key_path)

        # Early return if already at 0 or 1 (no rotation)
        if current_value in ("0", "1"):
            logger.debug(
                "Rotation already at 0 for %s, skipping",
                file_item.filename,
            )
            return

        # Use unified metadata manager if available
        if self._widget._direct_loader:
            try:
                # Set rotation to 0
                self._widget._direct_loader.set_metadata_value(file_item.full_path, key_path, "0")

                # Update tree display
                self._update_tree_item_value(key_path, "0")

                # Mark as modified
                self.mark_as_modified(key_path)

                logger.debug(
                    "Set rotation to 0 deg for %s via UnifiedMetadataManager",
                    file_item.filename,
                )

                # Emit signal
                if hasattr(self._widget, "value_edited"):
                    self._widget.value_edited.emit(
                        key_path, "0", str(current_value) if current_value else ""
                    )

                return
            except Exception as e:
                logger.exception(
                    "Failed to set rotation via UnifiedMetadataManager: %s",
                    e,
                )

        # Fallback to manual method
        self._fallback_set_rotation_to_zero(key_path, "0", current_value if current_value else "")

    def _fallback_set_rotation_to_zero(
        self, key_path: str, new_value: str, _current_value: Any
    ) -> None:
        """Fallback method for setting rotation to zero without command system.

        Args:
            key_path: Metadata key path
            new_value: New rotation value (should be "0")
            _current_value: Current value (unused in fallback)

        """
        from oncutf.core.metadata import get_metadata_staging_manager

        staging_manager = get_metadata_staging_manager()

        if not staging_manager:
            return

        # Update metadata in staging
        selected_files = self._widget._get_current_selection()
        for file_item in selected_files:
            staging_manager.stage_change(file_item.full_path, key_path, new_value)
            file_item.metadata_status = "modified"

        # Update the file icon status immediately
        self._widget._update_file_icon_status()

        # Update the tree display to show the new value
        self._update_tree_item_value(key_path, new_value)

        # Force viewport update to refresh visual state
        self._widget.viewport().update()

    def reset_value(self, key_path: str) -> None:
        """Reset a metadata value to its original value.

        Args:
            key_path: Metadata key path to reset

        """
        if not key_path:
            return

        # Get current file
        selected_files = self._widget._get_current_selection()
        file_item = selected_files[0] if selected_files else None
        if not file_item:
            logger.warning("No file selected for reset")
            return

        # Get original value
        original_value = self._widget._get_original_value_from_cache(key_path)
        if original_value is None:
            logger.warning("No original value found for %s", key_path)
            return

        # Use unified metadata manager if available
        if self._widget._direct_loader:
            try:
                # Reset to original value
                self._widget._direct_loader.set_metadata_value(
                    file_item.full_path, key_path, str(original_value)
                )

                # Update tree display
                self._update_tree_item_value(key_path, str(original_value))

                # Remove from staging
                from oncutf.core.metadata import get_metadata_staging_manager

                staging_manager = get_metadata_staging_manager()
                if (
                    staging_manager
                    and self._widget._current_file_path
                ):
                    staging_manager.clear_staged_change(self._widget._current_file_path, key_path)

                # Remove from modified items if it's there
                if key_path in self._widget.modified_items:
                    self._widget.modified_items.remove(key_path)

                # Update file icon status
                self._widget._update_file_icon_status()

                # Emit signal
                if hasattr(self._widget, "value_reset"):
                    self._widget.value_reset.emit(key_path)

                logger.debug(
                    "Reset %s to original value via UnifiedMetadataManager",
                    key_path,
                )

                return
            except Exception as e:
                logger.exception(
                    "Failed to reset value via UnifiedMetadataManager: %s",
                    e,
                )

        # Fallback to manual method
        self._fallback_reset_value(key_path, original_value)

    def _fallback_reset_value(self, key_path: str, original_value: Any) -> None:
        """Fallback method for resetting metadata without unified manager.

        Args:
            key_path: Metadata key path
            original_value: Original value to restore

        """
        from oncutf.core.metadata import get_metadata_staging_manager

        staging_manager = get_metadata_staging_manager()

        if not staging_manager:
            return

        # Clear staged change
        if self._widget._current_file_path:
            staging_manager.clear_staged_change(self._widget._current_file_path, key_path)

        # Remove from modified items
        if key_path in self._widget.modified_items:
            self._widget.modified_items.remove(key_path)

        # Update the file icon status
        self._widget._update_file_icon_status()

        # Update the tree display
        self._update_tree_item_value(key_path, str(original_value))

        # Force viewport update
        self._widget.viewport().update()

        # Emit signal
        if hasattr(self._widget, "value_reset"):
            self._widget.value_reset.emit(key_path)

    def _update_tree_item_value(self, key_path: str, new_value: str) -> None:
        """Update the tree item value display by delegating to widget.

        Args:
            key_path: Metadata key path
            new_value: New value to display

        """
        # Always delegate to widget method if available (allows mocking in tests)
        if hasattr(self._widget, "_update_tree_item_value"):
            # Call the widget's method directly to allow test mocking
            widget_method = self._widget._update_tree_item_value
            # Only call if it's not the behavior's own method (avoid recursion)
            if callable(widget_method) and widget_method != self._update_tree_item_value:
                widget_method(key_path, new_value)

    # =====================================
    # Modified Item Tracking
    # =====================================

    def mark_as_modified(self, key_path: str) -> None:
        """Mark a field as modified.

        Args:
            key_path: Metadata key path

        """
        if not key_path:
            return

        self._widget.modified_items.add(key_path)

        # Schedule UI update
        schedule_ui_update(self._widget._update_file_icon_status, delay=0)

        # Update information label if available
        if (
            hasattr(self._widget, "_current_display_data")
            and self._widget._current_display_data
        ):
            self._widget._update_information_label(self._widget._current_display_data)

        # Update the view
        self._widget.viewport().update()

    def smart_mark_modified(self, key_path: str, new_value: Any) -> None:
        """Mark a field as modified only if it differs from the original value.

        Args:
            key_path: Metadata key path
            new_value: New value to compare with original

        """
        # Get original value from ORIGINAL metadata cache, not staging
        original_value = self._widget._get_original_metadata_value(key_path)

        # Convert values to strings for comparison
        new_str = str(new_value) if new_value is not None else ""
        original_str = str(original_value) if original_value is not None else ""

        if new_str != original_str:
            self.mark_as_modified(key_path)
            logger.debug(
                "Marked as modified: %s ('%s' -> '%s')",
                key_path,
                original_str,
                new_str,
            )
        # Remove from modifications if values are the same
        elif key_path in self._widget.modified_items:
            self._widget.modified_items.remove(key_path)
            logger.debug(
                "Removed modification mark: %s (value restored to original)",
                key_path,
            )

    # =====================================
    # Undo/Redo Operations
    # =====================================

    def _undo_metadata_operation(self) -> None:
        """Undo the last metadata operation from context menu."""
        try:
            from oncutf.core.metadata import get_metadata_command_manager

            command_manager = get_metadata_command_manager()

            if command_manager.undo():
                logger.info("Undo operation successful")

                # Get parent window for status message
                parent_window = self._widget._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "status_manager"):
                    parent_window.status_manager.set_file_operation_status(
                        "Operation undone", success=True, auto_reset=True
                    )
            else:
                logger.info("No operations to undo")

                # Show status message
                parent_window = self._widget._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "status_manager"):
                    parent_window.status_manager.set_file_operation_status(
                        "No operations to undo", success=False, auto_reset=True
                    )

        except Exception as e:
            logger.exception("Error during undo operation: %s", e)

    def _redo_metadata_operation(self) -> None:
        """Redo the last undone metadata operation from context menu."""
        try:
            from oncutf.core.metadata import get_metadata_command_manager

            command_manager = get_metadata_command_manager()

            if command_manager.redo():
                logger.info("Redo operation successful")

                # Get parent window for status message
                parent_window = self._widget._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "status_manager"):
                    parent_window.status_manager.set_file_operation_status(
                        "Operation redone", success=True, auto_reset=True
                    )
            else:
                logger.info("No operations to redo")

                # Show status message
                parent_window = self._widget._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "status_manager"):
                    parent_window.status_manager.set_file_operation_status(
                        "No operations to redo", success=False, auto_reset=True
                    )

        except Exception as e:
            logger.exception("Error during redo operation: %s", e)

    def _show_history_dialog(self) -> None:
        """Show metadata history dialog."""
        try:
            from oncutf.ui.dialogs.metadata_history_dialog import MetadataHistoryDialog

            dialog = MetadataHistoryDialog(self._widget)  # type: ignore[arg-type]
            dialog.exec_()
        except ImportError:
            logger.warning("MetadataHistoryDialog not available")

    # =====================================
    # Utility Methods
    # =====================================

    def get_key_path(self, index: QModelIndex) -> str:
        """Return the full key path for the given index.

        Args:
            index: QModelIndex to get key path for

        Returns:
            str: Key path like "EXIF/DateTimeOriginal" or "XMP/Creator"

        """
        if not index.isValid():
            return ""

        # If on Value column, get the corresponding Key
        if index.column() == 1:
            index = index.sibling(index.row(), 0)

        # Get the text of the current item
        item_text = index.data()

        # Find the parent group
        parent_index = index.parent()
        if parent_index.isValid():
            parent_text = parent_index.data()
            return f"{parent_text}/{item_text}"

        return item_text

    def copy_value(self, value: Any) -> None:
        """Copy the value to clipboard and emit the value_copied signal.

        Args:
            value: Value to copy to clipboard

        """
        if not value:
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(str(value))

        if hasattr(self._widget, "value_copied"):
            self._widget.value_copied.emit(str(value))
