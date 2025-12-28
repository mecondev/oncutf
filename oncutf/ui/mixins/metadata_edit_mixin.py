"""Metadata editing mixin for MetadataTreeView.

This mixin handles all metadata editing operations including:
- Value editing with dialogs
- Date/time field editing
- Rotation metadata
- Reset operations
- Undo/redo support
- Modified item tracking

Extracted from MetadataTreeView as part of decomposition effort.
"""

from typing import Any

from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtWidgets import QApplication

from oncutf.utils.logging.logger_helper import get_logger
from oncutf.utils.shared.timer_manager import schedule_ui_update

logger = get_logger(__name__)


class MetadataEditMixin:
    """Mixin providing metadata editing operations for tree views.

    This mixin encapsulates all logic related to editing metadata:
    - Opening edit dialogs (text, datetime)
    - Handling edit commands with undo/redo
    - Marking items as modified
    - Resetting values to original
    - Tree navigation and selection restoration

    Requirements:
        - Must be mixed with a QTreeView subclass
        - Host class must provide: _get_current_selection(), _get_cache_helper(),
          _get_metadata_cache(), _get_parent_with_file_table()
        - Host class should have: _direct_loader, modified_items set,
          value_edited/value_reset signals
        - Must also mix with MetadataCacheMixin for cache operations
    """

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

        Args:
            key_path: Metadata key path

        Returns:
            bool: True if field is editable

        """
        # Standard metadata fields that can be edited
        editable_fields = {
            # Rotation field
            "rotation",
            # Basic metadata fields
            "title",
            "artist",
            "author",
            "creator",
            "copyright",
            "description",
            "keywords",
            # Common EXIF/XMP/IPTC fields
            "headline",
            "imagedescription",
            "by-line",
            "copyrightnotice",
            "caption-abstract",
            "rights",
        }

        # Check if key_path contains any editable field name
        key_lower = key_path.lower()
        if any(field in key_lower for field in editable_fields):
            return True

        # Also check if it's a date/time field
        return self._is_date_time_field(key_path)

    def _normalize_metadata_field_name(self, key_path: str) -> str:
        """Normalize metadata field names to standard form.

        Args:
            key_path: Raw metadata key path

        Returns:
            str: Normalized field name

        """
        key_lower = key_path.lower()

        # Rotation field
        if "rotation" in key_lower:
            return "Rotation"

        # Title fields
        if any(field in key_lower for field in ["title", "headline", "imagedescription"]):
            return "Title"

        # Artist/Creator fields
        if any(field in key_lower for field in ["artist", "creator", "by-line"]):
            return "Artist"

        # Author fields (same as Artist for now)
        if "author" in key_lower:
            return "Author"

        # Copyright fields
        if any(field in key_lower for field in ["copyright", "rights", "copyrightnotice"]):
            return "Copyright"

        # Description fields
        if any(field in key_lower for field in ["description", "caption-abstract"]):
            return "Description"

        # Keywords
        if "keywords" in key_lower:
            return "Keywords"

        # Return as-is if no match (fallback)
        return key_path

    # =====================================
    # Tree Navigation Methods
    # =====================================

    def _get_item_path(self, index: QModelIndex) -> list[str]:
        """Get the path from root to the given index as a list of display texts.

        Args:
            index: QModelIndex to get path for

        Returns:
            List of strings representing the path, e.g. ["File Info", "File Name"]

        """
        path = []
        current = index
        while current.isValid():
            path.insert(0, current.data(Qt.ItemDataRole.DisplayRole))
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

        model = self.model()
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
                logger.debug("[MetadataEditMixin] Path item not found: %s", text)
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
        model = self.model()
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
            self.setCurrentIndex(restored_index)
            self.scrollTo(restored_index)
            logger.debug(
                "[MetadataEditMixin] Restored selection to: %s",
                " > ".join(path),
            )
        else:
            logger.debug("[MetadataEditMixin] Could not restore selection, path not found")

    # =====================================
    # Main Edit Operations
    # =====================================

    def edit_value(self, key_path: str, current_value: Any) -> None:
        """Open a dialog to edit the value of a metadata field.

        Args:
            key_path: Metadata key path to edit
            current_value: Current value of the field

        """
        # Save current selection path before opening dialog
        current_index = self.currentIndex()
        saved_path = self._get_item_path(current_index) if current_index.isValid() else None

        # Fallback: if no current selection, try to find the item by key_path
        if not saved_path and key_path:
            saved_path = self._find_path_by_key(key_path)
            if saved_path:
                logger.debug(
                    "[MetadataEditMixin] Using fallback path from key_path: %s",
                    key_path,
                )

        # Get selected files and metadata cache
        selected_files = self._get_current_selection()
        metadata_cache = self._get_metadata_cache()

        if not selected_files:
            logger.warning("[MetadataEditMixin] No files selected for editing")
            return

        # Check if this is a date/time field - use DateTimeEditDialog
        if self._is_date_time_field(key_path):
            self._edit_date_time_field(key_path, current_value, saved_path)
            return

        # Normalize key path for standard metadata fields
        normalized_key_path = self._normalize_metadata_field_name(key_path)

        # Import dialog here to avoid circular imports
        from oncutf.ui.dialogs.metadata_edit_dialog import MetadataEditDialog

        # Use the static method from MetadataEditDialog
        accepted, new_value, files_to_modify = MetadataEditDialog.edit_metadata_field(
            parent=self,
            selected_files=selected_files,
            metadata_cache=metadata_cache,
            field_name=normalized_key_path,
            current_value=str(current_value),
        )

        if accepted and new_value != str(current_value):
            # Use command system for undo/redo support
            try:
                from oncutf.core.metadata_command_manager import get_metadata_command_manager
                from oncutf.core.metadata_commands import EditMetadataFieldCommand

                command_manager = get_metadata_command_manager()
                if command_manager:
                    # Create command for each file to modify
                    for file_item in files_to_modify:
                        command = EditMetadataFieldCommand(
                            file_path=file_item.full_path,
                            field_path=normalized_key_path,
                            new_value=new_value,
                            old_value=str(current_value),
                            metadata_tree_view=self,
                        )

                        if command_manager.execute_command(command, group_with_previous=True):
                            logger.debug(
                                "[MetadataEditMixin] Executed edit command for %s",
                                file_item.filename,
                            )
                        else:
                            logger.warning(
                                "[MetadataEditMixin] Failed to execute edit command for %s",
                                file_item.filename,
                            )
                else:
                    # Fallback if command system not available
                    logger.warning(
                        "[MetadataEditMixin] Command system not available, using fallback"
                    )
                    self._fallback_edit_value(
                        normalized_key_path, new_value, str(current_value), files_to_modify
                    )
            except ImportError:
                # Fallback if command system not available
                logger.warning("[MetadataEditMixin] Command system not available, using fallback")
                self._fallback_edit_value(
                    normalized_key_path, new_value, str(current_value), files_to_modify
                )

            # Emit signal for external listeners
            if hasattr(self, "value_edited"):
                self.value_edited.emit(normalized_key_path, str(current_value), new_value)

            # Restore selection AFTER tree has been updated
            if saved_path:
                schedule_ui_update(lambda: self._restore_selection(saved_path), delay=150)
        # For cancelled edits, restore immediately
        elif saved_path:
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
        from oncutf.core.metadata_staging_manager import get_metadata_staging_manager

        staging_manager = get_metadata_staging_manager()

        logger.info(
            "[MetadataEditMixin] Fallback edit: staging_manager=%s",
            staging_manager,
        )

        if not staging_manager:
            logger.error("Staging manager not available")
            return

        success_count = 0

        for file_item in files_to_modify:
            logger.info(
                "[MetadataEditMixin] Staging change: %s, %s, %s",
                file_item.full_path,
                key_path,
                new_value,
            )
            staging_manager.stage_change(file_item.full_path, key_path, new_value)
            success_count += 1
            file_item.metadata_status = "modified"

        if success_count == 0:
            logger.warning("[MetadataEditMixin] No files were successfully updated")
            return

        # Update the file icon status immediately
        self._update_file_icon_status()

        # Update the tree display to show the new value
        self._update_tree_item_value(key_path, new_value)

        # Force viewport update to refresh visual state
        self.viewport().update()

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
        selected_files = self._get_current_selection()
        if not selected_files:
            logger.warning("[MetadataEditMixin] No files selected for date editing")
            return

        # Determine date type from field name
        date_type = self._get_date_type_from_field(key_path)

        # Convert file items to paths
        file_paths = [f.full_path for f in selected_files]

        # Open DateTimeEditDialog
        result_files, new_datetime = DateTimeEditDialog.get_datetime_edit_choice(
            parent=self, selected_files=file_paths, date_type=date_type
        )

        if result_files and new_datetime:
            # Format datetime as string for metadata
            datetime_str = new_datetime.strftime("%Y:%m:%d %H:%M:%S")

            logger.info(
                "[MetadataEditMixin] Editing %s date for %d files to %s",
                date_type,
                len(result_files),
                datetime_str,
            )

            # Use command system for undo/redo support
            try:
                from oncutf.core.metadata_command_manager import get_metadata_command_manager
                from oncutf.core.metadata_commands import EditMetadataFieldCommand

                command_manager = get_metadata_command_manager()
                metadata_cache = self._get_metadata_cache()

                if command_manager:
                    # Create command for each selected file
                    for file_path in result_files:
                        # Find the file item
                        file_item = next(
                            (f for f in selected_files if f.full_path == file_path), None
                        )
                        if not file_item:
                            continue

                        # Get current value from metadata
                        old_value = ""
                        if metadata_cache and key_path in metadata_cache:
                            old_value = str(metadata_cache[key_path])

                        # Create and execute command
                        command = EditMetadataFieldCommand(
                            file_path=file_path,
                            field_path=key_path,
                            new_value=datetime_str,
                            old_value=old_value,
                            metadata_tree_view=self,
                        )

                        if command_manager.execute_command(command, group_with_previous=True):
                            logger.debug(
                                "[MetadataEditMixin] Executed date edit command for %s",
                                file_item.filename,
                            )
                        else:
                            logger.warning(
                                "[MetadataEditMixin] Failed to execute date edit command for %s",
                                file_item.filename,
                            )
                else:
                    logger.warning(
                        "[MetadataEditMixin] Command system not available for date editing"
                    )
            except ImportError:
                logger.warning("[MetadataEditMixin] Command system not available for date editing")

            # Emit signal for external listeners
            if hasattr(self, "value_edited"):
                self.value_edited.emit(key_path, str(current_value), datetime_str)

            # Restore selection AFTER tree has been updated
            if saved_path:
                schedule_ui_update(lambda: self._restore_selection(saved_path), delay=150)
        else:
            logger.debug("[MetadataEditMixin] Date edit cancelled")
            # For cancelled edits, restore immediately
            if saved_path:
                self._restore_selection(saved_path)

    # =====================================
    # Special Edit Operations
    # =====================================

    def set_rotation_to_zero(self, key_path: str) -> None:
        """Set rotation metadata to 0 degrees.

        Args:
            key_path: Metadata key path for rotation field

        """
        if not key_path:
            return

        # Get current file
        selected_files = self._get_current_selection()
        file_item = selected_files[0] if selected_files else None
        if not file_item:
            logger.warning("[MetadataEditMixin] No file selected for rotation reset")
            return

        # Check if already 0
        current_value = None
        metadata = self._get_metadata_cache()
        if metadata and key_path in metadata:
            current_value = metadata[key_path]
            if current_value in ["0", "0°", 0]:
                logger.debug(
                    "[MetadataEditMixin] Rotation already set to 0 deg for %s",
                    file_item.filename,
                    extra={"dev_only": True},
                )
                return

        # Use unified metadata manager if available
        if hasattr(self, "_direct_loader") and self._direct_loader:
            try:
                # Set rotation to 0
                self._direct_loader.set_metadata_value(file_item.full_path, key_path, "0")

                # Update tree display
                self._update_tree_item_value(key_path, "0")

                # Mark as modified
                self.mark_as_modified(key_path)

                logger.debug(
                    "[MetadataEditMixin] Set rotation to 0 deg for %s via UnifiedMetadataManager",
                    file_item.filename,
                    extra={"dev_only": True},
                )

                # Emit signal
                if hasattr(self, "value_edited"):
                    self.value_edited.emit(
                        key_path, "0", str(current_value) if current_value else ""
                    )

                return
            except Exception as e:
                logger.exception(
                    "[MetadataEditMixin] Failed to set rotation via UnifiedMetadataManager: %s",
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
        from oncutf.core.metadata_staging_manager import get_metadata_staging_manager

        staging_manager = get_metadata_staging_manager()

        if not staging_manager:
            return

        # Update metadata in staging
        selected_files = self._get_current_selection()
        for file_item in selected_files:
            staging_manager.stage_change(file_item.full_path, key_path, new_value)
            file_item.metadata_status = "modified"

        # Update the file icon status immediately
        self._update_file_icon_status()

        # Update the tree display to show the new value
        self._update_tree_item_value(key_path, new_value)

        # Force viewport update to refresh visual state
        self.viewport().update()

    def reset_value(self, key_path: str) -> None:
        """Reset a metadata value to its original value.

        Args:
            key_path: Metadata key path to reset

        """
        if not key_path:
            return

        # Get current file
        selected_files = self._get_current_selection()
        file_item = selected_files[0] if selected_files else None
        if not file_item:
            logger.warning("[MetadataEditMixin] No file selected for reset")
            return

        # Get original value
        original_value = self._get_original_value_from_cache(key_path)
        if original_value is None:
            logger.warning("[MetadataEditMixin] No original value found for %s", key_path)
            return

        # Use unified metadata manager if available
        if hasattr(self, "_direct_loader") and self._direct_loader:
            try:
                # Reset to original value
                self._direct_loader.set_metadata_value(
                    file_item.full_path, key_path, str(original_value)
                )

                # Update tree display
                self._update_tree_item_value(key_path, str(original_value))

                # Remove from staging
                from oncutf.core.metadata_staging_manager import get_metadata_staging_manager

                staging_manager = get_metadata_staging_manager()
                if (
                    staging_manager
                    and hasattr(self, "_current_file_path")
                    and self._current_file_path
                ):
                    staging_manager.clear_staged_change(self._current_file_path, key_path)

                logger.debug(
                    "[MetadataEditMixin] Executed reset command for %s",
                    file_item.filename,
                    extra={"dev_only": True},
                )

                # Emit signal
                if hasattr(self, "value_reset"):
                    self.value_reset.emit(key_path)

                return
            except Exception as e:
                logger.exception(
                    "[MetadataEditMixin] Failed to reset via UnifiedMetadataManager: %s",
                    e,
                )

        # Fallback to manual method
        self._fallback_reset_value(key_path, original_value)

    def _fallback_reset_value(self, key_path: str, original_value: Any) -> None:
        """Fallback method for resetting metadata without command system.

        Args:
            key_path: Metadata key path
            original_value: Original value to restore

        """
        from oncutf.core.metadata_staging_manager import get_metadata_staging_manager

        staging_manager = get_metadata_staging_manager()

        if staging_manager and hasattr(self, "_current_file_path") and self._current_file_path:
            # Remove from staging
            staging_manager.clear_staged_change(self._current_file_path, key_path)

        # Update the file icon status
        self._update_file_icon_status()

        # Update the tree display to show the original value
        if original_value is not None:
            self._update_tree_item_value(key_path, str(original_value))

        # Force viewport update to refresh visual state
        self.viewport().update()

    # =====================================
    # Tree Display Update
    # =====================================

    def _update_tree_item_value(self, _key_path: str, _new_value: str) -> None:
        """Update the display value of a tree item to reflect changes.
        Defers actual tree rebuild to UI scheduler to avoid race conditions.

        Args:
            _key_path: Metadata key path (unused, triggers full refresh)
            _new_value: New value (unused, triggers full refresh)

        """

        def _do_update():
            # Get current metadata and force refresh with modification context
            selected_files = self._get_current_selection()
            cache_helper = self._get_cache_helper()

            if selected_files and cache_helper and len(selected_files) == 1:
                file_item = selected_files[0]
                metadata = cache_helper.get_metadata_for_file(file_item)
                if isinstance(metadata, dict) and metadata:
                    display_metadata = dict(metadata)
                    display_metadata["FileName"] = file_item.filename
                    # Use modification context to force reload
                    self.display_metadata(display_metadata, context="modification")
                    return

            # Fallback to normal update if we can't get metadata
            self.update_from_parent_selection()

        # Schedule update with minimal delay
        schedule_ui_update(_do_update, delay=0)

    # =====================================
    # Modified Items Tracking
    # =====================================

    def mark_as_modified(self, key_path: str) -> None:
        """Mark an item as modified.

        Args:
            key_path: Metadata key path to mark as modified

        """
        if not hasattr(self, "modified_items"):
            self.modified_items = set()

        self.modified_items.add(key_path)

        # Defer icon update to avoid race conditions
        schedule_ui_update(self._update_file_icon_status, delay=0)

        # Update information label if available
        if hasattr(self, "_current_display_data") and self._current_display_data:
            self._update_information_label(self._current_display_data)

        # Update the view
        self.viewport().update()

    def smart_mark_modified(self, key_path: str, new_value: Any) -> None:
        """Mark a field as modified only if it differs from the original value.

        Args:
            key_path: Metadata key path
            new_value: New value to compare with original

        """
        # Get original value from ORIGINAL metadata cache, not staging
        original_value = self._get_original_metadata_value(key_path)

        # Convert values to strings for comparison
        new_str = str(new_value) if new_value is not None else ""
        original_str = str(original_value) if original_value is not None else ""

        if new_str != original_str:
            self.mark_as_modified(key_path)
            logger.debug(
                "[MetadataEditMixin] Marked as modified: %s ('%s' -> '%s')",
                key_path,
                original_str,
                new_str,
                extra={"dev_only": True},
            )
        # Remove from modifications if values are the same
        elif hasattr(self, "modified_items") and key_path in self.modified_items:
            self.modified_items.remove(key_path)
            logger.debug(
                "[MetadataEditMixin] Removed modification mark: %s (value restored to original)",
                key_path,
                extra={"dev_only": True},
            )

    # =====================================
    # Undo/Redo Operations
    # =====================================

    def _undo_metadata_operation(self) -> None:
        """Undo the last metadata operation from context menu."""
        try:
            from oncutf.core.metadata_command_manager import get_metadata_command_manager

            command_manager = get_metadata_command_manager()

            if command_manager.undo():
                logger.info("[MetadataEditMixin] Undo operation successful")

                # Get parent window for status message
                parent_window = self._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "status_manager"):
                    parent_window.status_manager.set_file_operation_status(
                        "Operation undone", success=True, auto_reset=True
                    )
            else:
                logger.info("[MetadataEditMixin] No operations to undo")

                # Show status message
                parent_window = self._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "status_manager"):
                    parent_window.status_manager.set_file_operation_status(
                        "No operations to undo", success=False, auto_reset=True
                    )

        except Exception as e:
            logger.exception("[MetadataEditMixin] Error during undo operation: %s", e)

    def _redo_metadata_operation(self) -> None:
        """Redo the last undone metadata operation from context menu."""
        try:
            from oncutf.core.metadata_command_manager import get_metadata_command_manager

            command_manager = get_metadata_command_manager()

            if command_manager.redo():
                logger.info("[MetadataEditMixin] Redo operation successful")

                # Get parent window for status message
                parent_window = self._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "status_manager"):
                    parent_window.status_manager.set_file_operation_status(
                        "Operation redone", success=True, auto_reset=True
                    )
            else:
                logger.info("[MetadataEditMixin] No operations to redo")

                # Show status message
                parent_window = self._get_parent_with_file_table()
                if parent_window and hasattr(parent_window, "status_manager"):
                    parent_window.status_manager.set_file_operation_status(
                        "No operations to redo", success=False, auto_reset=True
                    )

        except Exception as e:
            logger.exception("[MetadataEditMixin] Error during redo operation: %s", e)

    def _show_history_dialog(self) -> None:
        """Show metadata history dialog."""
        try:
            from oncutf.ui.dialogs.metadata_history_dialog import MetadataHistoryDialog

            dialog = MetadataHistoryDialog(self)
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

        if hasattr(self, "value_copied"):
            self.value_copied.emit(str(value))
