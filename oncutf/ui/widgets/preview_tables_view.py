"""Module: preview_tables_view.py

Author: Michael Economou
Date: 2025-06-11

preview_tables_view.py
Implements a view that manages the preview tables for old/new filenames
with intelligent placeholder management and scrollbar optimization.
Features:
- Placeholder management (show when empty, hide when populated)
- Intelligent horizontal scrolling (expand to fill or enable scrollbar)
- Synchronized scrolling between old/new name tables
- Status icon display for rename validation
- Custom table widgets with resize signal handling
"""

from oncutf.core.pyqt_imports import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QIcon,
    QLabel,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    pyqtSignal,
)
from oncutf.core.theme_manager import get_theme_manager
from oncutf.utils.filename_validator import get_validation_error_message, is_validation_error_marker
from oncutf.utils.logger_factory import get_cached_logger
from oncutf.utils.placeholder_helper import create_placeholder_helper
from oncutf.utils.timer_manager import schedule_scroll_adjust, schedule_ui_update
from oncutf.utils.tooltip_helper import TooltipHelper, TooltipType

logger = get_cached_logger(__name__)


class PreviewTableWidget(QTableWidget):
    """Custom QTableWidget for preview tables with intelligent scrollbar management.
    Emits resize signal when the widget is resized to update placeholders and column widths.
    Supports enhanced tooltips for validation errors.
    """

    resized = pyqtSignal()  # Emitted when table is resized

    def __init__(self, rows=0, columns=1, parent=None):
        super().__init__(rows, columns, parent)

        # Enable mouse tracking for tooltips
        self.setMouseTracking(True)

    def resizeEvent(self, event):
        """Override to emit resize signal for intelligent column width adjustments."""
        super().resizeEvent(event)
        # Emit signal with small delay to ensure layout is stable
        schedule_ui_update(self.resized.emit, 10)

    def mouseMoveEvent(self, event):
        """Handle mouse move events to show enhanced tooltips"""
        try:
            # Get item under mouse
            item = self.itemAt(event.pos())
            if item and item.text():
                # Check if this is a validation error case
                if is_validation_error_marker(item.text()):
                    # Show enhanced error tooltip
                    from oncutf.utils.tooltip_helper import TooltipHelper

                    error_msg = "Invalid filename - contains validation errors"
                    TooltipHelper.show_error_tooltip(self, error_msg)
                else:
                    # Let Qt handle standard tooltips
                    super().mouseMoveEvent(event)
            else:
                super().mouseMoveEvent(event)

        except Exception as e:
            logger.debug(
                "[PreviewTableWidget] Error in mouseMoveEvent: %s",
                e,
                extra={"dev_only": True},
            )
            super().mouseMoveEvent(event)


class PreviewTablesView(QWidget):
    """View that manages the preview tables for old/new filenames.

    Features:
    - Unified placeholder management using PlaceholderHelper
    - Synchronized scrolling between tables
    - Intelligent horizontal scrollbar management
    - Status icon display for rename validation

    Signals:
        status_updated: Emitted when status message should be updated
        refresh_requested: Emitted when F5 is pressed to request preview refresh
    """

    status_updated = pyqtSignal(str)  # Emitted with HTML status message
    refresh_requested = pyqtSignal()  # Emitted when F5 refresh is requested

    def __init__(self, parent=None):
        super().__init__(parent)

        # Allow widget to receive keyboard focus for shortcuts
        self.setFocusPolicy(Qt.StrongFocus)

        # Constants
        self.PLACEHOLDER_SIZE = 120

        # Initialize components
        self._setup_ui()
        self._setup_placeholders()
        self._setup_signals()
        self._setup_shortcuts()

        # Show placeholders immediately during initialization
        self._placeholders_ready = True
        self._set_placeholders_visible(True)

        # Center placeholders after layout with small delay
        schedule_ui_update(self._handle_table_resize, 50)

        logger.debug(
            "[PreviewTablesView] Initialized with intelligent scrolling", extra={"dev_only": True}
        )

    def _setup_ui(self):
        """Setup the UI layout and tables."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)  # Reduce spacing between labels and tables

        # Labels
        labels_layout = QHBoxLayout()
        labels_layout.setContentsMargins(0, 2, 0, 0)  # Add 2px top margin
        self.old_label = QLabel("Old file(s) name(s)")
        self.new_label = QLabel("New file(s) name(s)")

        # Create spacer label with same width as icon table for proper alignment
        self.icon_spacer_label = QLabel("")
        self.icon_spacer_label.setFixedWidth(24)  # Same as icon_table width

        labels_layout.addWidget(self.old_label)
        labels_layout.addWidget(self.new_label)
        labels_layout.addWidget(self.icon_spacer_label)  # Space for icon column

        layout.addLayout(labels_layout)

        # Tables
        tables_layout = QHBoxLayout()

        self.old_names_table = PreviewTableWidget(0, 1)
        self.new_names_table = PreviewTableWidget(0, 1)
        self.icon_table = QTableWidget(0, 1)  # Icon table doesn't need intelligent resizing

        # Set object names for debugging
        self.old_names_table.setObjectName("oldNamesTable")
        self.new_names_table.setObjectName("newNamesTable")
        self.icon_table.setObjectName("iconTable")

        # Configure preview tables - make them non-interactive (no hover/select)
        for table in [self.old_names_table, self.new_names_table]:
            table.setAlternatingRowColors(True)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.NoSelection)  # No selection allowed
            table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # type: ignore[attr-defined]
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # type: ignore[attr-defined]
            table.setWordWrap(False)
            table.setShowGrid(False)
            table.verticalHeader().setVisible(False)  # type: ignore
            table.horizontalHeader().setVisible(False)  # type: ignore
            table.setMouseTracking(False)  # Disable mouse tracking to prevent hover
            # Set row height from theme manager
            from oncutf.core.theme_manager import get_theme_manager

            theme = get_theme_manager()
            table.verticalHeader().setDefaultSectionSize(theme.get_constant("table_row_height"))  # type: ignore
            # Set minimum height for proper placeholder centering
            table.setMinimumHeight(200)
            # Reduce flickering during updates
            table.setUpdatesEnabled(True)
            table.viewport().setUpdatesEnabled(True)  # type: ignore
            # Disable hover highlighting
            table.setStyleSheet("QTableWidget::item:hover { background-color: transparent; }")

        # Configure icon table
        self.icon_table.setFixedWidth(24)
        self.icon_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.icon_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.icon_table.verticalHeader().setVisible(False)
        self.icon_table.setVerticalHeader(None)
        self.icon_table.setShowGrid(False)
        self.icon_table.horizontalHeader().setVisible(False)
        self.icon_table.setHorizontalHeader(None)
        self.icon_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.icon_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.icon_table.setShowGrid(False)
        self.icon_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        # Set background color to match main application
        bg_color = get_theme_manager().get_color("button_disabled_bg")
        self.icon_table.setStyleSheet(f"background-color: {bg_color};")
        # Use same row height from theme manager
        from oncutf.core.theme_manager import get_theme_manager

        theme = get_theme_manager()
        self.icon_table.verticalHeader().setDefaultSectionSize(
            theme.get_constant("table_row_height")
        )

        tables_layout.addWidget(self.old_names_table)
        tables_layout.addWidget(self.new_names_table)
        tables_layout.addWidget(self.icon_table)

        layout.addLayout(tables_layout)

    def _setup_placeholders(self):
        """Setup placeholder helpers for the preview tables."""
        self.old_names_placeholder_helper = create_placeholder_helper(
            self.old_names_table, "preview_old", icon_size=self.PLACEHOLDER_SIZE
        )
        self.new_names_placeholder_helper = create_placeholder_helper(
            self.new_names_table, "preview_new", icon_size=self.PLACEHOLDER_SIZE
        )

    def _setup_signals(self):
        """Setup signal connections for table interactions."""
        # Connect table resize events for intelligent scrollbar management
        self.old_names_table.resized.connect(self._handle_table_resize)
        self.new_names_table.resized.connect(self._handle_table_resize)

        # Synchronize scrolling between tables
        self.old_names_table.verticalScrollBar().valueChanged.connect(
            self.new_names_table.verticalScrollBar().setValue
        )
        self.new_names_table.verticalScrollBar().valueChanged.connect(
            self.old_names_table.verticalScrollBar().setValue
        )
        self.old_names_table.verticalScrollBar().valueChanged.connect(
            self.icon_table.verticalScrollBar().setValue
        )

    def _setup_shortcuts(self):
        """Setup local keyboard shortcuts for preview tables."""
        from oncutf.core.pyqt_imports import QKeySequence, QShortcut

        # F5: Refresh preview (recalculate from current selection)
        # F5 refresh shortcut for preview tables
        self._refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        self._refresh_shortcut.activated.connect(self._on_refresh_shortcut_pressed)
        logger.debug(
            "[PreviewTablesView] Local shortcuts setup: F5=refresh", extra={"dev_only": True}
        )

    def _on_refresh_requested(self):
        """Handle F5 refresh request by emitting signal to parent."""
        logger.info("[PreviewTablesView] F5 pressed - requesting preview refresh")
        self.refresh_requested.emit()

    def _on_refresh_shortcut_pressed(self) -> None:
        """Handle F5 shortcut press - refresh preview with status message.
        """
        from oncutf.utils.cursor_helper import wait_cursor

        logger.info("[PreviewTables] F5 pressed - refreshing preview")

        with wait_cursor():
            self._on_refresh_requested()

            # Show status message if parent window has status manager
            if hasattr(self, "parent") and callable(self.parent):
                parent = self.parent()
                if parent and hasattr(parent, "status_manager"):
                    parent.status_manager.set_file_operation_status(
                        "Preview tables refreshed", success=True, auto_reset=True
                    )

    def _set_placeholders_visible(self, visible: bool, defer_width_adjustment: bool = False):
        """Show or hide preview table placeholders using the unified helper."""
        logger.debug(
            "[PreviewTablesView] Setting placeholders visible: %s",
            visible,
            extra={"dev_only": True},
        )
        if visible:
            self.old_names_placeholder_helper.show()
            self.new_names_placeholder_helper.show()
            # Disable scrollbars and interactions when showing placeholders
            for table in [self.old_names_table, self.new_names_table]:
                table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                table.setEnabled(False)
            self.icon_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.icon_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            logger.debug(
                "[PreviewTablesView] Placeholders enabled - tables disabled",
                extra={"dev_only": True},
            )
            if hasattr(self, "_placeholders_ready") and self._placeholders_ready:
                schedule_ui_update(self._handle_table_resize, 5)
            else:
                self._handle_table_resize()
        else:
            self.old_names_placeholder_helper.hide()
            self.new_names_placeholder_helper.hide()
            for table in [self.old_names_table, self.new_names_table]:
                table.setEnabled(True)
            if not defer_width_adjustment:
                for table in [self.old_names_table, self.new_names_table]:
                    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                    table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                self._adjust_table_widths()
            logger.debug(
                "[PreviewTablesView] Placeholders disabled - tables enabled %s",
                "(deferred)" if defer_width_adjustment else "(immediate)",
                extra={"dev_only": True},
            )

    def _finalize_scrollbar_setup(self):
        """Complete the scrollbar setup after content has been added to prevent flickering."""
        # Temporarily disable updates to prevent flickering during multiple changes
        for table in [self.old_names_table, self.new_names_table, self.icon_table]:
            table.setUpdatesEnabled(False)

        try:
            # Re-enable intelligent scrollbars
            for table in [self.old_names_table, self.new_names_table]:
                table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

            # Update column widths for intelligent horizontal scrolling
            self._adjust_table_widths()

        finally:
            # Re-enable updates with a single batch refresh
            for table in [self.old_names_table, self.new_names_table, self.icon_table]:
                table.setUpdatesEnabled(True)

            # Force a single coordinated update for all tables
            self.old_names_table.viewport().update()
            self.new_names_table.viewport().update()
            self.icon_table.viewport().update()

        logger.debug("[PreviewTablesView] Scrollbar setup finalized", extra={"dev_only": True})

    def _adjust_table_widths(self):
        """Intelligently adjust preview table column widths based on content length."""
        font_metrics = self.fontMetrics()

        for table in [self.old_names_table, self.new_names_table]:
            if table.rowCount() == 0:
                continue

            viewport_width = table.viewport().width()
            if viewport_width <= 50:  # Skip if too small
                continue

            header = table.horizontalHeader()
            if not header:
                continue

            # First, set to ResizeToContents to get natural width
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            natural_width = table.columnWidth(0)

            # Get the actual content width by measuring text
            max_content_width = 0
            for row in range(table.rowCount()):
                item = table.item(row, 0)
                if item and item.text():
                    text_width = font_metrics.horizontalAdvance(item.text())
                    max_content_width = max(max_content_width, text_width)

            # Use the larger of natural width or measured content width, with padding
            content_width = max(natural_width, max_content_width + 30)  # 30px padding

            # Decide: expand to fill viewport or keep content width for scrolling
            if content_width < viewport_width:
                # Expand to fill viewport (prevents gaps in alternating colors)
                target_width = viewport_width - 5  # Small margin for scrollbar space
                header.setSectionResizeMode(0, QHeaderView.Fixed)
                table.setColumnWidth(0, target_width)
                logger.debug(
                    "[PreviewTablesView] %s expanded: %dpx -> %dpx",
                    table.objectName() or "Unknown",
                    content_width,
                    target_width,
                    extra={"dev_only": True},
                )
            else:
                # Keep content width (allows horizontal scrolling when needed)
                header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
                logger.debug(
                    "[PreviewTablesView] %s content width: %dpx (viewport: %dpx) - scrolling enabled",
                    table.objectName() or "Unknown",
                    content_width,
                    viewport_width,
                    extra={"dev_only": True},
                )

    def _handle_table_resize(self):
        """Handle resize events for preview tables to update placeholder positions and column widths."""
        if self.old_names_placeholder_helper.is_visible():
            self.old_names_placeholder_helper.update_position()
        if self.new_names_placeholder_helper.is_visible():
            self.new_names_placeholder_helper.update_position()
        # Update column widths if tables are active (not in placeholder mode)
        if not self.old_names_placeholder_helper.is_visible():
            self._adjust_table_widths()

    def update_from_pairs(
        self, name_pairs: list[tuple[str, str]], _preview_icons: dict, icon_paths: dict
    ):
        """Update preview tables with name pairs and status validation with performance optimizations."""
        # Performance optimization: Disable all updates at once
        self.setUpdatesEnabled(False)

        try:
            # Clear tables efficiently
            self.old_names_table.setRowCount(0)
            self.new_names_table.setRowCount(0)
            self.icon_table.setRowCount(0)

            if not name_pairs:
                self._set_placeholders_visible(True)
                self.status_updated.emit("No files selected.")
                return

            # Hide placeholders
            self._set_placeholders_visible(False, defer_width_adjustment=True)

            # Performance optimization: Precompute duplicates in one pass
            seen, duplicates = set(), set()
            for _, new_name in name_pairs:
                if new_name in seen:
                    duplicates.add(new_name)
                else:
                    seen.add(new_name)

            # Performance optimization: Batch process name pairs
            stats = {"unchanged": 0, "invalid": 0, "duplicate": 0, "valid": 0}
            self._process_name_pairs_batch(
                name_pairs, duplicates, stats, _preview_icons, icon_paths
            )

            # Update status
            self._update_status_summary(stats, icon_paths)

            # Setup scrollbars with delay
            schedule_scroll_adjust(self._finalize_scrollbar_setup, 15)

        finally:
            # Re-enable updates
            self.setUpdatesEnabled(True)

    def _process_name_pairs_batch(
        self,
        name_pairs: list[tuple[str, str]],
        duplicates: set,
        stats: dict,
        preview_icons: dict,
        icon_paths: dict,
    ):
        """Process name pairs in batches for better performance."""
        # Pre-allocate table rows
        row_count = len(name_pairs)
        self.old_names_table.setRowCount(row_count)
        self.new_names_table.setRowCount(row_count)
        self.icon_table.setRowCount(row_count)

        # Process in batches
        batch_size = 50
        for batch_start in range(0, row_count, batch_size):
            batch_end = min(batch_start + batch_size, row_count)
            self._process_name_pairs_batch_range(
                name_pairs[batch_start:batch_end],
                duplicates,
                stats,
                preview_icons,
                batch_start,
                icon_paths,
            )

    def _process_name_pairs_batch_range(
        self,
        name_pairs_batch: list[tuple[str, str]],
        duplicates: set,
        stats: dict,
        _preview_icons: dict,
        start_row: int,
        icon_paths: dict,
    ):
        """Process a batch of name pairs.

        The icon_path is the path to the image file (icon) that appears next to the new filename in the preview table.
        Each status (valid, invalid, unchanged, duplicate) has its own icon, e.g. assets/valid.png, assets/invalid.png etc.
        """
        import os

        for i, (old_name, new_name) in enumerate(name_pairs_batch):
            row = start_row + i

            # Set old name
            self.old_names_table.setItem(row, 0, QTableWidgetItem(old_name))

            # Set new name
            new_name_item = QTableWidgetItem(new_name)
            self.new_names_table.setItem(row, 0, new_name_item)

            # Determine status and update stats
            if old_name == new_name:
                status = "unchanged"
                icon_path = icon_paths.get("unchanged", "")
                stats["unchanged"] += 1
            elif new_name in duplicates:
                status = "duplicate"
                icon_path = icon_paths.get("duplicate", "")
                stats["duplicate"] += 1
            else:
                # Check if filename is valid
                try:
                    from oncutf.utils.validate_filename_text import is_valid_filename_text

                    basename, _ = os.path.splitext(new_name)
                    if is_valid_filename_text(basename):
                        status = "valid"
                        icon_path = icon_paths.get("valid", "")
                        stats["valid"] += 1
                    else:
                        status = "invalid"
                        icon_path = icon_paths.get("invalid", "")
                        stats["invalid"] += 1
                except ImportError:
                    status = "valid"
                    icon_path = icon_paths.get("valid", "")
                    stats["valid"] += 1

            # Set icon
            icon_item = QTableWidgetItem()
            if icon_path and os.path.exists(icon_path):
                icon_item.setIcon(QIcon(icon_path))
            self.icon_table.setItem(row, 0, icon_item)

            # Set tooltip for new name
            if status != "valid":
                tooltip = self._get_status_tooltip(status, new_name)
                tooltip_type = TooltipType.ERROR if status == "invalid" else TooltipType.WARNING
                TooltipHelper.setup_item_tooltip(
                    self.new_names_table, new_name_item, tooltip, tooltip_type
                )

    def _get_status_tooltip(self, status: str, new_name: str) -> str:
        """Get tooltip text for a given status."""
        mapping = {
            "duplicate": f"Duplicate filename: {new_name}",
            "invalid": f"Invalid filename: {new_name}",
            "unchanged": f"No change: {new_name}",
            "valid": f"Valid filename: {new_name}",
        }
        return mapping.get(status, f"Valid filename: {new_name}")

    def _determine_rename_status(
        self, old_name: str, new_name: str, duplicates: set
    ) -> tuple[str, str]:
        """Determine rename status and tooltip for a name pair."""
        if old_name == new_name:
            return "unchanged", "Unchanged filename"

        if is_validation_error_marker(new_name):
            return "invalid", get_validation_error_message(old_name)

        import os

        from oncutf.utils.filename_validator import validate_filename_part

        basename = os.path.splitext(new_name)[0]
        is_valid, _ = validate_filename_part(basename)

        if not is_valid:
            return "invalid", "Invalid filename"
        elif new_name in duplicates:
            return "duplicate", "Duplicate name"
        else:
            return "valid", "Ready to rename"

    def _update_status_summary(self, stats: dict, icon_paths: dict) -> None:
        """Update status summary with statistics."""
        from oncutf.config import PREVIEW_INDICATOR_SIZE

        # Get icon size from config
        icon_width, icon_height = PREVIEW_INDICATOR_SIZE

        # Get muted text color from theme
        muted_color = get_theme_manager().get_color("text_muted")

        status_msg = (
            f"<img src='{icon_paths['valid']}' width='{icon_width}' height='{icon_height}' style='vertical-align: middle';/>"
            f"<span style='color:{muted_color};'> Valid: {stats['valid']}</span>&nbsp;&nbsp;&nbsp;"
            f"<img src='{icon_paths['unchanged']}' width='{icon_width}' height='{icon_height}' style='vertical-align: middle';/>"
            f"<span style='color:{muted_color};'> Unchanged: {stats['unchanged']}</span>&nbsp;&nbsp;&nbsp;"
            f"<img src='{icon_paths['invalid']}' width='{icon_width}' height='{icon_height}' style='vertical-align: middle';/>"
            f"<span style='color:{muted_color};'> Invalid: {stats['invalid']}</span>&nbsp;&nbsp;&nbsp;"
            f"<img src='{icon_paths['duplicate']}' width='{icon_width}' height='{icon_height}' style='vertical-align: middle';/>"
            f"<span style='color:{muted_color};'> Duplicates: {stats['duplicate']}</span>"
        )
        self.status_updated.emit(status_msg)

    def clear_tables(self):
        """Clear all tables and show placeholders."""
        # Disable updates to prevent flickering during clearing
        self.old_names_table.setUpdatesEnabled(False)
        self.new_names_table.setUpdatesEnabled(False)
        self.icon_table.setUpdatesEnabled(False)

        try:
            self.old_names_table.setRowCount(0)
            self.new_names_table.setRowCount(0)
            self.icon_table.setRowCount(0)
            self._set_placeholders_visible(True)
        finally:
            # Re-enable updates after clearing is complete
            self.old_names_table.setUpdatesEnabled(True)
            self.new_names_table.setUpdatesEnabled(True)
            self.icon_table.setUpdatesEnabled(True)

    def handle_splitter_moved(self, _pos=None, _index=None):
        """Handle parent splitter movement to adjust table widths."""
        self._handle_table_resize()

    def _initialize_placeholders(self):
        """Initialize placeholders after they are ready to be shown."""
        logger.debug("[PreviewTablesView] Initializing placeholders", extra={"dev_only": True})
        self._set_placeholders_visible(True)
        self._placeholders_ready = True
        logger.debug(
            "[PreviewTablesView] Placeholders initialized and shown", extra={"dev_only": True}
        )
