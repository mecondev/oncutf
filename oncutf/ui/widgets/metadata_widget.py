"""Module: metadata_widget.py

Author: Michael Economou
Date: 2025-05-31

Widget for metadata selection (file dates or EXIF), with optimized signal emission system.
"""

from typing import Any

from PyQt5.QtCore import Qt, pyqtSignal

from oncutf.core.pyqt_imports import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from oncutf.ui.widgets.hierarchical_combo_box import HierarchicalComboBox
from oncutf.ui.widgets.metadata.category_manager import CategoryManager
from oncutf.ui.widgets.metadata.field_formatter import FieldFormatter
from oncutf.ui.widgets.metadata.hash_handler import HashHandler
from oncutf.ui.widgets.metadata.metadata_keys_handler import MetadataKeysHandler
from oncutf.ui.widgets.metadata.styling_handler import StylingHandler
from oncutf.ui.widgets.styled_combo_box import StyledComboBox
from oncutf.utils.logger_factory import get_cached_logger
from oncutf.utils.timer_manager import schedule_ui_update

# ApplicationContext integration
try:
    from oncutf.core.application_context import get_app_context
except ImportError:
    get_app_context = None

logger = get_cached_logger(__name__)


class MetadataWidget(QWidget):
    """Widget for file metadata selection (file dates or EXIF).
    Supports category selection and dynamic fields,
    and emits update signal only when there is an actual change.
    """

    updated = pyqtSignal(object)
    settings_changed = pyqtSignal(dict)  # Emitted on ANY setting change for instant preview

    def __init__(self, parent: QWidget | None = None, parent_window: QWidget | None = None) -> None:
        super().__init__(parent)
        self.parent_window = parent_window
        self._last_data = None
        self._last_category = None
        self._cached_metadata_keys = None
        self._hash_dialog_active = False  # Flag to prevent multiple dialogs
        self._last_selection_count = 0  # Track selection count to avoid unnecessary updates
        self._update_timer = None  # Timer for debouncing updates

        # Initialize handlers
        self._category_manager = CategoryManager(self)
        self._metadata_keys_handler = MetadataKeysHandler(self)
        self._hash_handler = HashHandler(self)
        self._styling_handler = StylingHandler(self)

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
        category_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # type: ignore[arg-type]

        self.category_combo = StyledComboBox()
        self.category_combo.setFixedWidth(150)

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
        self.options_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # type: ignore[arg-type]

        # Use HierarchicalComboBox for better organization
        self.options_combo = HierarchicalComboBox()
        self.options_combo.setFixedWidth(200)  # Increased width for metadata field names
        # HierarchicalComboBox handles its own height

        options_row.addWidget(self.options_label)
        options_row.addWidget(self.options_combo)
        options_row.addStretch()
        layout.addLayout(options_row)

        # Connections (delegate setup handled by StyledComboBox)
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        self.category_combo.currentIndexChanged.connect(self._emit_settings_changed)
        # Use new confirmed-selection signal to avoid preview races
        self.options_combo.item_selected.connect(self._on_hierarchical_item_selected)  # keep legacy
        self.options_combo.selection_confirmed.connect(self._on_hierarchical_selection_confirmed)
        self.options_combo.selection_confirmed.connect(self._emit_settings_changed)
        logger.debug("Connected to hierarchical combo selection_confirmed signal")

        # Initialize category availability
        self.update_category_availability()

        # Schedule options update (only if timer manager is available)
        try:
            schedule_ui_update(self.update_options, 0)
        except Exception:
            # Fallback for testing or when timer manager is not available
            self.update_options()

        self.setLayout(layout)
        logger.debug("MetadataWidget UI setup completed")

    def _on_category_changed(self) -> None:
        """Handle category combo box changes.

        Deprecated: Use CategoryManager.on_category_changed() instead.
        This method is kept for backwards compatibility.
        """
        self._category_manager.on_category_changed()

    def _emit_settings_changed(self) -> None:
        """Emit settings_changed signal on ANY user interaction.

        This provides instant preview updates while maintaining
        backwards compatibility with the 'updated' signal.
        """
        try:
            config = self.get_data()
            logger.debug("Emitting settings_changed with config: %s", config)
            self.settings_changed.emit(config)
            # Also emit legacy 'updated' signal for backwards compatibility
            self.updated.emit(config)
        except Exception as e:
            logger.warning("Error emitting settings_changed: %s", e)

    def update_options(self) -> None:
        """Update options combo box based on selected category.

        Deprecated: Use CategoryManager.update_options() instead.
        This method is kept for backwards compatibility.
        """
        category = self.category_combo.currentData()

        # Set label based on category
        if category in {"file_dates", "hash"}:
            self.options_label.setText("Type")
        elif category == "metadata_keys":
            self.options_label.setText("Field")

        # Delegate to CategoryManager
        self._category_manager.update_options()

        # Set to first option by default (if exists)
        if hasattr(self.options_combo, "get_current_data"):
            # For hierarchical combo box, we don't need to set index
            # The first item will be automatically selected
            current_data = self.options_combo.get_current_data()
            logger.debug("Hierarchical combo current data: %s", current_data)
        elif self.options_combo.count() > 0:
            self.options_combo.setCurrentIndex(0)
            logger.debug("Regular combo set to index 0")

    def populate_file_dates(self) -> None:
        """Populate options combo with file date formats.

        Deprecated: Use CategoryManager.populate_file_dates() instead.
        This method is kept for backwards compatibility.
        """
        self._category_manager.populate_file_dates()

    def populate_hash_options(self) -> bool:
        """Populate hash options with efficient batch hash checking."""
        return self._hash_handler.populate_hash_options()

    def _get_selected_files(self):
        """Get selected files from the main window."""
        try:
            # Try to get selected files from parent window
            if self.parent_window and hasattr(self.parent_window, "get_selected_files_ordered"):
                files = self.parent_window.get_selected_files_ordered()
                return files

            # Try to get from ApplicationContext
            context = self._get_app_context()

            # Try to get from FileStore
            if context and hasattr(context, "_file_store") and context._file_store:
                selected_files = context._file_store.get_selected_files()  # type: ignore
                if selected_files:
                    return selected_files

            # Try to get from SelectionStore
            if context and hasattr(context, "_selection_store") and context._selection_store:
                selected_files = context._selection_store.get_selected_files()  # type: ignore
                if selected_files:
                    return selected_files

        except Exception as e:
            logger.warning("[MetadataWidget] Error getting selected files: %s", e)

        return []

    def _calculate_hashes_for_files(self, files_needing_hash):
        """Calculate hashes for the given file paths.

        Deprecated: Use HashHandler._calculate_hashes_for_files() instead.
        This method is kept for backwards compatibility.
        """
        self._hash_handler._calculate_hashes_for_files(files_needing_hash)

    def populate_metadata_keys(self) -> None:
        """Populate the hierarchical combo box with available metadata keys.
        Keys are grouped by category for better organization.
        """
        self._metadata_keys_handler.populate_metadata_keys()

    def _group_metadata_keys(self, keys: set[str]) -> dict[str, list[str]]:
        """Group metadata keys by category for better organization.

        Deprecated: Use MetadataKeysHandler._group_metadata_keys() instead.
        This method is kept for backwards compatibility.
        """
        return self._metadata_keys_handler._group_metadata_keys(keys)

    def _classify_metadata_key(self, key: str) -> str:
        """Classify a metadata key into a category.

        Deprecated: Use MetadataKeysHandler._classify_metadata_key() instead.
        This method is kept for backwards compatibility.
        """
        return self._metadata_keys_handler._classify_metadata_key(key)

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
        try:
            from oncutf.core.application_context import get_app_context

            context = get_app_context()
            if context and hasattr(context, "_metadata_cache"):
                cache = context._metadata_cache
                return cache
            else:
                return None
        except Exception as e:
            logger.debug(
                "[MetadataWidget] Error getting metadata cache: %s",
                e,
                extra={"dev_only": True},
            )
            return None

    def get_available_metadata_keys(self) -> set[str]:
        """Get all available metadata keys from selected files.

        Returns:
            Set of metadata key names found in selected files
        """
        return self._metadata_keys_handler.get_available_metadata_keys()

    def format_metadata_key_name(self, key: str) -> str:
        """Format metadata key names for better readability.

        Deprecated: Use FieldFormatter.format_metadata_key_name() instead.
        This method is kept for backwards compatibility.
        """
        return FieldFormatter.format_metadata_key_name(key)

    def _format_field_name(self, field: str) -> str:
        """Format field names by replacing underscores and camelCase.

        Deprecated: Use FieldFormatter._format_field_name() instead.
        This method is kept for backwards compatibility.
        """
        return FieldFormatter._format_field_name(field)

    def _format_camel_case(self, text: str) -> str:
        """Format camelCase text by adding spaces before capitals.

        Deprecated: Use FieldFormatter._format_camel_case() instead.
        This method is kept for backwards compatibility.
        """
        return FieldFormatter._format_camel_case(text)

    def get_data(self) -> dict:
        """Returns the state for use in the rename system."""
        category = self.category_combo.currentData() or "file_dates"

        # Use the hierarchical combo box API
        if hasattr(self.options_combo, "get_current_data"):
            field = self.options_combo.get_current_data()
            logger.debug("get_data: Using hierarchical combo, field: %s", field)
        else:
            # Fallback to regular QComboBox API
            field = self.options_combo.currentData()
            logger.debug("get_data: Using regular combo, field: %s", field)

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
                    "[MetadataWidget] Hash algorithm '%s' not supported, using CRC32",
                    field,
                )
                field = "hash_crc32"

        # For metadata_keys category, ensure we don't return None field
        if category == "metadata_keys" and not field:
            # If no field is selected, try to get the first available metadata key
            available_keys = self.get_available_metadata_keys()
            if available_keys:
                field = sorted(available_keys)[0]
                logger.debug(
                    "[MetadataWidget] No field selected, using first available key: %s",
                    field,
                    extra={"dev_only": True},
                )
            else:
                # If no metadata keys available, fallback to file dates
                category = "file_dates"
                field = "last_modified_yymmdd"
                logger.debug(
                    "[MetadataWidget] No metadata keys available, falling back to file dates",
                    extra={"dev_only": True},
                )

        # Validate the field using MetadataFieldValidator if applicable
        if category == "metadata_keys" and field:
            # For metadata keys, we can't use the standard validators since these are field names
            # But we can check if the field exists in available keys
            available_keys = self.get_available_metadata_keys()
            if field not in available_keys:
                logger.warning(
                    "[MetadataWidget] Selected metadata field '%s' not available, using first available key",
                    field,
                )
                if available_keys:
                    field = sorted(available_keys)[0]
                else:
                    # Fallback to file dates if no metadata keys available
                    category = "file_dates"
                    field = "last_modified_yymmdd"

        result = {
            "type": "metadata",
            "category": category,
            "field": field,
        }

        logger.debug("get_data returning: %s", result)
        return result

    def emit_if_changed(self) -> None:
        # Log current combo box state
        if hasattr(self.options_combo, "get_current_data"):
            current_text = self.options_combo.get_current_text()
            current_data = self.options_combo.get_current_data()
            current_index = -1  # Not applicable for hierarchical combo
        else:
            current_index = self.options_combo.currentIndex()
            current_text = self.options_combo.currentText()
            current_data = self.options_combo.currentData()
        logger.debug(
            "[MetadataWidget] Current combo state - index: %d, text: '%s', data: %s",
            current_index,
            current_text,
            current_data,
            extra={"dev_only": True},
        )

        new_data = self.get_data()

        if new_data != self._last_data:
            self._last_data = new_data
            logger.debug("[MetadataWidget] Data changed, emitting signal", extra={"dev_only": True})
            self.updated.emit(self)
        else:
            # If data is the same but category changed, still emit for preview update
            # This handles the case where user switches from file_dates to hash and back
            current_category = self.category_combo.currentData()
            if hasattr(self, "_last_category") and self._last_category != current_category:
                self._last_category = current_category
                logger.debug(
                    "[MetadataWidget] Category changed to %s, forcing preview update",
                    current_category,
                    extra={"dev_only": True},
                )
                self.updated.emit(self)
            elif not hasattr(self, "_last_category"):
                self._last_category = current_category

    def force_preview_update(self) -> None:
        """Force preview update even if data hasn't changed (for hash calculation)."""
        self.update_options()
        self.emit_if_changed()
        self.updated.emit(self)
        logger.debug(
            "[MetadataWidget] Forced preview update with options refresh and emit_if_changed",
            extra={"dev_only": True},
        )

    def clear_cache(self) -> None:
        """Clear the metadata keys cache to force refresh."""
        self._cached_metadata_keys = None

    def refresh_metadata_keys(self) -> None:
        """Refresh metadata keys and update the combo box if currently showing metadata."""
        self.clear_cache()
        category = self.category_combo.currentData()
        if category == "metadata_keys":
            self.populate_metadata_keys()
            self.emit_if_changed()
        elif category == "hash":
            self.populate_hash_options()
            # The hash combo will remain disabled from populate_hash_options
            self.emit_if_changed()

    @staticmethod
    def is_effective(data: dict) -> bool:
        """The metadata module is effective if it has a valid field for the selected category.
        """
        field = data.get("field")
        category = data.get("category", "file_dates")

        # For hash category, check if field is a valid hash type
        if category == "hash":
            return field and field.startswith("hash_")  # type: ignore

        # For other categories, any field is effective
        return bool(field)

    def _get_supported_hash_algorithms(self) -> set:
        """Get list of supported hash algorithms from the async operations manager.

        Deprecated: Use HashHandler._get_supported_hash_algorithms() instead.
        This method is kept for backwards compatibility.
        """
        return self._hash_handler._get_supported_hash_algorithms()

    def update_category_availability(self):
        """Update category combo box availability based on selected files.

        Deprecated: Use CategoryManager.update_category_availability() instead.
        This method is kept for backwards compatibility.
        """
        self._category_manager.update_category_availability()

    def _check_files_have_hash(self, selected_files) -> bool:
        """Check if any of the selected files have hash data.

        Deprecated: Use HashHandler._check_files_have_hash() instead.
        This method is kept for backwards compatibility.
        """
        return self._hash_handler._check_files_have_hash(selected_files)

    def _ensure_theme_inheritance(self) -> None:
        """Ensure that child widgets inherit theme styles properly.

        Deprecated: Use StylingHandler.ensure_theme_inheritance() instead.
        This method is kept for backwards compatibility.
        """
        self._styling_handler.ensure_theme_inheritance()

    def trigger_update_options(self):
        """Trigger update_options and hash check immediately (no debounce)."""
        # Update category availability first
        self.update_category_availability()
        # Then update options
        self.update_options()

    def _debounced_update_options(self):
        """Immediate update_options and hash check (no debounce, for compatibility)."""
        # Update category availability first
        self.update_category_availability()
        # Then update options
        self.update_options()

    def _check_calculation_requirements(self, category: str):
        """Check if calculation dialog is needed for the selected category.

        Deprecated: Use CategoryManager._check_calculation_requirements() instead.
        This method is kept for backwards compatibility.
        """
        self._category_manager._check_calculation_requirements(category)

    def _check_hash_calculation_requirements(self, selected_files):
        """Check if hash calculation dialog is needed.

        Deprecated: Use HashHandler._check_hash_calculation_requirements() instead.
        This method is kept for backwards compatibility.
        """
        self._hash_handler._check_hash_calculation_requirements(selected_files)

    def _show_calculation_dialog(self, files_needing_calculation, calculation_type: str):
        """Show calculation dialog for hash or metadata.

        Deprecated: Use HashHandler._show_calculation_dialog() instead.
        This method is kept for backwards compatibility.
        """
        self._hash_handler._show_calculation_dialog(files_needing_calculation, calculation_type)

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
                    "[MetadataWidget] Metadata loading completed, preview update scheduled",
                    extra={"dev_only": True},
                )
            else:
                logger.error("[MetadataWidget] Could not find main window for metadata loading")
                self._hash_dialog_active = False

        except Exception as e:
            logger.error("[MetadataWidget] Error loading metadata: %s", e)
            self._hash_dialog_active = False

    def _apply_disabled_combo_styling(self):
        """Apply disabled styling to hierarchical combo box.

        Deprecated: Use StylingHandler.apply_disabled_combo_styling() instead.
        This method is kept for backwards compatibility.
        """
        self._styling_handler.apply_disabled_combo_styling()

    def _apply_normal_combo_styling(self):
        """Apply normal styling to hierarchical combo box.

        Deprecated: Use StylingHandler.apply_normal_combo_styling() instead.
        This method is kept for backwards compatibility.
        """
        self._styling_handler.apply_normal_combo_styling()

    def _apply_combo_theme_styling(self):
        """Apply theme styling to combo boxes.

        Deprecated: Use StylingHandler.apply_combo_theme_styling() instead.
        This method is kept for backwards compatibility.
        """
        self._styling_handler.apply_combo_theme_styling()

    def _apply_disabled_category_styling(self):
        """Apply disabled styling to the category combo box.

        Deprecated: Use StylingHandler.apply_disabled_category_styling() instead.
        This method is kept for backwards compatibility.
        """
        self._styling_handler.apply_disabled_category_styling()

    def _apply_category_styling(self):
        """Apply normal styling to the category combo box.

        Deprecated: Use StylingHandler.apply_category_styling() instead.
        This method is kept for backwards compatibility.
        """
        self._styling_handler.apply_category_styling()

    def _on_hierarchical_item_selected(self, _text: str, _data: Any):
        """Handle item selection from hierarchical combo box."""
        logger.debug(
            "[MetadataWidget] Hierarchical item selected - text: %s, data: %s",
            _text,
            _data,
            extra={"dev_only": True},
        )

        # CRITICAL: Close the dropdown immediately
        if hasattr(self.options_combo, "hidePopup"):
            self.options_combo.hidePopup()

        # Clear preview cache to force refresh when selection changes
        preview_manager = None

        # Try to find preview manager from parent window
        if self.parent_window and hasattr(self.parent_window, "preview_manager"):
            preview_manager = self.parent_window.preview_manager

        # Fallback: Try to find via application context
        if not preview_manager:
            try:
                from oncutf.core.application_context import get_app_context

                context = get_app_context()
                if (
                    context
                    and hasattr(context, "main_window")
                    and hasattr(context.main_window, "preview_manager")
                ):
                    preview_manager = context.main_window.preview_manager
            except Exception as e:
                logger.debug("[MetadataWidget] Error finding preview manager via context: %s", e)

        if preview_manager:
            preview_manager.clear_cache()
            logger.debug(
                "[MetadataWidget] Preview cache cleared on item selection", extra={"dev_only": True}
            )
        else:
            logger.warning("[MetadataWidget] Could not find preview_manager to clear cache")

        # Force update by resetting last data
        # This ensures emit_if_changed() will emit even if it thinks data hasn't changed
        self._last_data = None

        # Emit changes immediately without debouncing for responsive UI
        self.emit_if_changed()

    def _on_hierarchical_selection_confirmed(self, text: str, data: Any):
        """Handle confirmed item selection from hierarchical combo box (finalized after popup)."""
        logger.debug(
            "[MetadataWidget] Hierarchical selection confirmed - text: %s, data: %s",
            text,
            data,
            extra={"dev_only": True},
        )

        # Ensure popup is closed
        if hasattr(self.options_combo, "hidePopup"):
            self.options_combo.hidePopup()

        # Clear preview cache to force refresh when selection changes
        preview_manager = None
        if self.parent_window and hasattr(self.parent_window, "preview_manager"):
            preview_manager = self.parent_window.preview_manager

        # Fallback: Try to find via application context
        if not preview_manager:
            try:
                from oncutf.core.application_context import get_app_context

                context = get_app_context()
                if (
                    context
                    and hasattr(context, "main_window")
                    and hasattr(context.main_window, "preview_manager")
                ):
                    preview_manager = context.main_window.preview_manager
            except Exception:
                preview_manager = None

        if preview_manager:
            # Clear preview cache and request immediate refresh via parent window if possible
            preview_manager.clear_cache()
            logger.debug(
                "[MetadataWidget] Preview cache cleared on confirmed selection",
                extra={"dev_only": True},
            )
        else:
            logger.debug(
                "[MetadataWidget] No preview_manager found to clear cache", extra={"dev_only": True}
            )

        # Ask parent window to refresh preview immediately (no debounce)
        if self.parent_window and hasattr(self.parent_window, "request_preview_update"):
            try:
                self.parent_window.request_preview_update()
                logger.debug(
                    "[MetadataWidget] Requested preview update from parent_window",
                    extra={"dev_only": True},
                )
            except Exception as e:
                logger.debug(
                    "[MetadataWidget] request_preview_update failed: %s",
                    e,
                    extra={"dev_only": True},
                )
        else:
            # Fallback: try to build the full rename_data from parent_window if available,
            # don't pass only the metadata widget dict (it causes stale/mismatched cache keys).
            try:
                selected_files = self._get_selected_files()
                # Prefer parent_window.get_rename_data() if implemented
                if self.parent_window and hasattr(self.parent_window, "get_rename_data"):
                    full_rename_data = self.parent_window.get_rename_data()
                else:
                    # Best-effort fallback to attribute previously stored on the window
                    full_rename_data = getattr(self.parent_window, "rename_data", {}) or {}

                preview_manager.generate_preview_names_forced(
                    selected_files,
                    full_rename_data,
                    getattr(self.parent_window, "metadata_cache", None),
                    getattr(self.parent_window, "all_modules", []),
                )
                logger.debug(
                    "[MetadataWidget] Called preview_manager.generate_preview_names_forced (with full rename_data)",
                    extra={"dev_only": True},
                )
            except Exception as e:
                logger.debug(
                    "[MetadataWidget] Forced preview generation failed: %s",
                    e,
                    extra={"dev_only": True},
                )

        # Finally emit updated signal for the metadata widget (notify preview system)
        # We avoid relying on _last_data hack; just emit current state
        self.emit_if_changed()
        self.updated.emit(self)
        logger.debug(
            "[MetadataWidget] Emitted updated after confirmed selection", extra={"dev_only": True}
        )

    def _on_selection_changed(self):
        self.update_options()
        self.force_preview_update()

    def _on_metadata_loaded(self):
        self.update_options()
