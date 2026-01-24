"""Edit operations for metadata editing.

This module provides the core edit operations including:
- Value editing with dialogs
- Date/time field editing
- Fallback edit operations

Author: Michael Economou
Date: 2026-01-01
"""

from typing import TYPE_CHECKING, Any

from oncutf.ui.behaviors.metadata_edit.field_detector import (
    get_date_type_from_field,
    is_date_time_field,
    normalize_metadata_field_name,
)
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.ui.behaviors.metadata_edit.tree_navigator import TreeNavigator

logger = get_cached_logger(__name__)


class EditOperations:
    """Handles metadata edit operations.

    Provides methods for:
    - Opening edit dialogs (text, datetime)
    - Processing edit results
    - Fallback editing without command system
    """

    def __init__(
        self,
        widget: Any,
        tree_navigator: "TreeNavigator",
        update_tree_item_callback: Any,
    ) -> None:
        """Initialize edit operations.

        Args:
            widget: The host widget
            tree_navigator: Tree navigation helper
            update_tree_item_callback: Callback to update tree item value

        """
        self._widget = widget
        self._tree_navigator = tree_navigator
        self._update_tree_item_value = update_tree_item_callback

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
            saved_path = (
                self._tree_navigator.get_item_path(current_index)
                if current_index.isValid()
                else None
            )
        else:
            saved_path = None

        # Check if this is a date/time field
        if is_date_time_field(key_path):
            self._edit_date_time_field(key_path, current_value, saved_path)
            return

        # Get selected files
        selected_files = self._widget._get_current_selection()
        if not selected_files:
            logger.warning("No files selected for editing")
            return

        # Extract clean field name from grouped path
        # (e.g., "File Info (12 fields)/Rotation" -> "Rotation")
        # Handle both Unix and Windows path separators
        key_normalized = key_path.replace("\\", "/")
        if "/" in key_normalized:
            clean_field_name = key_normalized.split("/")[-1].strip()
        else:
            clean_field_name = key_path

        # Normalize the field name for storage (e.g., "rotation" -> "Rotation")
        normalized_field_path = normalize_metadata_field_name(clean_field_name)

        # Open basic text edit dialog
        from oncutf.ui.dialogs.metadata_edit_dialog import MetadataEditDialog

        dialog = MetadataEditDialog(
            parent=self._widget,
            selected_files=selected_files,
            metadata_cache=self._widget._cache_behavior.get_metadata_cache(),
            field_name=clean_field_name,  # For dialog display
            field_value=str(current_value) if current_value else "",
        )

        if dialog.exec_():
            new_value = dialog.get_validated_value()

            # Skip if value unchanged
            if str(new_value) == str(current_value):
                logger.debug(
                    "Value unchanged for %s, skipping edit",
                    clean_field_name,
                )
                return

            # Use command system for undo/redo support
            self._execute_edit_command(
                key_path,
                normalized_field_path,
                new_value,
                current_value,
                selected_files,
            )

        # Restore selection if we saved it
        if saved_path:
            self._tree_navigator.restore_selection(saved_path)

    def _execute_edit_command(
        self,
        key_path: str,
        normalized_field_path: str,
        new_value: Any,
        current_value: Any,
        selected_files: list,
    ) -> None:
        """Execute edit command with undo/redo support.

        Args:
            key_path: Original key path (for display)
            normalized_field_path: Normalized path (for storage)
            new_value: New value to set
            current_value: Current value
            selected_files: Files to modify

        """
        try:
            from oncutf.app.services import get_metadata_command_manager, get_metadata_service

            command_manager = get_metadata_command_manager()
            metadata_service = get_metadata_service()

            # For single file selection (metadata tree context), use command system
            if len(selected_files) == 1:
                file_item = selected_files[0]

                # Create and execute command
                command = metadata_service.create_edit_command(
                    file_path=file_item.full_path,
                    field_path=normalized_field_path,
                    new_value=new_value,
                    old_value=current_value,
                    metadata_tree_view=self._widget,
                    display_path=key_path,
                )

                command_manager.execute_command(command)

                logger.info(
                    "Edited %s metadata for file %s via command system",
                    normalized_field_path,
                    file_item.filename,
                )
            else:
                # Multi-file editing: execute command for each file
                for file_item in selected_files:
                    from oncutf.core.metadata.commands import EditMetadataFieldCommand

                    command = EditMetadataFieldCommand(
                        file_path=file_item.full_path,
                        field_path=normalized_field_path,
                        new_value=new_value,
                        old_value=current_value,
                        metadata_tree_view=self._widget,
                        display_path=key_path,
                    )
                    command_manager.execute_command(command)

                logger.info(
                    "Edited %s metadata for %d files via command system",
                    normalized_field_path,
                    len(selected_files),
                )

            # Emit signal with normalized path
            if hasattr(self._widget, "value_edited"):
                self._widget.value_edited.emit(
                    normalized_field_path,
                    new_value,
                    str(current_value) if current_value else "",
                )

        except Exception as e:
            logger.warning(
                "Command system not available or failed, using fallback: %s",
                e,
            )
            # Fallback to direct method with original path
            files_to_modify = list(selected_files)
            self._fallback_edit_value(key_path, new_value, current_value, files_to_modify)

            # Emit signal with original path
            if hasattr(self._widget, "value_edited"):
                self._widget.value_edited.emit(
                    key_path,
                    new_value,
                    str(current_value) if current_value else "",
                )

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
        from oncutf.app.services import get_metadata_service

        metadata_service = get_metadata_service()

        logger.info(
            "Fallback edit: using MetadataService",
        )

        success_count = 0

        for file_item in files_to_modify:
            logger.info(
                "Staging change: %s, %s, %s",
                file_item.full_path,
                key_path,
                new_value,
            )
            metadata_service.staging_manager.stage_change(
                file_item.full_path, key_path, new_value
            )
            success_count += 1
            file_item.metadata_status = "modified"

        if success_count == 0:
            logger.warning("No files were successfully updated")
            return

        # Update the file icon status immediately
        self._widget._cache_behavior.update_file_icon_status()

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
        date_type = get_date_type_from_field(key_path)

        # Convert file items to paths
        file_paths = [f.full_path for f in selected_files]

        # Open DateTimeEditDialog
        result_files, new_datetime = DateTimeEditDialog.get_datetime_edit_choice(
            parent=self._widget,
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
                from oncutf.app.services import (
                    get_metadata_command_manager,
                    get_metadata_service,
                )

                command_manager = get_metadata_command_manager()
                metadata_service = get_metadata_service()
                metadata_cache = self._widget._cache_behavior.get_metadata_cache()

                # Filter selected files to only those in result_files
                files_to_modify = [f for f in selected_files if f.full_path in result_files]

                if not files_to_modify:
                    logger.warning("No matching files found for date editing")
                    return

                # Create and execute command
                command = metadata_service.create_edit_command(
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
            self._tree_navigator.restore_selection(saved_path)
