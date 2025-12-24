"""Category Manager for MetadataWidget.

This module handles category-related operations for the MetadataWidget,
including category availability updates, option population, and file date formats.

Author: Michael Economou
Date: December 24, 2025
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QStandardItem, QStandardItemModel

from oncutf.core.theme_manager import get_theme_manager
from oncutf.ui.widgets.metadata.hash_handler import HASH_OPTIONS_DATA
from oncutf.utils.file_status_helpers import batch_metadata_status
from oncutf.utils.logger_factory import get_cached_logger
from oncutf.utils.timer_manager import schedule_ui_update

if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_widget import MetadataWidget

logger = get_cached_logger(__name__)


class CategoryManager:
    """Handles category combo box operations and option population."""

    def __init__(self, widget: MetadataWidget) -> None:
        """Initialize the CategoryManager.

        Args:
            widget: The parent MetadataWidget instance.
        """
        self.widget = widget
        logger.debug("CategoryManager initialized")

    def on_category_changed(self) -> None:
        """Handle category combo box changes.
        Updates available options based on selected category.
        """
        current_data = self.widget.category_combo.currentData()
        logger.debug("Category changed to: %s", current_data)

        if current_data is None:
            self.widget.category_combo.setCurrentIndex(0)
            return

        try:
            # Clear and update options
            self.widget.options_combo.clear()
            self.update_options()

            # Enable combo box for metadata keys
            if current_data == "metadata_keys":
                self.widget.options_combo.setEnabled(True)
                self.widget._apply_normal_combo_styling()

            # Check calculation requirements
            if current_data in ["hash", "metadata_keys"]:
                self._check_calculation_requirements(current_data)

            # Force UI update
            self.widget.options_combo.repaint()

            logger.debug("Category change completed for: %s", current_data)

        except Exception as e:
            logger.error("Error in _on_category_changed: %s", e)

    def update_options(self) -> None:
        """Update options combo box based on selected category."""
        category = self.widget.category_combo.currentData()
        self.widget.options_combo.clear()

        logger.debug("update_options called with category: %s", category)

        if category == "file_dates":
            self.populate_file_dates()
        elif category == "hash":
            success = self.widget._hash_handler.populate_hash_options()
            if not success:
                # If hash population fails, try again with schedule
                try:
                    schedule_ui_update(self.widget._hash_handler.populate_hash_options, 10)
                except Exception:
                    # Fallback if timer manager not available
                    self.widget._hash_handler.populate_hash_options()
        elif category == "metadata_keys":
            self.widget._metadata_keys_handler.populate_metadata_keys()

        # Schedule settings change emission
        try:
            schedule_ui_update(self.widget.emit_if_changed, 10)
        except Exception:
            # Fallback for testing or when timer manager is not available
            self.widget.emit_if_changed()

    def populate_file_dates(self) -> None:
        """Populate options combo with file date formats."""
        # Prepare hierarchical data for file dates
        hierarchical_data = {
            "File Date/Time": [
                ("Last Modified (YYMMDD)", "last_modified_yymmdd"),
                ("Last Modified (YYYY-MM-DD)", "last_modified_iso"),
                ("Last Modified (DD-MM-YYYY)", "last_modified_eu"),
                ("Last Modified (MM-DD-YYYY)", "last_modified_us"),
                ("Last Modified (YYYY)", "last_modified_year"),
                ("Last Modified (YYYY-MM)", "last_modified_month"),
                # New variants with time included
                ("Last Modified (YYYY-MM-DD HH-MM)", "last_modified_iso_time"),
                ("Last Modified (DD-MM-YYYY HH-MM)", "last_modified_eu_time"),
                ("Last Modified (YYMMDD_HHMM)", "last_modified_compact"),
            ]
        }

        logger.debug("Populating file dates with data: %s", hierarchical_data)

        # Populate the hierarchical combo box
        # auto-select first date format by default (behaviour preserved)
        self.widget.options_combo.populate_from_metadata_groups(
            hierarchical_data, auto_select_first=True
        )
        logger.debug("Used hierarchical combo populate_from_metadata_groups for file dates")

    def update_category_availability(self) -> None:
        """Update category combo box availability based on selected files."""
        # Ensure theme inheritance
        self.widget._ensure_theme_inheritance()

        # Get selected files
        selected_files = self.widget._get_selected_files()

        # Set up the model if not already done
        if not hasattr(self.widget, "category_model"):
            self.widget.category_model = QStandardItemModel()
            self.widget.category_combo.setModel(self.widget.category_model)

            # Add items to model
            item1 = QStandardItem("File Date/Time")
            item1.setData("file_dates", Qt.UserRole)  # type: ignore
            self.widget.category_model.appendRow(item1)

            item2 = QStandardItem("Hash")
            item2.setData("hash", Qt.UserRole)  # type: ignore
            self.widget.category_model.appendRow(item2)

            item3 = QStandardItem("EXIF/Metadata")
            item3.setData("metadata_keys", Qt.UserRole)  # type: ignore
            self.widget.category_model.appendRow(item3)

        # File Dates category is ALWAYS enabled
        file_dates_item = self.widget.category_model.item(0)
        file_dates_item.setFlags(file_dates_item.flags() | Qt.ItemIsEnabled)  # type: ignore
        file_dates_item.setForeground(QColor())  # type: ignore # Reset to default color

        if not selected_files:
            # Disable Hash and EXIF when no files are selected
            theme = get_theme_manager()
            hash_item = self.widget.category_model.item(1)
            metadata_item = self.widget.category_model.item(2)

            hash_item.setFlags(hash_item.flags() & ~Qt.ItemIsEnabled)  # type: ignore
            hash_item.setForeground(QColor(theme.get_color("text_muted")))  # type: ignore

            metadata_item.setFlags(metadata_item.flags() & ~Qt.ItemIsEnabled)  # type: ignore
            metadata_item.setForeground(QColor(theme.get_color("text_muted")))  # type: ignore

            # Apply normal styling - disabled items will be gray via QAbstractItemView styling
            self.widget._apply_category_styling()

            # If current category is hash and is disabled, apply disabled styling
            if self.widget.category_combo.currentData() == "hash":
                self.widget.options_combo.clear()
                self.widget.options_combo.populate_from_metadata_groups(HASH_OPTIONS_DATA)
                self.widget.options_combo.setEnabled(False)
                self.widget._apply_disabled_combo_styling()

            logger.debug(
                "[MetadataWidget] No files selected - disabled Hash and EXIF options",
                extra={"dev_only": True},
            )
        else:
            # Check if files have hash data
            has_hash_data = self.widget._hash_handler._check_files_have_hash(selected_files)
            theme = get_theme_manager()
            hash_item = self.widget.category_model.item(1)

            if has_hash_data:
                hash_item.setFlags(hash_item.flags() | Qt.ItemIsEnabled)  # type: ignore
                hash_item.setForeground(QColor())  # type: ignore # Reset to default color
            else:
                hash_item.setFlags(hash_item.flags() & ~Qt.ItemIsEnabled)  # type: ignore
                hash_item.setForeground(QColor(theme.get_color("text_muted")))  # type: ignore

                # If current category is hash and is disabled, apply disabled styling
                if self.widget.category_combo.currentData() == "hash":
                    self.widget.options_combo.clear()
                    self.widget.options_combo.populate_from_metadata_groups(HASH_OPTIONS_DATA)
                    self.widget.options_combo.setEnabled(False)
                    self.widget._apply_disabled_combo_styling()

            # Check if files have EXIF/metadata data
            has_metadata_data = self._check_files_have_metadata(selected_files)
            theme = get_theme_manager()
            metadata_item = self.widget.category_model.item(2)

            if has_metadata_data:
                metadata_item.setFlags(metadata_item.flags() | Qt.ItemIsEnabled)  # type: ignore
                metadata_item.setForeground(QColor())  # type: ignore # Reset to default color
            else:
                metadata_item.setFlags(metadata_item.flags() & ~Qt.ItemIsEnabled)  # type: ignore
                metadata_item.setForeground(QColor(theme.get_color("text_muted")))  # type: ignore

            # Apply styling to category combo based on state
            self.widget._apply_category_styling()

            logger.debug(
                "[MetadataWidget] %d files selected - Hash: %s, EXIF: %s",
                len(selected_files),
                has_hash_data,
                has_metadata_data,
            )

    def _check_files_have_metadata(self, selected_files) -> bool:
        """Check if any of the selected files have metadata."""
        try:
            file_paths = [file_item.full_path for file_item in selected_files]
            return any(batch_metadata_status(file_paths).values())
        except Exception as e:
            logger.error("[MetadataWidget] Error checking metadata availability: %s", e)
            return False

    def _check_calculation_requirements(self, category: str) -> None:
        """Check if calculation dialog is needed for the selected category."""
        if self.widget._hash_dialog_active:
            logger.debug(
                "[MetadataWidget] Dialog already active, skipping check", extra={"dev_only": True}
            )
            return

        try:
            selected_files = self.widget._get_selected_files()
            if not selected_files:
                logger.debug(
                    "[MetadataWidget] No files selected, no dialog needed",
                    extra={"dev_only": True},
                )
                return

            if category == "hash":
                self.widget._hash_handler._check_hash_calculation_requirements(selected_files)
            elif category == "metadata_keys":
                self._check_metadata_calculation_requirements(selected_files)

        except Exception as e:
            logger.error("[MetadataWidget] Error checking calculation requirements: %s", e)
            self.widget._hash_dialog_active = False

    def _check_metadata_calculation_requirements(self, selected_files) -> None:
        """Check if metadata calculation dialog is needed."""
        file_paths = [file_item.full_path for file_item in selected_files]
        batch_status = batch_metadata_status(file_paths)
        files_with_metadata = [p for p, has in batch_status.items() if has]
        total_files = len(selected_files)
        if len(files_with_metadata) < total_files:
            files_needing_metadata = [
                file_item.full_path
                for file_item in selected_files
                if not batch_status.get(file_item.full_path, False)
            ]
            logger.debug(
                "[MetadataWidget] %d files need metadata - showing dialog",
                len(files_needing_metadata),
                extra={"dev_only": True},
            )
            self.widget._hash_dialog_active = True
            self.widget._hash_handler._show_calculation_dialog(
                files_needing_metadata, "metadata"
            )
        else:
            logger.debug(
                "[MetadataWidget] All files have metadata - no dialog needed",
                extra={"dev_only": True},
            )
