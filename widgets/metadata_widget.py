"""
Module: metadata_widget.py

Author: Michael Economou
Date: 2025-05-31

Widget for metadata selection (file dates or EXIF), with optimized signal emission system.
"""

from typing import Optional, Set

from core.persistent_metadata_cache import MetadataEntry
from core.pyqt_imports import QComboBox, QHBoxLayout, QLabel, Qt, QVBoxLayout, QWidget, pyqtSignal
from utils.logger_factory import get_cached_logger
from utils.timer_manager import schedule_ui_update

# ApplicationContext integration
try:
    from core.application_context import get_app_context
except ImportError:
    get_app_context = None

logger = get_cached_logger(__name__)


class MetadataWidget(QWidget):
    """
    Widget for file metadata selection (file dates or EXIF).
    Supports category selection and dynamic fields,
    and emits update signal only when there is an actual change.
    """

    updated = pyqtSignal(object)

    def __init__(
        self, parent: Optional[QWidget] = None, parent_window: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.parent_window = parent_window  # Keep for backward compatibility
        self.setProperty("module", True)
        self._last_data: Optional[dict] = None  # For change tracking
        self._cached_metadata_keys: Optional[Set[str]] = None  # Cache for metadata keys

        self._hash_dialog_active = False  # Flag to prevent multiple dialogs

        self.setup_ui()

        # Ensure theme inheritance for child widgets
        self._ensure_theme_inheritance()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)  # Match final transformer margins
        layout.setSpacing(4)  # Set spacing to 4px

        # Row 1: Category
        category_row = QHBoxLayout()
        category_row.setContentsMargins(
            0, 0, 0, 0
        )  # Removed vertical margins to allow spacing control
        category_row.setSpacing(8)  # Match final transformer spacing between label and control
        category_label = QLabel("Category")
        category_label.setFixedWidth(70)  # Increased width by 10px
        category_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # type: ignore
        self.category_combo = QComboBox()
        self.category_combo.addItem("File Dates", userData="file_dates")
        self.category_combo.addItem("Hash", userData="hash")
        self.category_combo.addItem("EXIF/Metadata", userData="metadata_keys")
        self.category_combo.setFixedWidth(120)  # Reduced width by 10px
        self.category_combo.setFixedHeight(22)  # Match final transformer combo height
        category_row.addWidget(category_label)
        category_row.addWidget(self.category_combo)
        category_row.addStretch()
        layout.addLayout(category_row)

        # Row 2: Field
        options_row = QHBoxLayout()
        options_row.setContentsMargins(
            0, 0, 0, 0
        )  # Removed vertical margins to allow spacing control
        options_row.setSpacing(8)  # Match final transformer spacing between label and control
        options_label = QLabel("Field")
        options_label.setFixedWidth(70)  # Increased width by 10px
        options_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # type: ignore
        self.options_combo = QComboBox()
        self.options_combo.setFixedWidth(120)  # Reduced width by 10px
        self.options_combo.setFixedHeight(22)  # Match final transformer combo height
        options_row.addWidget(options_label)
        options_row.addWidget(self.options_combo)
        options_row.addStretch()
        layout.addLayout(options_row)

        # Connections
        self.category_combo.currentIndexChanged.connect(
            lambda: schedule_ui_update(self.update_options)
        )
        self.options_combo.currentIndexChanged.connect(self.emit_if_changed)

        # Schedule options update
        schedule_ui_update(self.update_options, 0)

    def update_options(self) -> None:
        """Updates fields according to the selected category."""
        category = self.category_combo.currentData()
        logger.debug(f"[MetadataWidget] Updating options for category: {category}")

        self.options_combo.clear()

        if category == "file_dates":
            self.populate_file_dates()
            self.options_combo.setEnabled(True)
        elif category == "hash":
            self.populate_hash_options()
        elif category == "metadata_keys":
            self.populate_metadata_keys()
            self.options_combo.setEnabled(True)

        # Set to first option by default (αν υπάρχει)
        if self.options_combo.count() > 0:
            self.options_combo.setCurrentIndex(0)

        self.emit_if_changed()

    def populate_file_dates(self) -> None:
        file_date_options = [
            ("Last Modified (YYMMDD)", "last_modified_yymmdd"),
            ("Last Modified (YYYY-MM-DD)", "last_modified_iso"),
            ("Last Modified (DD-MM-YYYY)", "last_modified_eu"),
            ("Last Modified (MM-DD-YYYY)", "last_modified_us"),
            ("Last Modified (YYYY)", "last_modified_year"),
            ("Last Modified (YYYY-MM)", "last_modified_month"),
        ]
        for label, val in file_date_options:
            self.options_combo.addItem(label, userData=val)

    def populate_hash_options(self) -> bool:
        """Populate hash options with efficient batch hash checking."""
        if self._hash_dialog_active:
            logger.debug("[HASH_DEBUG] Hash dialog already active, skipping.")
            return True

        self.options_combo.clear()

        try:
            # Get selected files
            selected_files = self._get_selected_files()
            logger.debug(f"[HASH_DEBUG] Found {len(selected_files)} selected files.")

            if not selected_files:
                # No files selected - disable hash option
                self.options_combo.addItem("CRC32", userData="hash_crc32")
                self.options_combo.setEnabled(False)
                return False

            # Use efficient batch checking via database
            file_paths = [file_item.full_path for file_item in selected_files]

            # Get files that have hashes using batch query
            from core.persistent_hash_cache import get_persistent_hash_cache
            hash_cache = get_persistent_hash_cache()

            # Use batch method for efficiency
            files_with_hash = hash_cache.get_files_with_hash_batch(file_paths, 'CRC32')
            files_needing_hash = [path for path in file_paths if path not in files_with_hash]

            logger.debug(f"[HASH_DEBUG] {len(files_with_hash)}/{len(file_paths)} files have hashes")

            # Always add CRC32 option (disabled if no choice)
            self.options_combo.addItem("CRC32", userData="hash_crc32")

            if files_needing_hash:
                # Some files need hash calculation - show dialog
                logger.debug(f"[HASH_DEBUG] {len(files_needing_hash)} files need hash calculation")
                self._hash_dialog_active = True
                self._show_hash_calculation_dialog(files_needing_hash)
                return True
            else:
                # All files have hashes - enable the option
                self.options_combo.setEnabled(True)
                return False

        except Exception as e:
            logger.error(f"[MetadataWidget] Error in populate_hash_options: {e}")
            # On error, disable hash option
            self.options_combo.addItem("CRC32", userData="hash_crc32")
            self.options_combo.setEnabled(False)
            return False
        finally:
            self._hash_dialog_active = False

    def _get_selected_files(self):
        """Get selected files from the main window."""
        logger.debug(f"[HASH_DEBUG] _get_selected_files called. parent_window: {self.parent_window}")

        try:
            # Try to get selected files from parent window
            if self.parent_window and hasattr(self.parent_window, 'get_selected_files_ordered'):
                logger.debug("[HASH_DEBUG] Getting files from parent_window")
                files = self.parent_window.get_selected_files_ordered()
                logger.debug(f"[HASH_DEBUG] Got {len(files)} files from parent_window")
                return files

            # Try to get from ApplicationContext
            context = self._get_app_context()
            logger.debug(f"[HASH_DEBUG] ApplicationContext: {context}")

            # Try to get from FileStore
            if context and hasattr(context, '_file_store') and context._file_store:
                logger.debug("[HASH_DEBUG] Trying to get files from FileStore")
                selected_files = context._file_store.get_selected_files()
                if selected_files:
                    logger.debug(f"[HASH_DEBUG] Got {len(selected_files)} files from FileStore")
                    return selected_files

            # Try to get from SelectionStore
            if context and hasattr(context, '_selection_store') and context._selection_store:
                logger.debug("[HASH_DEBUG] Trying to get files from SelectionStore")
                selected_files = context._selection_store.get_selected_files()
                if selected_files:
                    logger.debug(f"[HASH_DEBUG] Got {len(selected_files)} files from SelectionStore")
                    return selected_files

            logger.debug("[HASH_DEBUG] No files found in ApplicationContext stores")

        except Exception as e:
            logger.warning(f"[MetadataWidget] Error getting selected files: {e}")

        logger.debug("[HASH_DEBUG] Returning empty list - no source found")
        return []

    def _show_hash_calculation_dialog(self, files_needing_hash):
        """Show dialog to calculate hashes for files that need them."""
        logger.debug(f"[HASH_DEBUG] Showing hash dialog for {len(files_needing_hash)} files")
        try:
            from widgets.custom_message_dialog import CustomMessageDialog

            # Create dialog message
            file_count = len(files_needing_hash)
            message = f"{file_count} file(s) need hash calculation.\n\nWould you like to calculate hashes for all files now?\n\nThis will allow you to use hash values in your filename transformations."

            # Show dialog
            result = CustomMessageDialog.question(
                self.parent_window,
                "Hash Calculation Required",
                message,
                yes_text="Calculate Hashes",
                no_text="Cancel"
            )

            if result:
                # User chose to calculate hashes
                self._calculate_hashes_for_files(files_needing_hash)
            else:
                # User cancelled - just disable the hash option
                logger.debug("[HASH_DEBUG] User cancelled hash calculation")
                self.options_combo.setEnabled(False)

        except Exception as e:
            logger.error(f"[MetadataWidget] Error showing hash calculation dialog: {e}")
            # On error, disable the hash option
            self.options_combo.setEnabled(False)

    def _calculate_hashes_for_files(self, files_needing_hash):
        """Calculate hashes for the given file paths."""
        try:
            # Convert file paths back to FileItem objects for hash calculation
            selected_files = self._get_selected_files()
            file_items_needing_hash = []

            for file_path in files_needing_hash:
                for file_item in selected_files:
                    if file_item.full_path == file_path:
                        file_items_needing_hash.append(file_item)
                        break

            if not file_items_needing_hash:
                logger.warning("[MetadataWidget] No file items found for hash calculation")
                return

            # Get main window for hash calculation
            main_window = None
            if self.parent_window and hasattr(self.parent_window, 'main_window'):
                main_window = self.parent_window.main_window
            elif self.parent_window:
                main_window = self.parent_window
            else:
                context = self._get_app_context()
                if context and hasattr(context, 'main_window'):
                    main_window = context.main_window

            if main_window and hasattr(main_window, 'event_handler_manager'):
                # Use the existing hash calculation method
                main_window.event_handler_manager._handle_calculate_hashes(file_items_needing_hash)

                # Enable hash option after calculation
                self.options_combo.setEnabled(True)
                logger.debug("[MetadataWidget] Hash calculation completed")
            else:
                logger.error("[MetadataWidget] Could not find main window for hash calculation")
                self.options_combo.setEnabled(False)

        except Exception as e:
            logger.error(f"[MetadataWidget] Error calculating hashes: {e}")
            self.options_combo.setEnabled(False)

    def populate_metadata_keys(self) -> None:
        keys = self.get_available_metadata_keys()
        if not keys:
            # Check if metadata cache exists but is empty vs not loaded
            metadata_cache = self._get_metadata_cache_via_context()
            if (
                metadata_cache
                and hasattr(metadata_cache, "_memory_cache")
                and metadata_cache._memory_cache
            ):
                row = self.options_combo.count()
                self.options_combo.addItem("(No metadata found in files)", userData=None)
                self.options_combo.model().item(row).setEnabled(False)
            else:
                row = self.options_combo.count()
                self.options_combo.addItem("(No metadata loaded)", userData=None)
                self.options_combo.model().item(row).setEnabled(False)
            return

        # Add metadata keys
        for key in sorted(keys):
            display = self.format_metadata_key_name(key)
            self.options_combo.addItem(display, userData=key)

    def _get_app_context(self):
        """Get ApplicationContext with fallback to None."""
        if get_app_context is None:
            return None
        try:
            return get_app_context()
        except RuntimeError:
            # ApplicationContext not ready yet
            return None

    def _get_metadata_cache_via_context(self):
        """Get metadata cache via ApplicationContext with fallback to parent traversal."""
        # Try ApplicationContext first
        context = self._get_app_context()
        if context and hasattr(context, "_metadata_cache"):
            logger.debug("[MetadataWidget] Found metadata cache via ApplicationContext")
            return context._metadata_cache

        # Fallback to legacy parent_window approach
        if self.parent_window and hasattr(self.parent_window, "metadata_cache"):
            logger.debug("[MetadataWidget] Found metadata cache via parent_window")
            return self.parent_window.metadata_cache

        # Try to find metadata cache in main window
        if (
            self.parent_window
            and hasattr(self.parent_window, "main_window")
            and self.parent_window.main_window
        ):
            main_window = self.parent_window.main_window
            if hasattr(main_window, "metadata_cache"):
                logger.debug("[MetadataWidget] Found metadata cache via main_window")
                return main_window.metadata_cache

        # Try to find metadata cache in rename modules area
        if self.parent_window and hasattr(self.parent_window, "rename_modules_area"):
            rename_area = self.parent_window.rename_modules_area
            if hasattr(rename_area, "parent") and rename_area.parent():
                parent = rename_area.parent()
                if hasattr(parent, "metadata_cache"):
                    logger.debug("[MetadataWidget] Found metadata cache via rename area parent")
                    return parent.metadata_cache

        logger.warning("[MetadataWidget] No metadata cache found")
        return None

    def get_available_metadata_keys(self) -> Set[str]:
        # Return cached keys if available
        if self._cached_metadata_keys is not None:
            return self._cached_metadata_keys

        metadata_cache = self._get_metadata_cache_via_context()
        if not metadata_cache:
            self._cached_metadata_keys = set()
            return self._cached_metadata_keys

        all_keys = set()
        try:
            # For PersistentMetadataCache, we need to access the memory cache
            if hasattr(metadata_cache, "_memory_cache"):
                for entry in metadata_cache._memory_cache.values():
                    if isinstance(entry, MetadataEntry) and entry.data:
                        filtered = {
                            k
                            for k in entry.data
                            if not k.startswith("_") and k not in {"path", "filename"}
                        }
                        all_keys.update(filtered)
            # Fallback for other cache types
            elif hasattr(metadata_cache, "_cache"):
                for entry in metadata_cache._cache.values():
                    if isinstance(entry, MetadataEntry) and entry.data:
                        filtered = {
                            k
                            for k in entry.data
                            if not k.startswith("_") and k not in {"path", "filename"}
                        }
                        all_keys.update(filtered)
            # Additional fallback for different cache structures
            elif hasattr(metadata_cache, "get_all_entries"):
                entries = metadata_cache.get_all_entries()
                for entry in entries:
                    if hasattr(entry, "data") and entry.data:
                        filtered = {
                            k
                            for k in entry.data
                            if not k.startswith("_") and k not in {"path", "filename"}
                        }
                        all_keys.update(filtered)
            # Direct dictionary access fallback
            elif isinstance(metadata_cache, dict):
                for entry in metadata_cache.values():
                    if isinstance(entry, dict):
                        filtered = {
                            k
                            for k in entry
                            if not k.startswith("_") and k not in {"path", "filename"}
                        }
                        all_keys.update(filtered)
        except Exception as e:
            logger.warning(f"[MetadataWidget] Error accessing metadata cache: {e}")

        # Cache the result
        self._cached_metadata_keys = all_keys
        return all_keys

    def format_metadata_key_name(self, key: str) -> str:
        formatted = key.replace("_", " ").title()
        replacements = {"Exif": "EXIF", "Gps": "GPS", "Iso": "ISO", "Rgb": "RGB", "Dpi": "DPI"}
        for old, new in replacements.items():
            formatted = formatted.replace(old, new)
        return formatted

    def get_data(self) -> dict:
        """Returns the state for use in the rename system."""
        category = self.category_combo.currentData() or "file_dates"
        field = self.options_combo.currentData()

        # Set default field based on category
        if not field:
            if category == "file_dates":
                field = "last_modified_yymmdd"
            elif category == "hash":
                field = "hash_crc32"
            elif category == "metadata_keys":
                field = "last_modified_yymmdd"  # Fallback

                # For hash category, ensure we only return CRC32
        if category == "hash" and field:
            # Only CRC32 is supported, so ensure we return it
            if field != "hash_crc32":
                logger.warning(f"[MetadataWidget] Hash algorithm '{field}' not supported, using CRC32")
                field = "hash_crc32"

        # For metadata_keys category, ensure we don't return None field
        if category == "metadata_keys" and not field:
            # If user somehow selected a disabled metadata item, fallback to file dates
            category = "file_dates"
            field = "last_modified_yymmdd"

        return {
            "type": "metadata",
            "category": category,
            "field": field,
        }

    def emit_if_changed(self) -> None:
        """Emits updated signal only if the state has changed."""
        new_data = self.get_data()
        if new_data != self._last_data:
            self._last_data = new_data
            self.updated.emit(self)

    def clear_cache(self) -> None:
        """Clear the metadata keys cache to force refresh."""
        self._cached_metadata_keys = None

    def refresh_metadata_keys(self) -> None:
        """Refresh metadata keys and update the combo box if currently showing metadata."""
        logger.debug("[MetadataWidget] Refreshing metadata keys")
        self.clear_cache()
        category = self.category_combo.currentData()
        if category == "metadata_keys":
            logger.debug("[MetadataWidget] Currently showing metadata keys, updating combo box")
            self.populate_metadata_keys()
            self.emit_if_changed()
        elif category == "hash":
            logger.debug("[MetadataWidget] Currently showing hash options, updating combo box")
            self.populate_hash_options()
            self.emit_if_changed()
        else:
            logger.debug(
                f"[MetadataWidget] Not currently showing metadata keys or hash, cache cleared for next time (category: {category})"
            )

    @staticmethod
    def is_effective(data: dict) -> bool:
        """
        The metadata module is effective if it has a valid field for the selected category.
        """
        field = data.get("field")
        category = data.get("category", "file_dates")

        # For hash category, check if field is a valid hash type
        if category == "hash":
            return field and field.startswith("hash_")

        # For other categories, any field is effective
        return bool(field)

    def _get_supported_hash_algorithms(self) -> set:
        """Get list of supported hash algorithms from the async operations manager."""
        # Only CRC32 is supported and implemented
        return {"CRC32"}

    def _ensure_theme_inheritance(self) -> None:
        """
        Ensure that child widgets inherit theme styles properly.
        This is needed because child widgets sometimes don't inherit
        the global application stylesheet correctly.
        """
        try:
            # Get theme colors
            from utils.theme_engine import ThemeEngine
            theme = ThemeEngine()

            # Apply specific styles to combo boxes to ensure they inherit theme
            combo_styles = f"""
                QComboBox {{
                    background-color: {theme.get_color('combo_background')};
                    color: {theme.get_color('combo_text')};
                    border: 1px solid {theme.get_color('combo_border')};
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-family: "{theme.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                    font-size: {theme.fonts['base_size']};
                }}

                QComboBox:hover {{
                    background-color: {theme.get_color('combo_background_hover')};
                    border-color: {theme.get_color('input_border_hover')};
                }}

                QComboBox:disabled {{
                    background-color: {theme.get_color('disabled_background')};
                    color: {theme.get_color('disabled_text')};
                    border-color: {theme.get_color('input_border')};
                }}

                QComboBox::drop-down {{
                    border: none;
                    background-color: transparent;
                    width: 18px;
                    subcontrol-origin: padding;
                    subcontrol-position: center right;
                }}

                QComboBox::down-arrow {{
                    image: url(resources/icons/feather_icons/chevrons-down.svg);
                    width: 12px;
                    height: 12px;
                }}

                QComboBox::down-arrow:disabled {{
                    opacity: 0.5;
                }}
            """

            # Apply styles to combo boxes
            self.category_combo.setStyleSheet(combo_styles)
            self.options_combo.setStyleSheet(combo_styles)

            logger.debug("[MetadataWidget] Theme inheritance ensured for combo boxes")

        except Exception as e:
            logger.warning(f"[MetadataWidget] Failed to ensure theme inheritance: {e}")

    def trigger_update_options(self):
        """Public method to trigger update_options from outside (e.g. on selection change)."""
        self.update_options()

