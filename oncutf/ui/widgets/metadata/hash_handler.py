"""Module: hash_handler.py

Author: Michael Economou
Date: 2025-12-24

Handler for hash operations - hash checking, calculation dialogs, and hash availability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from oncutf.utils.file_status_helpers import batch_hash_status
from oncutf.utils.logger_factory import get_cached_logger
from oncutf.utils.timer_manager import schedule_ui_update

if TYPE_CHECKING:
    from oncutf.ui.widgets.metadata_widget import MetadataWidget

logger = get_cached_logger(__name__)

# Standard hash options data structure (only CRC32 supported)
HASH_OPTIONS_DATA = {"Hash Types": [("CRC32", "hash_crc32")]}


class HashHandler:
    """Handler for hash operations in MetadataWidget."""

    def __init__(self, widget: MetadataWidget) -> None:
        """Initialize the handler with a reference to the widget.

        Args:
            widget: The MetadataWidget instance
        """
        self._widget = widget

    def populate_hash_options(self) -> bool:
        """Populate hash options with efficient batch hash checking.

        Returns:
            True if successful, False otherwise
        """
        self._widget.options_combo.clear()

        try:
            # Get selected files
            selected_files = self._widget._get_selected_files()

            if not selected_files:
                # No files selected - disable hash option
                logger.debug("No files selected, populating disabled hash options")

                # For hash options we avoid auto-select to prevent unintended preview refreshes
                self._widget.options_combo.populate_from_metadata_groups(
                    HASH_OPTIONS_DATA, auto_select_first=False
                )

                # Disable the combo box
                self._widget.options_combo.setEnabled(False)
                # Apply disabled styling to show text in gray
                self._widget._styling_handler.apply_disabled_combo_styling()
                return False

            # Use efficient batch checking via database
            file_paths = [file_item.full_path for file_item in selected_files]

            # Get files that have hashes using batch query
            from oncutf.core.cache.persistent_hash_cache import get_persistent_hash_cache

            hash_cache = get_persistent_hash_cache()

            # Use batch method for efficiency
            files_with_hash = hash_cache.get_files_with_hash_batch(file_paths, "CRC32")
            files_needing_hash = [path for path in file_paths if path not in files_with_hash]

            logger.debug(
                "Populating hash options: %d/%d files have hash",
                len(files_with_hash),
                len(file_paths),
            )

            self._widget.options_combo.populate_from_metadata_groups(HASH_OPTIONS_DATA)

            # Always disabled combo box for hash (only CRC32 available)
            self._widget.options_combo.setEnabled(False)
            # Apply disabled styling to show text in gray
            self._widget._styling_handler.apply_disabled_combo_styling()

            if files_needing_hash:
                # Some files need hash calculation
                return True
            else:
                # All files have hashes - but combo still disabled
                return True

        except Exception as e:
            logger.error("[HashHandler] Error in populate_hash_options: %s", e)
            # On error, disable hash option
            self._widget.options_combo.populate_from_metadata_groups(HASH_OPTIONS_DATA)

            # Disable the combo box in case of error
            self._widget.options_combo.setEnabled(False)
            # Apply disabled styling to show text in gray
            self._widget._styling_handler.apply_disabled_combo_styling()
            return False

    def calculate_hashes_for_files(self, files_needing_hash):
        """Calculate hashes for the given file paths.

        Args:
            files_needing_hash: List of file paths that need hash calculation
        """
        try:
            # Convert file paths back to FileItem objects for hash calculation
            selected_files = self._widget._get_selected_files()
            file_items_needing_hash = []

            for file_path in files_needing_hash:
                for file_item in selected_files:
                    if file_item.full_path == file_path:
                        file_items_needing_hash.append(file_item)
                        break

            if not file_items_needing_hash:
                logger.warning("[HashHandler] No file items found for hash calculation")
                return

            # Get main window for hash calculation
            main_window = None
            if self._widget.parent_window and hasattr(self._widget.parent_window, "main_window"):
                main_window = self._widget.parent_window.main_window
            elif self._widget.parent_window:
                main_window = self._widget.parent_window
            else:
                context = self._widget._get_app_context()
                if context and hasattr(context, "main_window"):
                    main_window = context.main_window  # type: ignore

            if main_window and hasattr(main_window, "event_handler_manager"):
                # Use the existing hash calculation method
                main_window.event_handler_manager._handle_calculate_hashes(file_items_needing_hash)

                # Force preview update after hash calculation
                schedule_ui_update(
                    self._widget.force_preview_update, 100
                )  # Small delay to ensure hash calculation completes
                self._widget._hash_dialog_active = False  # <-- Ensure flag reset after calculation
            else:
                logger.error("[HashHandler] Could not find main window for hash calculation")
                self._widget._hash_dialog_active = False

        except Exception as e:
            logger.error("[HashHandler] Error calculating hashes: %s", e)
            self._widget._hash_dialog_active = False  # <-- Ensure flag reset on error

    def check_hash_calculation_requirements(self, selected_files) -> None:
        """Check if hash calculation dialog is needed.

        Args:
            selected_files: List of FileItem objects to check
        """
        file_paths = [file_item.full_path for file_item in selected_files]
        from oncutf.core.cache.persistent_hash_cache import get_persistent_hash_cache

        hash_cache = get_persistent_hash_cache()
        files_with_hash = hash_cache.get_files_with_hash_batch(file_paths, "CRC32")
        files_needing_hash = [path for path in file_paths if path not in files_with_hash]

        if files_needing_hash:
            logger.debug(
                "[HashHandler] %d files need hash calculation - showing dialog",
                len(files_needing_hash),
                extra={"dev_only": True},
            )
            self._widget._hash_dialog_active = True
            self.show_calculation_dialog(files_needing_hash, "hash")
        else:
            logger.debug(
                "[HashHandler] All files have hashes - no dialog needed",
                extra={"dev_only": True},
            )

    def check_files_have_hash(self, selected_files) -> bool:
        """Check if any of the selected files have hash data.

        Args:
            selected_files: List of FileItem objects to check

        Returns:
            True if any files have hash data, False otherwise
        """
        try:
            file_paths = [file_item.full_path for file_item in selected_files]
            return any(batch_hash_status(file_paths).values())
        except Exception as e:
            logger.error("[HashHandler] Error checking hash availability: %s", e)
            return False

    def _get_supported_hash_algorithms(self) -> set:
        """Get list of supported hash algorithms from the async operations manager.

        Returns:
            Set of supported hash algorithm names
        """
        # Only CRC32 is supported and implemented
        return {"CRC32"}

    def show_calculation_dialog(self, files_needing_calculation, calculation_type: str):
        """Show calculation dialog for hash or metadata.

        Args:
            files_needing_calculation: List of file paths needing calculation
            calculation_type: Type of calculation ("hash" or "metadata")
        """
        try:
            from oncutf.ui.widgets.custom_message_dialog import CustomMessageDialog

            # Create dialog message based on calculation type
            file_count = len(files_needing_calculation)

            if calculation_type == "hash":
                message = f"{file_count} out of {len(self._widget._get_selected_files())} selected files do not have hash.\n\nWould you like to calculate hash for all files now?\n\nThis will allow you to use hash values in your filename transformations."
                title = "Hash Calculation Required"
                yes_text = "Calculate Hash"
            else:  # metadata
                message = f"{file_count} out of {len(self._widget._get_selected_files())} selected files do not have metadata.\n\nWould you like to load metadata for all files now?\n\nThis will allow you to use metadata values in your filename transformations."
                title = "Metadata Loading Required"
                yes_text = "Load Metadata"

            logger.debug(
                "[HashHandler] Showing %s calculation dialog",
                calculation_type,
                extra={"dev_only": True},
            )

            # Show dialog
            result = CustomMessageDialog.question(
                self._widget.parent_window, title, message, yes_text=yes_text, no_text="Cancel"
            )

            if result:
                # User chose to calculate
                logger.debug(
                    "[HashHandler] User chose to calculate %s",
                    calculation_type,
                    extra={"dev_only": True},
                )
                if calculation_type == "hash":
                    self.calculate_hashes_for_files(files_needing_calculation)
                else:
                    # Delegate to widget for metadata loading
                    self._widget._load_metadata_for_files(files_needing_calculation)
            else:
                # User cancelled - combo remains enabled but shows original names
                logger.debug(
                    "[HashHandler] User cancelled %s calculation",
                    calculation_type,
                    extra={"dev_only": True},
                )
                # Don't disable combo - let it show original names for files without hash/metadata

        except Exception as e:
            logger.error(
                "[HashHandler] Error showing %s calculation dialog: %s",
                calculation_type,
                e,
            )
            self._widget._hash_dialog_active = False
