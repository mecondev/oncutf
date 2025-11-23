"""
Module: results_table_dialog.py

Author: Michael Economou
Date: 2025-11-23

Global reusable dialog for displaying tabular results with persistent geometry.

Features:
- QTableView with custom model (not QTableWidget)
- Two-column table with customizable headers
- Proper styling matching file_table_view
- Alternating row colors
- Adjustable column widths (persisted to user config)
- Persistent window geometry
- Min/max height constraints
"""

from pathlib import Path

from config import (
    HASH_LIST_CONTENT_MARGINS,
    HASH_LIST_WINDOW_DEFAULT_HEIGHT,
    HASH_LIST_WINDOW_DEFAULT_WIDTH,
    HASH_LIST_WINDOW_MAX_HEIGHT,
    HASH_LIST_WINDOW_MIN_HEIGHT,
    RESULTS_TABLE_DEFAULT_HEIGHT,
    RESULTS_TABLE_DEFAULT_WIDTH,
    RESULTS_TABLE_LEFT_COLUMN_WIDTH,
    RESULTS_TABLE_MAX_HEIGHT,
    RESULTS_TABLE_MIN_HEIGHT,
    RESULTS_TABLE_MIN_WIDTH,
)
from core.pyqt_imports import (
    QAction,
    QApplication,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    Qt,
    QTableView,
    QVBoxLayout,
)
from models.results_table_model import ResultsTableModel
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ResultsTableDialog(QDialog):
    """
    Global reusable dialog for displaying two-column tabular results using QTableView.

    Features:
    - QTableView with custom ResultsTableModel for full control
    - Customizable column headers
    - Persistent column widths
    - Persistent window geometry
    - Auto-sizing with min/max constraints
    - Proper dark theme styling
    """

    def __init__(
        self,
        parent=None,
        title: str = "Results",
        left_header: str = "Item",
        right_header: str = "Value",
        data: dict | None = None,
        config_key: str = "results_table",
    ):
        """Initialize the results table dialog."""
        super().__init__(parent)
        self.config_key = config_key
        self.left_header = left_header
        self.right_header = right_header
        self.data = data or {}
        self._suspend_column_save = False
        self._columns_changed = False  # Track if user resized columns

        self.setWindowTitle(title)
        self.setModal(True)
        
        # Ensure dialog can receive keyboard events
        self.setFocusPolicy(Qt.StrongFocus)

        # Setup UI
        self._setup_ui()
        self._load_geometry()
        self._populate_data()
        
        # Set focus to dialog after setup
        self.setFocus()

        logger.debug(f"[ResultsTableDialog] Created with {len(self.data)} rows")

    def _setup_ui(self):
        """Setup the dialog UI components."""
        layout = QVBoxLayout(self)

        # Margins
        try:
            margins = HASH_LIST_CONTENT_MARGINS
            layout.setContentsMargins(
                margins.get("left", 8),
                margins.get("top", 8),
                margins.get("right", 8),
                margins.get("bottom", 8),
            )
        except Exception:
            layout.setContentsMargins(12, 12, 12, 12)

        layout.setSpacing(10)

        # Title label
        self.title_label = QLabel(f"{len(self.data)} items")
        self.title_label.setObjectName("title_label")
        layout.addWidget(self.title_label)

        # Create model and table view
        self.model = ResultsTableModel(self.data, parent=self)
        self.model.set_headers(self.left_header, self.right_header)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.NoSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        
        # Install event filter on table to forward Ctrl+T shortcuts to dialog
        self.table.installEventFilter(self)

        # Configure row height from theme engine
        from utils.theme_engine import ThemeEngine
        theme = ThemeEngine()
        row_height = theme.get_constant("table_row_height")
        self.table.verticalHeader().setDefaultSectionSize(row_height)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        # Configure columns
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionsClickable(False)  # Disable click/hover like file_table
        header.setHighlightSections(False)   # Disable hover highlight
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        # Connect header resize signal (batched save on close, not immediate)
        header.sectionResized.connect(self._on_column_resized)

        # Context menu for copying values
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_context_menu)

        # Scrollbars
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Use manual control for horizontal scrollbar to match FileTableView behavior
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        layout.addWidget(self.table)

        # Button bar
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        self.close_button.setObjectName("dialog_action_button")
        # Use theme constant for button height
        from utils.theme_engine import ThemeEngine
        theme = ThemeEngine()
        self.close_button.setFixedHeight(theme.get_constant("button_height"))
        button_layout.addWidget(self.close_button)

        # Export button
        try:
            self.export_button = QPushButton("Export")
            self.export_button.setObjectName("dialog_action_button")
            self.export_button.setFixedHeight(theme.get_constant("button_height"))
            button_layout.insertWidget(button_layout.count() - 1, self.export_button)
        except Exception:
            pass

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # Initial scrollbar update
        self._update_scrollbar_visibility()

    def resizeEvent(self, event):
        """Handle resize events to update scrollbar visibility."""
        super().resizeEvent(event)
        self._update_scrollbar_visibility()

    def _update_scrollbar_visibility(self) -> None:
        """Update scrollbar visibility based on table content and column widths.
        
        Matches behavior of FileTableView to prevent unnecessary scrollbars.
        """
        if not hasattr(self, "table") or not self.table.model():
            return

        # Calculate total column width
        total_width = 0
        header = self.table.horizontalHeader()
        for i in range(header.count()):
            if not header.isSectionHidden(i):
                total_width += self.table.columnWidth(i)

        # Get viewport width
        viewport_width = self.table.viewport().width()

        # Simple logic: show scrollbar if content is wider than viewport
        if total_width > viewport_width:
            self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def _populate_data(self):
        """Populate the table with data."""
        if not self.data:
            return
        self.model.set_data(self.data)

    def _load_geometry(self):
        """Load persistent geometry and column widths from user config."""
        from utils.json_config_manager import get_app_config_manager

        config_manager = get_app_config_manager()
        dialogs_config = config_manager.get_category("dialogs", create_if_not_exists=True)
        
        logger.info(f"[ResultsTableDialog] Loading config for key: {self.config_key}")
        logger.info(f"[ResultsTableDialog] Dialogs config keys: {list(dialogs_config._data.keys()) if hasattr(dialogs_config, '_data') else 'N/A'}")

        # Load window geometry
        geometry_key = f"{self.config_key}_geometry"
        geometry = dialogs_config.get(geometry_key)
        logger.info(f"[ResultsTableDialog] Loaded geometry from '{geometry_key}': {geometry}")
        
        if geometry and len(geometry) == 4:
            try:
                x, y, width, height = geometry
                self.setGeometry(x, y, width, height)
                logger.info(f"[ResultsTableDialog] ✓ Applied geometry: {width}x{height} at ({x}, {y})")

                # Enforce min/max
                if getattr(self, "config_key", "").startswith("hash"):
                    min_h = HASH_LIST_WINDOW_MIN_HEIGHT
                    max_h = HASH_LIST_WINDOW_MAX_HEIGHT
                else:
                    min_h = RESULTS_TABLE_MIN_HEIGHT
                    max_h = RESULTS_TABLE_MAX_HEIGHT

                try:
                    min_w = RESULTS_TABLE_MIN_WIDTH
                except NameError:
                    min_w = 350

                self.setMinimumSize(min_w, min_h)
                self.setMaximumHeight(max_h)
            except Exception as e:
                logger.warning(f"[ResultsTableDialog] Failed to restore geometry: {e}")
                self._set_default_geometry()
        else:
            logger.info(f"[ResultsTableDialog] No saved geometry found (got: {geometry}), using defaults")
            self._set_default_geometry()

        # Load column widths (always, regardless of geometry loading)
        column_widths_key = f"{self.config_key}_column_widths"
        column_widths = dialogs_config.get(column_widths_key)
        logger.info(f"[ResultsTableDialog] Loaded column widths from '{column_widths_key}': {column_widths}")
        
        if column_widths and len(column_widths) == 2:
            try:
                self.table.setColumnWidth(0, column_widths[0])
                logger.info(f"[ResultsTableDialog] ✓ Applied column widths: {column_widths}")
            except Exception as e:
                logger.warning(f"[ResultsTableDialog] Failed to restore column widths: {e}")
                self._set_default_column_widths()
        else:
            logger.info(f"[ResultsTableDialog] No saved column widths found (got: {column_widths}), using defaults")
            self._set_default_column_widths()

    def _set_default_geometry(self):
        """Set default window geometry from config."""
        if getattr(self, "config_key", "").startswith("hash"):
            width = HASH_LIST_WINDOW_DEFAULT_WIDTH
            height = HASH_LIST_WINDOW_DEFAULT_HEIGHT
            min_h = HASH_LIST_WINDOW_MIN_HEIGHT
            max_h = HASH_LIST_WINDOW_MAX_HEIGHT
        else:
            width = RESULTS_TABLE_DEFAULT_WIDTH
            height = RESULTS_TABLE_DEFAULT_HEIGHT
            min_h = RESULTS_TABLE_MIN_HEIGHT
            max_h = RESULTS_TABLE_MAX_HEIGHT

        try:
            min_w = RESULTS_TABLE_MIN_WIDTH
        except NameError:
            min_w = 350

        # Adjust height based on row count
        if self.data:
            row_count = len(self.data)
            estimated_height = 80 + (row_count * 25)
            height = max(min_h, min(estimated_height, max_h))

        self.resize(width, height)
        from contextlib import suppress
        with suppress(Exception):
            self.setMinimumSize(min_w, min_h)

        # Center on parent or screen
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - width) // 2
            y = parent_geo.y() + (parent_geo.height() - height) // 2
            self.move(x, y)

        logger.debug(f"[ResultsTableDialog] Set default geometry: {width}x{height}")

    def _set_default_column_widths(self):
        """Set default column widths from config."""
        left_width = RESULTS_TABLE_LEFT_COLUMN_WIDTH
        self.table.setColumnWidth(0, left_width)
        logger.debug(f"[ResultsTableDialog] Set default column width: {left_width}")

    def _on_column_resized(self, logical_index: int, _old_size: int, new_size: int):
        """Track column resize (save batched on close, not immediate)."""
        if getattr(self, "_suspend_column_save", False):
            return
        # Just mark that columns changed - actual save happens in closeEvent
        self._columns_changed = True
        
        # Update scrollbar visibility
        self._update_scrollbar_visibility()
        
        # Force immediate scrollbar and viewport update
        self.table.updateGeometry()
        self.table.viewport().update()

    def _on_table_context_menu(self, pos):
        """Show context menu for copying values."""
        idx = self.table.indexAt(pos)
        if not idx.isValid():
            return

        row = idx.row()
        col = idx.column()

        # Only copy from right column (value column)
        if col != 1:
            return

        menu = QMenu(self)
        # Apply theme styling
        from utils.theme_engine import ThemeEngine
        theme = ThemeEngine()
        menu.setStyleSheet(theme.get_context_menu_stylesheet())
        
        action_copy = QAction("Copy value", self)

        def do_copy():
            value = self.model.data(self.model.index(row, col), Qt.DisplayRole)
            if value:
                QApplication.clipboard().setText(str(value))

        action_copy.triggered.connect(do_copy)
        menu.addAction(action_copy)
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts (Ctrl+T for auto-fit, Ctrl+Shift+T for reset)."""
        logger.debug(f"[ResultsTableDialog] keyPressEvent: key={event.key()}, modifiers={event.modifiers()}")
        
        # Ctrl+T: Auto-fit columns to content
        if event.key() == Qt.Key_T and event.modifiers() == Qt.ControlModifier:
            logger.debug("[ResultsTableDialog] Ctrl+T pressed - auto-fitting columns")
            self._auto_fit_columns_to_content()
            event.accept()
            return

        # Ctrl+Shift+T: Reset column widths to default
        if event.key() == Qt.Key_T and event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier):
            logger.debug("[ResultsTableDialog] Ctrl+Shift+T pressed - resetting columns")
            self._reset_columns_to_default()
            event.accept()
            return

        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        """Forward keyboard events from table to dialog for shortcuts."""
        if obj == self.table and event.type() == event.KeyPress:
            # Forward Ctrl+T and Ctrl+Shift+T to dialog's keyPressEvent
            if event.key() == Qt.Key_T and (event.modifiers() & Qt.ControlModifier):
                self.keyPressEvent(event)
                if event.isAccepted():
                    return True
        return super().eventFilter(obj, event)

    def _reset_columns_to_default(self):
        """Reset column widths to default values (Ctrl+Shift+T)."""
        self._suspend_column_save = True
        try:
            left_width = RESULTS_TABLE_LEFT_COLUMN_WIDTH
            self.table.setColumnWidth(0, left_width)
            # Right column auto-sizes
            logger.debug(f"[ResultsTableDialog] Reset columns to default: {left_width}")
        finally:
            self._suspend_column_save = False
            # Mark config as dirty to save the new widths
            self._columns_changed = True
            self._update_scrollbar_visibility()

    def _auto_fit_columns_to_content(self):
        """Auto-fit column widths to content (Ctrl+T).
        
        Resizes both columns to fit their content optimally.
        """
        self._suspend_column_save = True
        try:
            # Resize both columns to their content
            self.table.resizeColumnToContents(0)
            self.table.resizeColumnToContents(1)
            
            # Get the new widths
            left_width = self.table.columnWidth(0)
            right_width = self.table.columnWidth(1)
            
            logger.info(f"[ResultsTableDialog] Auto-fit columns: [{left_width}, {right_width}]")
        finally:
            self._suspend_column_save = False
            # Mark config as dirty to save the new widths
            self._columns_changed = True
            self._update_scrollbar_visibility()

    def closeEvent(self, event):
        """Save geometry and column widths when dialog closes (single batch save)."""
        self._save_config()
        super().closeEvent(event)

    def accept(self):
        """Override accept() to save config before closing (called by Close button)."""
        self._save_config()
        super().accept()

    def _save_config(self):
        """Save dialog geometry and column widths to config."""
        from utils.json_config_manager import get_app_config_manager

        config_manager = get_app_config_manager()
        dialogs_config = config_manager.get_category("dialogs", create_if_not_exists=True)
        
        logger.info(f"[ResultsTableDialog] Saving config for key: {self.config_key}")
        
        # Save geometry
        geometry_key = f"{self.config_key}_geometry"
        geo = self.geometry()
        geometry = [geo.x(), geo.y(), geo.width(), geo.height()]
        dialogs_config.set(geometry_key, geometry)
        logger.info(f"[ResultsTableDialog] Set '{geometry_key}' = {geometry}")
        
        # Save column widths
        column_widths_key = f"{self.config_key}_column_widths"
        left_width = self.table.columnWidth(0)
        right_width = self.table.columnWidth(1)
        dialogs_config.set(column_widths_key, [left_width, right_width])
        logger.info(f"[ResultsTableDialog] Set '{column_widths_key}' = [{left_width}, {right_width}]")
        
        # Single save for both
        config_manager.save_immediate()
        logger.info(f"[ResultsTableDialog] ✓ Config saved to disk")
        
        # Verify it was saved
        verify_geo = dialogs_config.get(geometry_key)
        verify_cols = dialogs_config.get(column_widths_key)
        logger.info(f"[ResultsTableDialog] Verification - geometry: {verify_geo}, columns: {verify_cols}")

    @classmethod
    def show_hash_results(
        cls,
        parent,
        hash_results: dict,
        was_cancelled: bool = False,
    ):
        """Factory method to show hash/checksum results."""
        if not hash_results:
            return

        # Extract filenames from full paths
        display_data = {}
        for file_path, hash_value in hash_results.items():
            filename = Path(file_path).name
            display_data[filename] = hash_value

        title_suffix = " (Partial)" if was_cancelled else ""
        title = f"Checksum Results{title_suffix}"

        dialog = cls(
            parent=parent,
            title=title,
            left_header="Filename",
            right_header="Checksum",
            data=display_data,
            config_key="hash_list",
        )
        dialog.exec_()
