"""Menu builder for metadata context menus.

Handles construction and display of context menu items.

Author: Michael Economou
Date: 2026-01-05
"""
from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QAction, QMenu

from oncutf.ui.behaviors.metadata_edit.field_detector import normalize_metadata_field_name
from oncutf.utils.filesystem.file_status_helpers import get_metadata_value
from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from PyQt5.QtCore import QPoint

    from oncutf.ui.behaviors.metadata_context_menu.protocols import ContextMenuWidget

logger = get_cached_logger(__name__)


class MenuBuilder:
    """Builds and displays metadata context menus."""

    def __init__(self, widget: "ContextMenuWidget"):
        """Initialize menu builder.

        Args:
            widget: The host widget

        """
        self._widget = widget

    def show_context_menu(self, position: "QPoint") -> None:
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

        key_path = self._widget._edit_behavior.get_key_path(index)
        value = index.sibling(index.row(), 1).data()
        selected_files = self._widget._get_current_selection()
        has_multiple_selection = len(selected_files) > 1

        # Check if this field can be edited
        is_editable_field = self._widget._edit_behavior._is_editable_metadata_field(key_path)

        logger.debug(
            "[MetadataMenu] key_path=%s, is_editable=%s, has_multi_sel=%s",
            key_path,
            is_editable_field,
            has_multiple_selection,
            extra={"dev_only": True},
        )

        # Check if current file has modifications for this field
        has_modifications, current_field_value = self._get_field_state(
            key_path, selected_files
        )

        # Create menu
        menu = QMenu(self._widget)
        self._widget._current_menu = menu

        # Apply theme styling
        from oncutf.ui.theme_manager import get_theme_manager

        theme = get_theme_manager()
        menu.setStyleSheet(theme.get_context_menu_stylesheet())

        # Add menu sections
        self._add_edit_actions(
            menu, key_path, value, has_multiple_selection, is_editable_field, has_modifications
        )
        self._add_rotation_action(
            menu, key_path, has_multiple_selection, current_field_value
        )

        menu.addSeparator()
        self._add_history_menu(menu)
        menu.addSeparator()
        self._add_copy_action(menu, value)

        # Use popup() instead of exec_() to avoid blocking
        menu.popup(self._widget.mapToGlobal(position))

        # Connect cleanup to aboutToHide after showing
        menu.aboutToHide.connect(self._cleanup_menu)

    def _cleanup_menu(self) -> None:
        """Clean up the current menu reference."""
        self._widget._current_menu = None

    def _get_field_state(
        self, key_path: str, selected_files: list
    ) -> tuple[bool, str | None]:
        """Get modification state and current value for a field.

        Args:
            key_path: Metadata key path
            selected_files: Currently selected files

        Returns:
            Tuple of (has_modifications, current_field_value)

        """
        has_modifications = False
        current_field_value = None

        if self._widget._current_file_path:
            # Normalize key path for standard metadata fields
            normalized_key_path = normalize_metadata_field_name(key_path)

            # Check staging manager
            from oncutf.core.metadata.metadata_service import get_metadata_service

            metadata_service = get_metadata_service()
            staged_changes = metadata_service.staging_manager.get_staged_changes(
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
                    current_field_value = self._widget._cache_behavior._get_value_from_metadata_dict(
                        file_item.metadata, key_path
                    )

                # Default to empty string if no value found
                if current_field_value is None:
                    current_field_value = ""

        return has_modifications, current_field_value

    def _add_edit_actions(
        self,
        menu: QMenu,
        key_path: str,
        value: str,
        has_multiple_selection: bool,
        is_editable_field: bool,
        has_modifications: bool,
    ) -> None:
        """Add edit and reset actions to menu.

        Args:
            menu: Target menu
            key_path: Metadata key path
            value: Current value
            has_multiple_selection: Whether multiple files are selected
            is_editable_field: Whether field is editable
            has_modifications: Whether field has modifications

        """
        # Edit action
        edit_action = QAction("Edit Value", menu)
        edit_action.setIcon(self._get_menu_icon("edit"))
        edit_action.triggered.connect(
            lambda: self._widget._edit_behavior.edit_value(key_path, value)
        )
        edit_action.setEnabled(not has_multiple_selection and is_editable_field)

        # Add tooltip to explain why it's disabled
        if has_multiple_selection:
            edit_action.setToolTip("Edit disabled: Multiple files selected")
        elif not is_editable_field:
            edit_action.setToolTip(f"Edit disabled: Field '{key_path}' is not editable")
        else:
            edit_action.setToolTip("Edit this metadata value")

        menu.addAction(edit_action)

        # Reset action
        reset_action = QAction("Reset Value", menu)
        reset_action.setIcon(self._get_menu_icon("rotate-ccw"))
        reset_action.triggered.connect(
            lambda: self._widget._edit_behavior.reset_value(key_path)
        )
        reset_action.setEnabled(
            not has_multiple_selection and is_editable_field and has_modifications
        )
        menu.addAction(reset_action)

    def _add_rotation_action(
        self,
        menu: QMenu,
        key_path: str,
        has_multiple_selection: bool,
        current_field_value: str | None,
    ) -> None:
        """Add rotation-specific action if applicable.

        Args:
            menu: Target menu
            key_path: Metadata key path
            has_multiple_selection: Whether multiple files are selected
            current_field_value: Current field value

        """
        is_rotation_field = "rotation" in key_path.lower()
        if not is_rotation_field:
            return

        set_zero_action = QAction("Set Rotation to 0", menu)
        set_zero_action.setIcon(self._get_menu_icon("rotate-ccw"))
        set_zero_action.triggered.connect(
            lambda: self._widget._edit_behavior.set_rotation_to_zero(key_path)
        )

        # Enable only if: single selection + rotation field + current value is not "0"
        current_value_str = (
            str(current_field_value).strip() if current_field_value is not None else ""
        )
        is_zero_rotation = current_value_str in {"0", ""}

        set_zero_enabled = not has_multiple_selection and not is_zero_rotation
        set_zero_action.setEnabled(set_zero_enabled)

        # Update tooltip based on current state
        if has_multiple_selection:
            set_zero_action.setToolTip("Single file selection required")
        elif is_zero_rotation:
            set_zero_action.setToolTip("Rotation is already set to 0")
        else:
            set_zero_action.setToolTip(
                f"Set rotation to 0 (current: {current_field_value})"
            )

        menu.addAction(set_zero_action)

    def _add_history_menu(self, menu: QMenu) -> None:
        """Add history submenu with undo/redo actions.

        Args:
            menu: Target menu

        """
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
        undo_action.triggered.connect(self._widget._edit_behavior._undo_metadata_operation)

        # Redo action with operation description
        redo_text = (
            f"Redo: {redo_desc}\tCtrl+Shift+Z" if redo_desc else "Redo\tCtrl+Shift+Z"
        )
        redo_action = QAction(redo_text, history_menu)
        redo_action.setIcon(self._get_menu_icon("rotate-cw"))
        redo_action.setEnabled(can_redo)
        redo_action.triggered.connect(self._widget._edit_behavior._redo_metadata_operation)

        history_menu.addAction(undo_action)
        history_menu.addAction(redo_action)

        history_menu.addSeparator()

        # Show History action
        show_history_action = QAction("Show History\tCtrl+Y", history_menu)
        show_history_action.setIcon(self._get_menu_icon("list"))
        show_history_action.triggered.connect(self._widget._edit_behavior._show_history_dialog)
        history_menu.addAction(show_history_action)

        menu.addMenu(history_menu)

    def _add_copy_action(self, menu: QMenu, value: str) -> None:
        """Add copy to clipboard action.

        Args:
            menu: Target menu
            value: Value to copy

        """
        copy_action = QAction("Copy", menu)
        copy_action.setIcon(self._get_menu_icon("copy"))
        copy_action.triggered.connect(
            lambda: self._widget._edit_behavior.copy_value(value)
        )
        copy_action.setEnabled(bool(value))
        menu.addAction(copy_action)

    def _get_menu_icon(self, icon_name: str):
        """Get menu icon using the icon loader system.

        Args:
            icon_name: Name of the icon to load

        Returns:
            QIcon or None if icon loading fails

        """
        try:
            from oncutf.ui.helpers.icons_loader import get_menu_icon

            return get_menu_icon(icon_name)
        except ImportError:
            return None


__all__ = ["MenuBuilder"]
