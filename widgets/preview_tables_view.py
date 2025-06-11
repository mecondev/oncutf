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

from utils.logger_helper import get_logger

logger = get_logger(__name__)


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
        QTimer.singleShot(10, self.resized.emit)


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

        # Show placeholders initially
        self._set_placeholders_visible(True)

        logger.debug("[PreviewTablesView] Initialized with intelligent scrolling")

    def _setup_ui(self):
        """Setup the UI layout and tables."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Labels
        labels_layout = QHBoxLayout()
        self.old_label = QLabel("Old file(s) name(s)")
        self.new_label = QLabel("New file(s) name(s)")

        labels_layout.addWidget(self.old_label)
        labels_layout.addWidget(self.new_label)
        labels_layout.addWidget(QLabel(" "))  # Space for icon column

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
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
            table.setWordWrap(False)
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.setSelectionMode(QAbstractItemView.NoSelection)
            table.verticalHeader().setVisible(False)
            table.setVerticalHeader(None)
            table.horizontalHeader().setVisible(False)
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
            table.setAlternatingRowColors(True)
            table.verticalHeader().setDefaultSectionSize(22)
            # Disable drag & drop functionality
            table.setDragEnabled(False)
            table.setAcceptDrops(False)
            table.setDragDropMode(QAbstractItemView.NoDragDrop)

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
        else:
            logger.warning("Old names placeholder icon could not be loaded.")

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
        else:
            logger.warning("New names placeholder icon could not be loaded.")

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

            logger.debug("[PreviewTablesView] Placeholders enabled - tables disabled", extra={"dev_only": True})

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

            logger.debug(f"[PreviewTablesView] Placeholders disabled - tables enabled {'(deferred)' if defer_width_adjustment else '(immediate)'}", extra={"dev_only": True})

    def _finalize_scrollbar_setup(self):
        """Complete the scrollbar setup after content has been added to prevent flickering."""
        # Temporarily disable updates to prevent flickering during multiple changes
        for table in [self.old_names_table, self.new_names_table]:
            table.setUpdatesEnabled(False)

        try:
            # Re-enable intelligent scrollbars
            for table in [self.old_names_table, self.new_names_table]:
                table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

            # Update column widths for intelligent horizontal scrolling
            self._adjust_table_widths()

        finally:
            # Re-enable updates and force a single refresh
            for table in [self.old_names_table, self.new_names_table]:
                table.setUpdatesEnabled(True)
                table.viewport().update()

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
                logger.debug(f"[PreviewTablesView] {table.objectName() or 'Unknown'} expanded: {content_width}px → {target_width}px", extra={"dev_only": True})
            else:
                # Keep content width (allows horizontal scrolling when needed)
                header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
                logger.debug(f"[PreviewTablesView] {table.objectName() or 'Unknown'} content width: {content_width}px (viewport: {viewport_width}px) - scrolling enabled", extra={"dev_only": True})

    def _handle_table_resize(self):
        """Handle resize events for preview tables to update placeholder positions and column widths."""
        # Update placeholder positions
        if hasattr(self, 'old_names_placeholder'):
            self.old_names_placeholder.resize(self.old_names_table.viewport().size())
            self.old_names_placeholder.move(0, 0)

        if hasattr(self, 'new_names_placeholder'):
            self.new_names_placeholder.resize(self.new_names_table.viewport().size())
            self.new_names_placeholder.move(0, 0)

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
        logger.debug(f"[PreviewTablesView] Processing {len(name_pairs)} name pairs - scrollbar setup deferred", extra={"dev_only": True})

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

        # Finalize scrollbar setup after all content is loaded to prevent flickering
        QTimer.singleShot(15, self._finalize_scrollbar_setup)

    def clear_tables(self):
        """Clear all tables and show placeholders."""
        self.old_names_table.setRowCount(0)
        self.new_names_table.setRowCount(0)
        self.icon_table.setRowCount(0)
        self._set_placeholders_visible(True)

    def handle_splitter_moved(self):
        """Handle parent splitter movement to adjust table widths."""
        self._handle_table_resize()
