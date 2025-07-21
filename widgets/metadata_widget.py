"""
Module: metadata_widget.py

Author: Michael Economou
Date: 2025-05-31

Widget for metadata selection (file dates or EXIF), with optimized signal emission system.
"""

from typing import Optional, Set

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QStandardItem, QStandardItemModel, QBrush, QPalette
from PyQt5.QtWidgets import QComboBox, QHBoxLayout, QLabel, QStyle, QVBoxLayout, QWidget, QStyledItemDelegate

from core.persistent_metadata_cache import MetadataEntry
from core.pyqt_imports import QComboBox, QHBoxLayout, QLabel, QStyle, QVBoxLayout, QWidget
from utils.logger_factory import get_cached_logger
from utils.theme_engine import ThemeEngine
from utils.timer_manager import schedule_ui_update

# ApplicationContext integration
try:
    from core.application_context import get_app_context
except ImportError:
    get_app_context = None

logger = get_cached_logger(__name__)


class ComboBoxItemDelegate(QStyledItemDelegate):
    """Custom delegate to render QComboBox dropdown items with theme and proper states."""

    def __init__(self, parent=None, theme=None):
        super().__init__(parent)
        self.theme = theme  # Pass your ThemeEngine or color dict

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)

        # Use font from theme for absolute consistency
        option.font.setFamily(self.theme.fonts['base_family'])
        option.font.setPointSize(int(self.theme.fonts['interface_size'].replace('pt', '')))
        # Height same as QComboBox fixedHeight (24px to match new height)
        option.rect.setHeight(24)

        # Handle disabled item (grayout)
        if not (index.flags() & Qt.ItemIsEnabled):
            option.palette.setBrush(QPalette.Text, QBrush(QColor(self.theme.get_color("disabled_text"))))
            option.font.setItalic(True)
            # Disabled items should not have hover/selected background
            option.palette.setBrush(QPalette.Highlight, QBrush(QColor("transparent")))
        else:
            # Handle selected/hover colors for enabled items
            if option.state & QStyle.State_Selected:
                option.palette.setBrush(QPalette.Text, QBrush(QColor(self.theme.get_color("input_selection_text"))))
                option.palette.setBrush(QPalette.Highlight, QBrush(QColor(self.theme.get_color("combo_item_background_selected"))))
            elif option.state & QStyle.State_MouseOver:
                option.palette.setBrush(QPalette.Text, QBrush(QColor(self.theme.get_color("combo_text"))))
                option.palette.setBrush(QPalette.Highlight, QBrush(QColor(self.theme.get_color("combo_item_background_hover"))))
            else:
                # Normal state
                option.palette.setBrush(QPalette.Text, QBrush(QColor(self.theme.get_color("combo_text"))))
                option.palette.setBrush(QPalette.Highlight, QBrush(QColor("transparent")))


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
        self.parent_window = parent_window
        self._last_data = None
        self._last_category = None
        self._cached_metadata_keys = None
        self._hash_dialog_active = False  # Flag to prevent multiple dialogs
        self._last_selection_count = 0  # Track selection count to avoid unnecessary updates
        self._update_timer = None  # Timer for debouncing updates
        self.setup_ui()

        # Ensure theme inheritance for child widgets
        self._ensure_theme_inheritance()

    def setup_ui(self) -> None:
        """Setup the UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)  # Reduced from 8px to match text_removal_module

        # Row 1: Category
        category_row = QHBoxLayout()
        category_row.setContentsMargins(0, 0, 0, 0)
        category_row.setSpacing(8)
        category_label = QLabel("Category")
        category_label.setFixedWidth(70)
        category_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # type: ignore

        self.category_combo = QComboBox()
        self.category_combo.setFixedWidth(150)
        self.category_combo.setFixedHeight(24)

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
        self.options_label = QLabel("Field")  # Will be updated based on category
        self.options_label.setFixedWidth(70)  # Increased width by 10px
        self.options_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # type: ignore
        self.options_combo = QComboBox()
        self.options_combo.setFixedWidth(200)  # Increased width for metadata field names
        self.options_combo.setFixedHeight(24)  # Increased to match theme engine better

        options_row.addWidget(self.options_label)
        options_row.addWidget(self.options_combo)
        options_row.addStretch()
        layout.addLayout(options_row)

        # Apply custom delegates for better dropdown styling
        theme = ThemeEngine()
        self.options_combo.setItemDelegate(ComboBoxItemDelegate(self.options_combo, theme))
        self.category_combo.setItemDelegate(ComboBoxItemDelegate(self.category_combo, theme))

        # Connections
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        self.options_combo.currentIndexChanged.connect(self.emit_if_changed)

        # Initialize category availability
        self.update_category_availability()

        # Schedule options update (only if timer manager is available)
        try:
            schedule_ui_update(self.update_options, 0)
        except Exception:
            # Fallback for testing or when timer manager is not available
            self.update_options()

        self.setLayout(layout)

    def _on_category_changed(self) -> None:
        """Handle category combo box changes with safe timer scheduling."""
        # Check if disabled item was selected (None data)
        current_data = self.category_combo.currentData()
        if current_data is None:
            # Return to File Dates if disabled item was selected
            self.category_combo.setCurrentIndex(0)
            logger.debug("[MetadataWidget] Disabled item selected, returning to File Dates")
            return

        try:
            schedule_ui_update(self.update_options)
        except Exception:
            # Fallback for testing or when timer manager is not available
            self.update_options()

        # Check if we need to show dialog for hash/metadata calculation
        category = self.category_combo.currentData()
        if category in ["hash", "metadata_keys"]:
            self._check_calculation_requirements(category)

        # If Hash category is disabled, apply disabled styling
        if category == "hash":
            hash_item = self.category_model.item(1)
            if not (hash_item.flags() & Qt.ItemIsEnabled):
                # Hash category is disabled, apply disabled styling
                self.options_combo.clear()
                self.options_combo.addItem("CRC32", userData="hash_crc32")
                self.options_combo.setEnabled(False)
                self._apply_disabled_combo_styling()
                logger.debug("[MetadataWidget] Hash category disabled - applied disabled styling")

    def update_options(self) -> None:
        logger.debug(f"[DEBUG] [MetadataWidget] update_options CALLED for category: {self.category_combo.currentData()}")
        category = self.category_combo.currentData()
        logger.debug(f"[MetadataWidget] Updating options for category: {category}")

        self.options_combo.clear()
        logger.debug(f"[DEBUG] [MetadataWidget] Selected files: {[getattr(f, 'filename', None) for f in self._get_selected_files()]}")
        logger.debug(f"[DEBUG] [MetadataWidget] Selected files ids: {[id(f) for f in self._get_selected_files()]}")
        logger.debug(f"[DEBUG] [MetadataWidget] Selected files metadata: {[getattr(f, 'metadata', None) for f in self._get_selected_files()]}")

        if category == "file_dates":
            self.options_label.setText("Type")
            self.populate_file_dates()
            # File dates are always enabled
            self.options_combo.setEnabled(True)
            # Apply normal styling
            self._apply_normal_combo_styling()
        elif category == "hash":
            self.options_label.setText("Type")
            # ALWAYS call populate_hash_options for hash checking (even when file selection changes)
            logger.debug("[MetadataWidget] Hash category selected - checking for hash requirements")
            self.populate_hash_options()
            # Hash combo is managed by populate_hash_options
        elif category == "metadata_keys":
            self.options_label.setText("Field")
            self.populate_metadata_keys()
            # Metadata combo is managed by populate_metadata_keys
            # Apply normal styling if enabled
            if self.options_combo.isEnabled():
                self._apply_normal_combo_styling()

        # Set to first option by default (if exists)
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
        self.options_combo.clear()

        try:
            # Get selected files
            selected_files = self._get_selected_files()
            logger.debug(f"[HASH_DEBUG] Found {len(selected_files)} selected files.")

            if not selected_files:
                # No files selected - disable hash option
                self.options_combo.addItem("CRC32", userData="hash_crc32")
                # Disable the combo box
                self.options_combo.setEnabled(False)
                # Apply disabled styling to show text in gray
                self._apply_disabled_combo_styling()
                return False

            # Use efficient batch checking via database
            file_paths = [file_item.full_path for file_item in selected_files]

            # Get files that have hashes using batch query
            from core.persistent_hash_cache import get_persistent_hash_cache

            hash_cache = get_persistent_hash_cache()

            # Use batch method for efficiency
            files_with_hash = hash_cache.get_files_with_hash_batch(file_paths, "CRC32")
            files_needing_hash = [path for path in file_paths if path not in files_with_hash]

            logger.debug(f"[HASH_DEBUG] {len(files_with_hash)}/{len(file_paths)} files have hashes")

            # Always add CRC32 option (only hash type supported) - but always disabled
            self.options_combo.addItem("CRC32", userData="hash_crc32")

            # Always disabled combo box for hash (only CRC32 available)
            self.options_combo.setEnabled(False)
            # Apply disabled styling to show text in gray
            self._apply_disabled_combo_styling()

            if files_needing_hash:
                # Some files need hash calculation
                logger.debug(f"[HASH_DEBUG] {len(files_needing_hash)} files need hash calculation")
                return True
            else:
                # All files have hashes - but combo still disabled
                logger.debug(
                    "[HASH_DEBUG] All files have hashes, but combo disabled (only CRC32 available)"
                )
                return True

        except Exception as e:
            logger.error(f"[MetadataWidget] Error in populate_hash_options: {e}")
            # On error, disable hash option
            self.options_combo.addItem("CRC32", userData="hash_crc32")
            # Disable the combo box in case of error
            self.options_combo.setEnabled(False)
            # Apply disabled styling to show text in gray
            self._apply_disabled_combo_styling()
            return False

    def _get_selected_files(self):
        """Get selected files from the main window."""
        logger.debug(
            f"[HASH_DEBUG] _get_selected_files called. parent_window: {self.parent_window}"
        )

        try:
            # Try to get selected files from parent window
            if self.parent_window and hasattr(self.parent_window, "get_selected_files_ordered"):
                logger.debug("[HASH_DEBUG] Getting files from parent_window")
                files = self.parent_window.get_selected_files_ordered()
                logger.debug(f"[HASH_DEBUG] Got {len(files)} files from parent_window")
                return files

            # Try to get from ApplicationContext
            context = self._get_app_context()
            logger.debug(f"[HASH_DEBUG] ApplicationContext: {context}")

            # Try to get from FileStore
            if context and hasattr(context, "_file_store") and context._file_store:
                logger.debug("[HASH_DEBUG] Trying to get files from FileStore")
                selected_files = context._file_store.get_selected_files()
                if selected_files:
                    logger.debug(f"[HASH_DEBUG] Got {len(selected_files)} files from FileStore")
                    return selected_files

            # Try to get from SelectionStore
            if context and hasattr(context, "_selection_store") and context._selection_store:
                logger.debug("[HASH_DEBUG] Trying to get files from SelectionStore")
                selected_files = context._selection_store.get_selected_files()
                if selected_files:
                    logger.debug(
                        f"[HASH_DEBUG] Got {len(selected_files)} files from SelectionStore"
                    )
                    return selected_files

            logger.debug("[HASH_DEBUG] No files found in ApplicationContext stores")

        except Exception as e:
            logger.warning(f"[MetadataWidget] Error getting selected files: {e}")

        logger.debug("[HASH_DEBUG] Returning empty list - no source found")
        return []

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
            if self.parent_window and hasattr(self.parent_window, "main_window"):
                main_window = self.parent_window.main_window
            elif self.parent_window:
                main_window = self.parent_window
            else:
                context = self._get_app_context()
                if context and hasattr(context, "main_window"):
                    main_window = context.main_window

            if main_window and hasattr(main_window, "event_handler_manager"):
                # Use the existing hash calculation method
                main_window.event_handler_manager._handle_calculate_hashes(file_items_needing_hash)

                # Force preview update after hash calculation
                schedule_ui_update(
                    self.force_preview_update, 100
                )  # Small delay to ensure hash calculation completes
                self._hash_dialog_active = False  # <-- Ensure flag reset after calculation
                logger.debug(
                    "[MetadataWidget] Hash calculation completed, preview update scheduled"
                )
            else:
                logger.error("[MetadataWidget] Could not find main window for hash calculation")
                self._hash_dialog_active = False

        except Exception as e:
            logger.error(f"[MetadataWidget] Error calculating hashes: {e}")
            self._hash_dialog_active = False  # <-- Ensure flag reset on error

    def populate_metadata_keys(self) -> None:
        """Populate metadata keys με smart availability checking."""
        try:
            # Get selected files
            selected_files = self._get_selected_files()
            if not selected_files:
                # No files selected - disable metadata option
                self.options_combo.addItem("(No files selected)", userData=None)
                self.options_combo.setEnabled(False)
                # Apply disabled styling
                self._apply_disabled_combo_styling()
                logger.debug("[MetadataWidget] No files selected - disabled metadata combo")
                return

            # Use batch query for metadata availability
            from core.unified_rename_engine import UnifiedRenameEngine

            engine = UnifiedRenameEngine()
            metadata_availability = engine.get_metadata_availability(selected_files)

            # Count files with metadata
            files_with_metadata = sum(1 for has_meta in metadata_availability.values() if has_meta)
            total_files = len(selected_files)

            logger.debug(
                f"[MetadataWidget] {files_with_metadata}/{total_files} files have metadata"
            )

            if files_with_metadata == 0:
                # No files have metadata - disable combo
                self.options_combo.addItem("(No metadata found in files)", userData=None)
                self.options_combo.setEnabled(False)
                # Apply disabled styling
                self._apply_disabled_combo_styling()
                logger.debug("[MetadataWidget] No metadata found - disabled metadata combo")
                return

            # Get available metadata keys
            keys = self.get_available_metadata_keys()
            if not keys:
                # No metadata keys available - disable combo
                self.options_combo.addItem("(No metadata fields available)", userData=None)
                self.options_combo.setEnabled(False)
                # Apply disabled styling
                self._apply_disabled_combo_styling()
                logger.debug(
                    "[MetadataWidget] No metadata keys available - disabled metadata combo"
                )
                return

            # Some files have metadata - enable combo
            self.options_combo.setEnabled(True)
            # Apply normal styling
            self._apply_normal_combo_styling()
            logger.debug(f"[MetadataWidget] {len(keys)} metadata keys available - enabled combo")

            # Add metadata keys
            for key in sorted(keys):
                display = self.format_metadata_key_name(key)
                self.options_combo.addItem(display, userData=key)

        except Exception as e:
            logger.error(f"[MetadataWidget] Error in populate_metadata_keys: {e}")
            # On error, disable metadata option
            self.options_combo.addItem("(Error loading metadata)", userData=None)
            self.options_combo.setEnabled(False)
            # Apply disabled styling
            self._apply_disabled_combo_styling()
            logger.debug("[MetadataWidget] Error occurred - disabled metadata combo")

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
                logger.warning(
                    f"[MetadataWidget] Hash algorithm '{field}' not supported, using CRC32"
                )
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
        logger.debug(f"[DEBUG] [MetadataWidget] emit_if_changed CALLED")
        logger.debug(f"[DEBUG] [MetadataWidget] Current options: {[self.options_combo.itemText(i) for i in range(self.options_combo.count())]}")
        logger.debug(f"[DEBUG] [MetadataWidget] Current selected files: {[getattr(f, 'filename', None) for f in self._get_selected_files()]}")
        logger.debug(f"[DEBUG] [MetadataWidget] Current selected files ids: {[id(f) for f in self._get_selected_files()]}")
        logger.debug(f"[DEBUG] [MetadataWidget] Current selected files metadata: {[getattr(f, 'metadata', None) for f in self._get_selected_files()]}")
        new_data = self.get_data()
        if new_data != self._last_data:
            self._last_data = new_data
            self.updated.emit(self)
        else:
            # If data is the same but category changed, still emit for preview update
            # This handles the case where user switches from file_dates to hash and back
            current_category = self.category_combo.currentData()
            if hasattr(self, "_last_category") and self._last_category != current_category:
                self._last_category = current_category
                self.updated.emit(self)
                logger.debug(
                    f"[MetadataWidget] Category changed to {current_category}, forcing preview update"
                )
            elif not hasattr(self, "_last_category"):
                self._last_category = current_category

    def force_preview_update(self) -> None:
        """Force preview update even if data hasn't changed (for hash calculation)."""
        logger.debug("[DEBUG] [MetadataWidget] force_preview_update CALLED")
        self.update_options()
        self.emit_if_changed()
        self.updated.emit(self)
        logger.debug(
            "[MetadataWidget] Forced preview update with options refresh and emit_if_changed"
        )

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
            # The hash combo will remain disabled from populate_hash_options
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

    def update_category_availability(self):
        """Update category combo box availability based on selected files."""
        # Ensure theme inheritance
        self._ensure_theme_inheritance()

        # Get selected files
        selected_files = self._get_selected_files()

        # Set up the model if not already done
        if not hasattr(self, "category_model"):
            self.category_model = QStandardItemModel()
            self.category_combo.setModel(self.category_model)

            # Add items to model
            item1 = QStandardItem("File Dates")
            item1.setData("file_dates", Qt.UserRole)
            self.category_model.appendRow(item1)

            item2 = QStandardItem("Hash")
            item2.setData("hash", Qt.UserRole)
            self.category_model.appendRow(item2)

            item3 = QStandardItem("EXIF/Metadata")
            item3.setData("metadata_keys", Qt.UserRole)
            self.category_model.appendRow(item3)

        # File Dates category is ALWAYS enabled
        file_dates_item = self.category_model.item(0)
        file_dates_item.setFlags(file_dates_item.flags() | Qt.ItemIsEnabled)
        file_dates_item.setForeground(QColor())  # Reset to default color

        if not selected_files:
            # Disable Hash and EXIF when no files are selected
            hash_item = self.category_model.item(1)
            metadata_item = self.category_model.item(2)

            hash_item.setFlags(hash_item.flags() & ~Qt.ItemIsEnabled)
            hash_item.setForeground(QColor("#888888"))

            metadata_item.setFlags(metadata_item.flags() & ~Qt.ItemIsEnabled)
            metadata_item.setForeground(QColor("#888888"))

            # Apply normal styling - disabled items will be gray via QAbstractItemView styling
            self._apply_category_styling()

            # If current category is hash and is disabled, apply disabled styling
            if self.category_combo.currentData() == "hash":
                self.options_combo.clear()
                self.options_combo.addItem("CRC32", userData="hash_crc32")
                self.options_combo.setEnabled(False)
                self._apply_disabled_combo_styling()

            logger.debug("[MetadataWidget] No files selected - disabled Hash and EXIF options")
        else:
            # Check if files have hash data
            has_hash_data = self._check_files_have_hash(selected_files)
            hash_item = self.category_model.item(1)

            if has_hash_data:
                hash_item.setFlags(hash_item.flags() | Qt.ItemIsEnabled)
                hash_item.setForeground(QColor())  # Reset to default color
            else:
                hash_item.setFlags(hash_item.flags() & ~Qt.ItemIsEnabled)
                hash_item.setForeground(QColor("#888888"))

                # If current category is hash and is disabled, apply disabled styling
                if self.category_combo.currentData() == "hash":
                    self.options_combo.clear()
                    self.options_combo.addItem("CRC32", userData="hash_crc32")
                    self.options_combo.setEnabled(False)
                    self._apply_disabled_combo_styling()

            # Check if files have EXIF/metadata data
            has_metadata_data = self._check_files_have_metadata(selected_files)
            metadata_item = self.category_model.item(2)

            if has_metadata_data:
                metadata_item.setFlags(metadata_item.flags() | Qt.ItemIsEnabled)
                metadata_item.setForeground(QColor())  # Reset to default color
            else:
                metadata_item.setFlags(metadata_item.flags() & ~Qt.ItemIsEnabled)
                metadata_item.setForeground(QColor("#888888"))

            # Apply styling to category combo based on state
            self._apply_category_styling()

            logger.debug(
                f"[MetadataWidget] {len(selected_files)} files selected - Hash: {has_hash_data}, EXIF: {has_metadata_data}"
            )

    def _check_files_have_hash(self, selected_files) -> bool:
        """Check if any of the selected files have hash data."""
        try:
            file_paths = [file_item.full_path for file_item in selected_files]
            from core.persistent_hash_cache import get_persistent_hash_cache

            hash_cache = get_persistent_hash_cache()
            files_with_hash = hash_cache.get_files_with_hash_batch(file_paths, "CRC32")
            return len(files_with_hash) > 0
        except Exception as e:
            logger.error(f"[MetadataWidget] Error checking hash availability: {e}")
            return False

    def _check_files_have_metadata(self, selected_files) -> bool:
        """Check if any of the selected files have metadata."""
        try:
            from core.unified_rename_engine import UnifiedRenameEngine

            engine = UnifiedRenameEngine()
            metadata_availability = engine.get_metadata_availability(selected_files)
            return any(metadata_availability.values())
        except Exception as e:
            logger.error(f"[MetadataWidget] Error checking metadata availability: {e}")
            return False

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

            # Apply minimal styles to combo boxes
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

                /* Custom styling for disabled items in custom model */
                QComboBox QAbstractItemView::item {{
                    background-color: transparent;
                    color: {theme.get_color('combo_text')};
                    padding: 6px 8px;
                    border: none;
                    min-height: 18px;
                    border-radius: 3px;
                    margin: 1px;
                }}

                QComboBox QAbstractItemView::item:hover {{
                    background-color: {theme.get_color('combo_item_background_hover')};
                    color: {theme.get_color('combo_text')};
                }}

                QComboBox QAbstractItemView::item:selected {{
                    background-color: {theme.get_color('combo_item_background_selected')};
                    color: {theme.get_color('input_selection_text')};
                }}

                /* Force grayout for items without ItemIsEnabled flag */
                QComboBox QAbstractItemView::item:!enabled {{
                    background-color: transparent !important;
                    color: {theme.get_color('disabled_text')} !important;
                    opacity: 0.6 !important;
                }}

                QComboBox QAbstractItemView::item:!enabled:hover {{
                    background-color: transparent !important;
                    color: {theme.get_color('disabled_text')} !important;
                }}
            """

            # Apply styles to combo boxes
            # self.category_combo.setStyleSheet(combo_styles)
            # self.options_combo.setStyleSheet(combo_styles)

            logger.debug("[MetadataWidget] Theme inheritance ensured for combo boxes")

        except Exception as e:
            logger.warning(f"[MetadataWidget] Failed to ensure theme inheritance: {e}")

    def trigger_update_options(self):
        """Trigger update_options and hash check immediately (no debounce)."""
        logger.debug("[DEBUG] [MetadataWidget] trigger_update_options CALLED (no debounce)")
        # Update category availability first
        self.update_category_availability()
        # Then update options
        self.update_options()

    def _debounced_update_options(self):
        """Immediate update_options and hash check (no debounce, for compatibility)."""
        logger.debug("[DEBUG] [MetadataWidget] _debounced_update_options CALLED (no debounce)")
        # Update category availability first
        self.update_category_availability()
        # Then update options
        self.update_options()

    def _check_calculation_requirements(self, category: str):
        """Check if calculation dialog is needed for the selected category."""
        logger.debug(
            f"[DEBUG] [MetadataWidget] _check_calculation_requirements CALLED for category: {category}"
        )

        if self._hash_dialog_active:
            logger.debug("[MetadataWidget] Dialog already active, skipping check")
            return

        try:
            selected_files = self._get_selected_files()
            if not selected_files:
                logger.debug("[MetadataWidget] No files selected, no dialog needed")
                return

            if category == "hash":
                self._check_hash_calculation_requirements(selected_files)
            elif category == "metadata_keys":
                self._check_metadata_calculation_requirements(selected_files)

        except Exception as e:
            logger.error(f"[MetadataWidget] Error checking calculation requirements: {e}")
            self._hash_dialog_active = False

    def _check_hash_calculation_requirements(self, selected_files):
        """Check if hash calculation dialog is needed."""
        file_paths = [file_item.full_path for file_item in selected_files]
        from core.persistent_hash_cache import get_persistent_hash_cache

        hash_cache = get_persistent_hash_cache()
        files_with_hash = hash_cache.get_files_with_hash_batch(file_paths, "CRC32")
        files_needing_hash = [path for path in file_paths if path not in files_with_hash]

        if files_needing_hash:
            logger.debug(
                f"[MetadataWidget] {len(files_needing_hash)} files need hash calculation - showing dialog"
            )
            self._hash_dialog_active = True
            self._show_calculation_dialog(files_needing_hash, "hash")
        else:
            logger.debug("[MetadataWidget] All files have hashes - no dialog needed")

    def _check_metadata_calculation_requirements(self, selected_files):
        logger.debug(f"[DEBUG] [MetadataWidget] _check_metadata_calculation_requirements CALLED for {len(selected_files)} files")
        from core.unified_rename_engine import UnifiedRenameEngine
        engine = UnifiedRenameEngine()
        metadata_availability = engine.get_metadata_availability(selected_files)
        logger.debug(f"[DEBUG] [MetadataWidget] metadata_availability: {metadata_availability}")

        # Count files with metadata
        files_with_metadata = sum(1 for has_meta in metadata_availability.values() if has_meta)
        total_files = len(selected_files)

        if files_with_metadata < total_files:
            files_needing_metadata = [
                file_item.full_path
                for file_item in selected_files
                if not metadata_availability.get(file_item.full_path, False)
            ]
            logger.debug(
                f"[MetadataWidget] {len(files_needing_metadata)} files need metadata - showing dialog"
            )
            self._hash_dialog_active = True
            self._show_calculation_dialog(files_needing_metadata, "metadata")
        else:
            logger.debug("[MetadataWidget] All files have metadata - no dialog needed")

    def _show_calculation_dialog(self, files_needing_calculation, calculation_type: str):
        """Show dialog to calculate hash or metadata for files that need them."""
        logger.debug(
            f"[DEBUG] [MetadataWidget] _show_calculation_dialog CALLED for {len(files_needing_calculation)} files, type: {calculation_type}"
        )
        try:
            from widgets.custom_message_dialog import CustomMessageDialog

            # Create dialog message based on calculation type
            file_count = len(files_needing_calculation)

            if calculation_type == "hash":
                message = f"{file_count} out of {len(self._get_selected_files())} selected files do not have hash.\n\nWould you like to calculate hash for all files now?\n\nThis will allow you to use hash values in your filename transformations."
                title = "Hash Calculation Required"
                yes_text = "Calculate Hash"
            else:  # metadata
                message = f"{file_count} out of {len(self._get_selected_files())} selected files do not have metadata.\n\nWould you like to load metadata for all files now?\n\nThis will allow you to use metadata values in your filename transformations."
                title = "Metadata Loading Required"
                yes_text = "Load Metadata"

            logger.debug(
                f"[DEBUG] [MetadataWidget] Showing {calculation_type} calculation dialog with message: {message}"
            )

            # Show dialog
            result = CustomMessageDialog.question(
                self.parent_window, title, message, yes_text=yes_text, no_text="Cancel"
            )

            logger.debug(f"[DEBUG] [MetadataWidget] Dialog result: {result}")

            if result:
                # User chose to calculate
                logger.debug(f"[DEBUG] [MetadataWidget] User chose to calculate {calculation_type}")
                if calculation_type == "hash":
                    self._calculate_hashes_for_files(files_needing_calculation)
                else:
                    self._load_metadata_for_files(files_needing_calculation)
            else:
                # User cancelled - combo remains enabled but shows original names
                logger.debug(f"[MetadataWidget] User cancelled {calculation_type} calculation")
                # Don't disable combo - let it show original names for files without hash/metadata

        except Exception as e:
            logger.error(
                f"[MetadataWidget] Error showing {calculation_type} calculation dialog: {e}"
            )
            self._hash_dialog_active = False

    def _load_metadata_for_files(self, files_needing_metadata):
        """Load metadata for the given file paths."""
        try:
            # Convert file paths back to FileItem objects for metadata loading
            selected_files = self._get_selected_files()
            file_items_needing_metadata = []

            for file_path in files_needing_metadata:
                for file_item in selected_files:
                    if file_item.full_path == file_path:
                        file_items_needing_metadata.append(file_item)
                        break

            if not file_items_needing_metadata:
                logger.warning("[MetadataWidget] No file items found for metadata loading")
                return

            # Get main window for metadata loading
            main_window = None
            if self.parent_window and hasattr(self.parent_window, "main_window"):
                main_window = self.parent_window.main_window
            elif self.parent_window:
                main_window = self.parent_window
            else:
                context = self._get_app_context()
                if context and hasattr(context, "main_window"):
                    main_window = context.main_window

            if main_window and hasattr(main_window, "load_metadata_for_items"):
                # Use the existing metadata loading method
                main_window.load_metadata_for_items(
                    file_items_needing_metadata, use_extended=False, source="metadata_widget"
                )

                # Force preview update after metadata loading
                schedule_ui_update(
                    self.force_preview_update, 100
                )  # Small delay to ensure metadata loading completes
                self._hash_dialog_active = False
                logger.debug(
                    "[MetadataWidget] Metadata loading completed, preview update scheduled"
                )
            else:
                logger.error("[MetadataWidget] Could not find main window for metadata loading")
                self._hash_dialog_active = False

        except Exception as e:
            logger.error(f"[MetadataWidget] Error loading metadata: {e}")
            self._hash_dialog_active = False

    def _apply_disabled_combo_styling(self):
        """Apply disabled styling to the options combo box to show gray text"""
        try:
            from utils.theme_engine import ThemeEngine

            theme = ThemeEngine()

            # Apply simplified styling - dropdown styling handled by delegate
            disabled_css = f"""
                QComboBox {{
                    color: {theme.get_color('disabled_text')} !important;
                    background-color: {theme.get_color('combo_background')};
                    border: 1px solid {theme.get_color('combo_border')};
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-family: "{theme.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                    font-size: {theme.fonts['interface_size']};
                    min-height: 18px;
                }}

                QComboBox:disabled {{
                    color: {theme.get_color('disabled_text')} !important;
                    background-color: {theme.get_color('combo_background')};
                    border: 1px solid {theme.get_color('combo_border')};
                }}

                QComboBox::drop-down {{
                    border: none;
                    background-color: transparent;
                    width: 18px;
                }}

                QComboBox::down-arrow {{
                    image: url(resources/icons/feather_icons/chevrons-down.svg);
                    width: 12px;
                    height: 12px;
                }}
            """

            self.options_combo.setStyleSheet(disabled_css)
            self.options_combo.view().setStyleSheet(disabled_css)
            logger.debug("[MetadataWidget] Applied disabled styling to hash combo")

        except Exception as e:
            logger.warning(f"[MetadataWidget] Error applying disabled combo styling: {e}")

    def _apply_normal_combo_styling(self):
        """Apply normal styling to the options combo box"""
        try:
            from utils.theme_engine import ThemeEngine

            theme = ThemeEngine()

            # Apply simplified styling - dropdown styling handled by delegate
            normal_css = f"""
                QComboBox {{
                    background-color: {theme.get_color('combo_background')};
                    border: 1px solid {theme.get_color('combo_border')};
                    border-radius: 4px;
                    padding: 2px 6px;
                    color: {theme.get_color('combo_text')};
                    font-family: "{theme.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                    font-size: {theme.fonts['interface_size']};
                    min-height: 18px;
                    selection-background-color: {theme.get_color('combo_item_background_selected')};
                    selection-color: {theme.get_color('input_selection_text')};
                }}

                QComboBox:hover {{
                    background-color: {theme.get_color('combo_background_hover')};
                    border-color: {theme.get_color('input_border_hover')};
                    color: {theme.get_color('combo_text')};
                }}

                QComboBox:focus {{
                    border-color: {theme.get_color('input_border_focus')};
                    background-color: {theme.get_color('combo_background_hover')};
                    color: {theme.get_color('combo_text')};
                }}

                QComboBox:focus:hover {{
                    background-color: {theme.get_color('combo_background_pressed')};
                    color: {theme.get_color('combo_text_pressed')};
                }}

                QComboBox:on {{
                    background-color: {theme.get_color('combo_background_pressed')};
                    color: {theme.get_color('combo_text_pressed')};
                    border-color: {theme.get_color('input_border_focus')};
                }}

                QComboBox::drop-down {{
                    border: none;
                    background-color: transparent;
                    width: 18px;
                }}

                QComboBox::down-arrow {{
                    image: url(resources/icons/feather_icons/chevrons-down.svg);
                    width: 12px;
                    height: 12px;
                }}
            """

            self.options_combo.setStyleSheet(normal_css)
            self.options_combo.view().setStyleSheet(normal_css)
            logger.debug("[MetadataWidget] Applied normal styling to options combo")

        except Exception as e:
            logger.warning(f"[MetadataWidget] Error applying normal combo styling: {e}")

    def _apply_combo_theme_styling(self):
        """Apply theme styling to combo boxes and ensure inheritance"""
        try:
            theme = ThemeEngine()
            logger.debug("[MetadataWidget] Theme inheritance ensured for combo boxes")

            css = f"""
                QComboBox {{
                    background-color: {theme.get_color('input_background')};
                    border: 1px solid {theme.get_color('input_border')};
                    border-radius: 4px;
                    padding: 6px 8px;
                    color: {theme.get_color('input_text')};
                    font-size: 12px;
                    min-height: 20px;
                    selection-background-color: {theme.get_color('input_selection_background')};
                    selection-color: {theme.get_color('input_selection_text')};
                }}

                QComboBox:hover {{
                    border-color: {theme.get_color('input_border_hover')};
                }}

                QComboBox:focus {{
                    border-color: {theme.get_color('input_border_focus')};
                }}

                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}

                QComboBox::down-arrow {{
                    image: url(resources/icons/feather_icons/chevrons-down.svg);
                    width: 12px;
                    height: 12px;
                }}

                /* Custom styling for disabled items in custom model */
                QComboBox QAbstractItemView::item {{
                    background-color: transparent;
                    color: {theme.get_color('combo_text')};
                    padding: 6px 8px;
                    border: none;
                    min-height: 18px;
                    border-radius: 3px;
                    margin: 1px;
                }}

                QComboBox QAbstractItemView::item:hover {{
                    background-color: {theme.get_color('combo_item_background_hover')};
                    color: {theme.get_color('combo_text')};
                }}

                QComboBox QAbstractItemView::item:selected {{
                    background-color: {theme.get_color('combo_item_background_selected')};
                    color: {theme.get_color('input_selection_text')};
                }}

                /* Force grayout for items without ItemIsEnabled flag */
                QComboBox QAbstractItemView::item:!enabled {{
                    background-color: transparent !important;
                    color: {theme.get_color('disabled_text')} !important;
                    opacity: 0.6 !important;
                }}

                QComboBox QAbstractItemView::item:!enabled:hover {{
                    background-color: transparent !important;
                    color: {theme.get_color('disabled_text')} !important;
                }}
            """

            self.category_combo.setStyleSheet(css)

            # Apply style recursively to ensure inheritance
            apply_style_recursively(self.category_combo, self.category_combo.style())

        except Exception as e:
            logger.error(f"[MetadataWidget] Error applying combo theme styling: {e}")

    def _apply_disabled_category_styling(self):
        """Apply disabled styling to the category combo box to show gray text"""
        try:
            from utils.theme_engine import ThemeEngine

            theme = ThemeEngine()

            # Apply simplified styling - dropdown styling handled by delegate
            disabled_css = f"""
                QComboBox {{
                    color: {theme.get_color('disabled_text')} !important;
                    background-color: {theme.get_color('combo_background')};
                    border: 1px solid {theme.get_color('combo_border')};
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-family: "{theme.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                    font-size: {theme.fonts['interface_size']};
                    min-height: 18px;
                }}

                QComboBox:disabled {{
                    color: {theme.get_color('disabled_text')} !important;
                    background-color: {theme.get_color('combo_background')};
                    border: 1px solid {theme.get_color('combo_border')};
                }}

                QComboBox::drop-down {{
                    border: none;
                    background-color: transparent;
                    width: 18px;
                }}

                QComboBox::down-arrow {{
                    image: url(resources/icons/feather_icons/chevrons-down.svg);
                    width: 12px;
                    height: 12px;
                }}
            """

            self.category_combo.setStyleSheet(disabled_css)
            self.category_combo.view().setStyleSheet(disabled_css)
            logger.debug("[MetadataWidget] Applied disabled styling to category combo")

        except Exception as e:
            logger.warning(f"[MetadataWidget] Error applying disabled category styling: {e}")

    def _apply_category_styling(self):
        """Apply normal styling to the category combo box"""
        try:
            from utils.theme_engine import ThemeEngine

            theme = ThemeEngine()

            # Apply simplified styling - dropdown styling handled by delegate
            normal_css = f"""
                QComboBox {{
                    background-color: {theme.get_color('combo_background')};
                    border: 1px solid {theme.get_color('combo_border')};
                    border-radius: 4px;
                    padding: 2px 6px;
                    color: {theme.get_color('combo_text')};
                    font-family: "{theme.fonts['base_family']}", "Segoe UI", Arial, sans-serif;
                    font-size: {theme.fonts['interface_size']};
                    min-height: 18px;
                    selection-background-color: {theme.get_color('combo_item_background_selected')};
                    selection-color: {theme.get_color('input_selection_text')};
                }}

                QComboBox:hover {{
                    background-color: {theme.get_color('combo_background_hover')};
                    border-color: {theme.get_color('input_border_hover')};
                    color: {theme.get_color('combo_text')};
                }}

                QComboBox:focus {{
                    border-color: {theme.get_color('input_border_focus')};
                    background-color: {theme.get_color('combo_background_hover')};
                    color: {theme.get_color('combo_text')};
                }}

                QComboBox:focus:hover {{
                    background-color: {theme.get_color('combo_background_pressed')};
                    color: {theme.get_color('combo_text_pressed')};
                }}

                QComboBox:on {{
                    background-color: {theme.get_color('combo_background_pressed')};
                    color: {theme.get_color('combo_text_pressed')};
                    border-color: {theme.get_color('input_border_focus')};
                }}

                QComboBox::drop-down {{
                    border: none;
                    background-color: transparent;
                    width: 18px;
                }}

                QComboBox::down-arrow {{
                    image: url(resources/icons/feather_icons/chevrons-down.svg);
                    width: 12px;
                    height: 12px;
                }}
            """

            self.category_combo.setStyleSheet(normal_css)
            self.category_combo.view().setStyleSheet(normal_css)
            logger.debug("[MetadataWidget] Applied normal styling to category combo")

        except Exception as e:
            logger.warning(f"[MetadataWidget] Error applying normal category styling: {e}")
