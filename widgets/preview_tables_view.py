"""
preview_tables_view.py

Author: Michael Economou
Date: 2025-06-05

Implements a view that manages the preview tables for old/new filenames
with intelligent placeholder management and scrollbar optimization.

Features:
- Placeholder management (show when empty, hide when populated)
- Intelligent horizontal scrolling (expand to fill or enable scrollbar)
- Synchronized scrolling between old/new name tables
- Status icon display for rename validation
- Custom table widgets with resize signal handling
"""

from pathlib import Path
from typing import Optional, Tuple

from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from utils.logger_factory import get_cached_logger
from utils.timer_manager import schedule_ui_update, schedule_scroll_adjust

logger = get_cached_logger(__name__)


class PreviewTableWidget(QTableWidget):
    """
    Custom QTableWidget for preview tables with intelligent scrollbar management.
    Emits resize signal when the widget is resized to update placeholders and column widths.
    """
    resized = pyqtSignal()  # Emitted when table is resized

    def __init__(self, rows=0, columns=1, parent=None):
        super().__init__(rows, columns, parent)

    def resizeEvent(self, event):
        """Override to emit resize signal for intelligent column width adjustments."""
        super().resizeEvent(event)
        # Emit signal with small delay to ensure layout is stable
        schedule_ui_update(self.resized.emit, 10)


class PreviewTablesView(QWidget):
    """
    View that manages the preview tables for old/new filenames.

    Features:
    - Intelligent placeholder management
    - Synchronized scrolling between tables
    - Intelligent horizontal scrollbar management
    - Status icon display for rename validation

    Signals:
        status_updated: Emitted when status message should be updated
    """

    status_updated = pyqtSignal(str)  # Emitted with HTML status message

    def __init__(self, parent=None):
        super().__init__(parent)

        # Constants
        self.PLACEHOLDER_SIZE = 120

        # Initialize components
        self._setup_ui()
        self._setup_placeholders()
        self._setup_signals()

        # Don't show placeholders initially - they will be shown after proper positioning
        # This prevents the "jump" effect where placeholders appear top-left then move to center
        self._placeholders_ready = False

        # Schedule initial placeholder setup with positioning
        schedule_ui_update(self._initialize_placeholders, 10)

        logger.debug("[PreviewTablesView] Initialized with intelligent scrolling")

    def _setup_ui(self):
        """Setup the UI layout and tables."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Labels
        labels_layout = QHBoxLayout()
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

        # Configure preview tables
        for table in [self.old_names_table, self.new_names_table]:
            table.setAlternatingRowColors(True)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.SingleSelection)
            table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            table.setWordWrap(False)
            table.setShowGrid(False)
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setVisible(False)
            table.setFocusPolicy(Qt.NoFocus)
            # Set same row height as icon table
            table.verticalHeader().setDefaultSectionSize(22)
            # Reduce flickering during updates
            table.setUpdatesEnabled(True)
            table.viewport().setUpdatesEnabled(True)

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
        self.icon_table.setStyleSheet("background-color: #212121;")
        self.icon_table.verticalHeader().setDefaultSectionSize(22)

        tables_layout.addWidget(self.old_names_table)
        tables_layout.addWidget(self.new_names_table)
        tables_layout.addWidget(self.icon_table)

        layout.addLayout(tables_layout)

    def _setup_placeholders(self):
        """Setup placeholder labels for the preview tables."""
        # Setup old names placeholder
        self.old_names_placeholder = QLabel(self.old_names_table.viewport())
        self.old_names_placeholder.setAlignment(Qt.AlignCenter)
        self.old_names_placeholder.setVisible(False)

        old_icon_path = Path(__file__).parent.parent / "resources/images/old_names-preview_placeholder.png"
        self.old_names_placeholder_icon = QPixmap(str(old_icon_path))

        if not self.old_names_placeholder_icon.isNull():
            scaled_old = self.old_names_placeholder_icon.scaled(
                self.PLACEHOLDER_SIZE, self.PLACEHOLDER_SIZE,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.old_names_placeholder.setPixmap(scaled_old)
            # Store the actual scaled size for accurate centering
            self.old_placeholder_actual_size = scaled_old.size()
        else:
            logger.warning("Old names placeholder icon could not be loaded.")
            self.old_placeholder_actual_size = None

        # Setup new names placeholder
        self.new_names_placeholder = QLabel(self.new_names_table.viewport())
        self.new_names_placeholder.setAlignment(Qt.AlignCenter)
        self.new_names_placeholder.setVisible(False)

        new_icon_path = Path(__file__).parent.parent / "resources/images/new_names-preview_placeholder.png"
        self.new_names_placeholder_icon = QPixmap(str(new_icon_path))

        if not self.new_names_placeholder_icon.isNull():
            scaled_new = self.new_names_placeholder_icon.scaled(
                self.PLACEHOLDER_SIZE, self.PLACEHOLDER_SIZE,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.new_names_placeholder.setPixmap(scaled_new)
            # Store the actual scaled size for accurate centering
            self.new_placeholder_actual_size = scaled_new.size()
        else:
            logger.warning("New names placeholder icon could not be loaded.")
            self.new_placeholder_actual_size = None

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

    def _set_placeholders_visible(self, visible: bool, defer_width_adjustment: bool = False):
        """Show or hide preview table placeholders and configure table states accordingly."""
        if visible:
            # Show placeholders
            if hasattr(self, 'old_names_placeholder'):
                self.old_names_placeholder.raise_()
                self.old_names_placeholder.show()

            if hasattr(self, 'new_names_placeholder'):
                self.new_names_placeholder.raise_()
                self.new_names_placeholder.show()

            # Disable scrollbars and interactions when showing placeholders
            for table in [self.old_names_table, self.new_names_table]:
                table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                table.setEnabled(False)  # Disable all interactions

            # Keep icon table minimal
            self.icon_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.icon_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

            logger.debug("[PreviewTablesView] Placeholders enabled - tables disabled")

            # Center placeholders immediately if they are ready, otherwise they will be centered during initialization
            if hasattr(self, '_placeholders_ready') and self._placeholders_ready:
                schedule_ui_update(self._handle_table_resize, 5)
            else:
                # Do immediate centering for initialization
                self._handle_table_resize()

        else:
            # Hide placeholders
            if hasattr(self, 'old_names_placeholder'):
                self.old_names_placeholder.hide()

            if hasattr(self, 'new_names_placeholder'):
                self.new_names_placeholder.hide()

            # Re-enable interactions first
            for table in [self.old_names_table, self.new_names_table]:
                table.setEnabled(True)  # Re-enable interactions

            # Defer scrollbar policy changes to avoid flickering when content is about to be added
            if not defer_width_adjustment:
                # Re-enable intelligent scrollbars immediately
                for table in [self.old_names_table, self.new_names_table]:
                    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                    table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

                # Update column widths for intelligent horizontal scrolling
                self._adjust_table_widths()

            logger.debug(f"[PreviewTablesView] Placeholders disabled - tables enabled {'(deferred)' if defer_width_adjustment else '(immediate)'}")

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

        logger.debug("[PreviewTablesView] Scrollbar setup finalized")

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
                logger.debug(f"[PreviewTablesView] {table.objectName() or 'Unknown'} expanded: {content_width}px → {target_width}px")
            else:
                # Keep content width (allows horizontal scrolling when needed)
                header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
                logger.debug(f"[PreviewTablesView] {table.objectName() or 'Unknown'} content width: {content_width}px (viewport: {viewport_width}px) - scrolling enabled")

    def _handle_table_resize(self):
        """Handle resize events for preview tables to update placeholder positions and column widths."""
        # Update placeholder positions - center them properly in viewport (only if visible)
        if hasattr(self, 'old_names_placeholder') and self.old_names_placeholder.isVisible():
            viewport_size = self.old_names_table.viewport().size()

            # Use the stored scaled size for accurate centering
            if hasattr(self, 'old_placeholder_actual_size') and self.old_placeholder_actual_size:
                placeholder_width = self.old_placeholder_actual_size.width()
                placeholder_height = self.old_placeholder_actual_size.height()
            else:
                # Fallback to placeholder size if no stored size
                placeholder_width = self.PLACEHOLDER_SIZE
                placeholder_height = self.PLACEHOLDER_SIZE

            # Calculate center position
            x = max(0, (viewport_size.width() - placeholder_width) // 2)
            y = max(0, (viewport_size.height() - placeholder_height) // 2)

            self.old_names_placeholder.resize(placeholder_width, placeholder_height)
            self.old_names_placeholder.move(x, y)

        if hasattr(self, 'new_names_placeholder') and self.new_names_placeholder.isVisible():
            viewport_size = self.new_names_table.viewport().size()

            # Use the stored scaled size for accurate centering
            if hasattr(self, 'new_placeholder_actual_size') and self.new_placeholder_actual_size:
                placeholder_width = self.new_placeholder_actual_size.width()
                placeholder_height = self.new_placeholder_actual_size.height()
            else:
                # Fallback to placeholder size if no stored size
                placeholder_width = self.PLACEHOLDER_SIZE
                placeholder_height = self.PLACEHOLDER_SIZE

            # Calculate center position
            x = max(0, (viewport_size.width() - placeholder_width) // 2)
            y = max(0, (viewport_size.height() - placeholder_height) // 2)

            self.new_names_placeholder.resize(placeholder_width, placeholder_height)
            self.new_names_placeholder.move(x, y)

        # Update column widths if tables are active (not in placeholder mode)
        if (hasattr(self, 'old_names_placeholder') and
            not self.old_names_placeholder.isVisible()):
            self._adjust_table_widths()

    def update_from_pairs(self, name_pairs: list[Tuple[str, str]], preview_icons: dict, icon_paths: dict, validator):
        """
        Update preview tables with name pairs and status validation.

        Args:
            name_pairs: List of (old_name, new_name) tuples
            preview_icons: Dictionary of status icons
            icon_paths: Dictionary of icon file paths for HTML rendering
            validator: FilenameValidator instance for validation
        """
        # Disable updates to prevent flickering during batch operations
        self.old_names_table.setUpdatesEnabled(False)
        self.new_names_table.setUpdatesEnabled(False)
        self.icon_table.setUpdatesEnabled(False)

        try:
            # Clear all preview tables before updating
            self.old_names_table.setRowCount(0)
            self.new_names_table.setRowCount(0)
            self.icon_table.setRowCount(0)

            if not name_pairs:
                # Show placeholders when no content
                self._set_placeholders_visible(True)
                self.status_updated.emit("No files selected.")
                return

            # Hide placeholders when we have content (defer scrollbar setup to avoid flickering)
            self._set_placeholders_visible(False, defer_width_adjustment=True)
            logger.debug(f"[PreviewTablesView] Processing {len(name_pairs)} name pairs - scrollbar setup deferred")

            # Precompute duplicates
            seen, duplicates = set(), set()
            for _, new_name in name_pairs:
                if new_name in seen:
                    duplicates.add(new_name)
                else:
                    seen.add(new_name)

            # Initialize status counters
            stats = {"unchanged": 0, "invalid": 0, "duplicate": 0, "valid": 0}

            for row, (old_name, new_name) in enumerate(name_pairs):
                self.old_names_table.insertRow(row)
                self.new_names_table.insertRow(row)
                self.icon_table.insertRow(row)

                # Create table items
                old_item = QTableWidgetItem(old_name)
                new_item = QTableWidgetItem(new_name)

                # Determine rename status
                if old_name == new_name:
                    status = "unchanged"
                    tooltip = "Unchanged filename"
                else:
                    is_valid, _ = validator.is_valid_filename(new_name)
                    if not is_valid:
                        status = "invalid"
                        tooltip = "Invalid filename"
                    elif new_name in duplicates:
                        status = "duplicate"
                        tooltip = "Duplicate name"
                    else:
                        status = "valid"
                        tooltip = "Ready to rename"

                # Update status counts
                stats[status] += 1

                # Prepare status icon
                icon_item = QTableWidgetItem()
                icon = preview_icons.get(status)
                if icon:
                    icon_item.setIcon(icon)
                icon_item.setToolTip(tooltip)

                # Insert items into corresponding tables
                self.old_names_table.setItem(row, 0, old_item)
                self.new_names_table.setItem(row, 0, new_item)
                self.icon_table.setItem(row, 0, icon_item)

            # Render bottom status summary (valid, unchanged, invalid, duplicate)
            status_msg = (
                f"<img src='{icon_paths['valid']}' width='14' height='14' style='vertical-align: middle';/>"
                f"<span style='color:#ccc;'> Valid: {stats['valid']}</span>&nbsp;&nbsp;&nbsp;"
                f"<img src='{icon_paths['unchanged']}' width='14' height='14' style='vertical-align: middle';/>"
                f"<span style='color:#ccc;'> Unchanged: {stats['unchanged']}</span>&nbsp;&nbsp;&nbsp;"
                f"<img src='{icon_paths['invalid']}' width='14' height='14' style='vertical-align: middle';/>"
                f"<span style='color:#ccc;'> Invalid: {stats['invalid']}</span>&nbsp;&nbsp;&nbsp;"
                f"<img src='{icon_paths['duplicate']}' width='14' height='14' style='vertical-align: middle';/>"
                f"<span style='color:#ccc;'> Duplicates: {stats['duplicate']}</span>"
            )
            self.status_updated.emit(status_msg)

            # Schedule scrollbar setup
            schedule_scroll_adjust(self._finalize_scrollbar_setup, 15)

        finally:
            # Re-enable updates after all operations are complete
            self.old_names_table.setUpdatesEnabled(True)
            self.new_names_table.setUpdatesEnabled(True)
            self.icon_table.setUpdatesEnabled(True)

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

    def handle_splitter_moved(self):
        """Handle parent splitter movement to adjust table widths."""
        self._handle_table_resize()

    def _initialize_placeholders(self):
        """Initialize placeholders after they are ready to be shown."""
        self._set_placeholders_visible(True)
        self._placeholders_ready = True
        logger.debug("[PreviewTablesView] Placeholders initialized")
