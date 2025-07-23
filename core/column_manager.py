"""
Module: column_manager.py

Author: Michael Economou
Date: 2025-06-10

Column Management System for OnCutF Application
This module provides centralized column management for all table views in the application,
including the main file table view, metadata tree view, and preview tables.
Key Features:
- Intelligent column width calculation based on content and available space
- Adaptive column sizing for different screen sizes and window states
- Column persistence and restoration from configuration
- Dynamic column adjustment on splitter movement and window resize
- Support for both fixed and interactive column resize modes
- Font-aware column sizing with proper text metrics
- Scrollbar-aware space calculation
- User preference tracking and manual resize detection
Classes:
ColumnManager: Main column management class
ColumnType: Enum for different column types
ColumnConfig: Configuration class for column settings
ColumnState: State tracking for column management
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Union

from core.config_imports import FILE_TABLE_COLUMN_CONFIG, METADATA_TREE_COLUMN_WIDTHS
from core.pyqt_imports import QFontMetrics, QHeaderView, QTableView, QTreeView, QWidget
from utils.logger_helper import get_cached_logger

logger = get_cached_logger(__name__)


class ColumnType(Enum):
    """Enum for different column types and their resize behavior."""

    FIXED = "fixed"  # Fixed width, cannot be resized
    INTERACTIVE = "interactive"  # User can resize, but has minimum width
    STRETCH = "stretch"  # Stretches to fill available space
    CONTENT_BASED = "content_based"  # Width based on content length


@dataclass
class ColumnConfig:
    """Configuration class for individual column settings."""

    column_index: int
    column_type: ColumnType
    min_width: int
    max_width: Optional[int] = None
    default_width: int = 0
    resize_mode: QHeaderView.ResizeMode = QHeaderView.Fixed
    priority: int = 0  # Higher priority columns get space first

    def __post_init__(self):
        """Set default values based on column type."""
        if self.column_type == ColumnType.FIXED:
            self.resize_mode = QHeaderView.Fixed
        elif self.column_type == ColumnType.INTERACTIVE:
            self.resize_mode = QHeaderView.Interactive
        elif self.column_type == ColumnType.STRETCH:
            self.resize_mode = QHeaderView.Stretch
        elif self.column_type == ColumnType.CONTENT_BASED:
            self.resize_mode = QHeaderView.ResizeToContents


@dataclass
class ColumnState:
    """State tracking for column management."""

    user_preferred_widths: Dict[int, int] = field(default_factory=dict)
    manual_resize_flags: Dict[int, bool] = field(default_factory=dict)
    last_calculated_widths: Dict[int, int] = field(default_factory=dict)
    programmatic_resize_active: bool = False
    font_metrics: Optional[QFontMetrics] = None

    def set_user_preference(self, column_index: int, width: int) -> None:
        """Set user preference for a column width."""
        self.user_preferred_widths[column_index] = width
        self.manual_resize_flags[column_index] = True

    def clear_user_preference(self, column_index: int) -> None:
        """Clear user preference for a column (allow auto-sizing)."""
        self.user_preferred_widths.pop(column_index, None)
        self.manual_resize_flags[column_index] = False

    def has_user_preference(self, column_index: int) -> bool:
        """Check if user has manually set a preference for this column."""
        return self.manual_resize_flags.get(column_index, False)


class ColumnManager:
    """
    Centralized column management system for all table views.

    This class handles intelligent column width calculation, user preference tracking,
    and dynamic column adjustment based on available space and content.
    """

    def __init__(self, main_window: QWidget) -> None:
        """
        Initialize the ColumnManager.

        Args:
            main_window: Reference to the main window for accessing components
        """
        self.main_window = main_window
        self.state = ColumnState()
        self.table_configs: Dict[str, Dict[int, ColumnConfig]] = {}

        # Initialize default configurations
        self._initialize_default_configs()

    def _initialize_default_configs(self) -> None:
        """Initialize default column configurations for different table types."""
        # File table configuration
        self.table_configs["file_table"] = {
            0: ColumnConfig(
                column_index=0,
                column_type=ColumnType.FIXED,
                min_width=50,  # Hardcoded status column width
                default_width=50,  # Hardcoded status column width
            ),
            1: ColumnConfig(
                column_index=1,
                column_type=ColumnType.INTERACTIVE,
                min_width=150,  # Reasonable minimum for filename column
                default_width=FILE_TABLE_COLUMN_CONFIG.get("filename", {}).get("width", 250),
            ),
            2: ColumnConfig(
                column_index=2,
                column_type=ColumnType.INTERACTIVE,
                min_width=FILE_TABLE_COLUMN_CONFIG.get("file_size", {}).get("min_width", 60),
                default_width=FILE_TABLE_COLUMN_CONFIG.get("file_size", {}).get("width", 75),
            ),
            3: ColumnConfig(
                column_index=3,
                column_type=ColumnType.INTERACTIVE,
                min_width=FILE_TABLE_COLUMN_CONFIG.get("type", {}).get("min_width", 40),
                default_width=FILE_TABLE_COLUMN_CONFIG.get("type", {}).get("width", 50),
            ),
            4: ColumnConfig(
                column_index=4,
                column_type=ColumnType.INTERACTIVE,
                min_width=FILE_TABLE_COLUMN_CONFIG.get("modified", {}).get("min_width", 100),
                default_width=FILE_TABLE_COLUMN_CONFIG.get("modified", {}).get("width", 115),
            ),
        }

        # Metadata tree configuration
        self.table_configs["metadata_tree"] = {
            0: ColumnConfig(
                column_index=0,
                column_type=ColumnType.INTERACTIVE,
                min_width=METADATA_TREE_COLUMN_WIDTHS["KEY_MIN_WIDTH"],
                max_width=METADATA_TREE_COLUMN_WIDTHS["KEY_MAX_WIDTH"],
                default_width=METADATA_TREE_COLUMN_WIDTHS["NORMAL_KEY_INITIAL_WIDTH"],
            ),
            1: ColumnConfig(
                column_index=1,
                column_type=ColumnType.INTERACTIVE,  # Changed from STRETCH to INTERACTIVE
                min_width=METADATA_TREE_COLUMN_WIDTHS["VALUE_MIN_WIDTH"],
                default_width=METADATA_TREE_COLUMN_WIDTHS["NORMAL_VALUE_INITIAL_WIDTH"],
            ),
        }

        # Preview tables auto-regulate and don't need column management

    def configure_table_columns(
        self, table_view: Union[QTableView, QTreeView], table_type: str
    ) -> None:
        """
        Configure columns for a specific table view.

        Args:
            table_view: The table/tree view to configure
            table_type: Type identifier ('file_table', 'metadata_tree', 'preview_old', 'preview_new')
        """
        # Skip preview tables as they auto-regulate
        if table_type in ["preview_old", "preview_new"]:
            logger.debug(
                f"[ColumnManager] Skipping auto-regulating table type: {table_type}",
                extra={"dev_only": True},
            )
            return

        # TEMPORARILY skip file_table to avoid conflicts with FileTableView column management
        if table_type == "file_table":
            logger.debug(
                "[ColumnManager] Skipping file_table - managed by FileTableView directly",
                extra={"dev_only": True},
            )
            return

        if table_type not in self.table_configs:
            logger.warning(f"[ColumnManager] Unknown table type: {table_type}")
            return

        if not table_view.model():
            logger.warning(f"[ColumnManager] No model set for table type: {table_type}")
            return

        # Get header - QTableView has horizontalHeader(), QTreeView has header()
        header = None
        if isinstance(table_view, QTableView):
            header = table_view.horizontalHeader()
        elif isinstance(table_view, QTreeView):
            header = table_view.header()

        if not header:
            logger.warning(f"[ColumnManager] No header found for table type: {table_type}")
            return

        # Get font metrics for text-based calculations
        self._update_font_metrics(table_view)

        # Configure each column
        config = self.table_configs[table_type]
        logger.debug(
            f"[ColumnManager] Configuring {len(config)} columns for {table_type}",
            extra={"dev_only": True},
        )

        for column_index, column_config in config.items():
            if column_index >= table_view.model().columnCount():
                logger.debug(
                    f"[ColumnManager] Skipping column {column_index} - exceeds model column count",
                    extra={"dev_only": True},
                )
                continue

            # Set resize mode
            header.setSectionResizeMode(column_index, column_config.resize_mode)
            logger.debug(
                f"[ColumnManager] SectionResizeMode for column {column_index}: {column_config.resize_mode}",
                extra={"dev_only": True},
            )

            # Calculate and set width
            width = self._calculate_column_width(table_view, table_type, column_config)
            logger.debug(
                f"[ColumnManager] Will set column {column_index} width to {width}px (config default: {column_config.default_width}px, min: {column_config.min_width}px)",
                extra={"dev_only": True},
            )
            table_view.setColumnWidth(column_index, width)

        # After configuration, log the actual widths
        for i in range(table_view.model().columnCount()):
            logger.debug(
                f"[ColumnManager] Actual width for column {i}: {table_view.columnWidth(i)}px",
                extra={"dev_only": True},
            )

        # Connect resize signals for user preference tracking
        self._connect_resize_signals(table_view, table_type)

        # Ensure horizontal scrollbar state is correct
        if isinstance(table_view, QTableView):
            self.ensure_horizontal_scrollbar_state(table_view)

        logger.debug(
            f"[ColumnManager] Configured columns for table type: {table_type}",
            extra={"dev_only": True},
        )

    def _update_font_metrics(self, widget: QWidget) -> None:
        """Update font metrics for text-based calculations."""
        try:
            # Try to get font metrics from the widget or its parent
            font_metrics = None
            current_widget = widget

            while current_widget and not font_metrics:
                if hasattr(current_widget, "fontMetrics"):
                    font_metrics = current_widget.fontMetrics()
                    break
                current_widget = current_widget.parent()

            if font_metrics:
                self.state.font_metrics = font_metrics
            else:
                logger.warning("[ColumnManager] Could not obtain font metrics")

        except Exception as e:
            logger.warning(f"[ColumnManager] Error updating font metrics: {e}")

    def _calculate_column_width(
        self, table_view: Union[QTableView, QTreeView], table_type: str, column_config: ColumnConfig
    ) -> int:
        logger.debug(
            f"[ColumnManager] Calculating width for column {column_config.column_index} (type: {column_config.column_type})",
            extra={"dev_only": True},
        )
        # Check if user has a preference for this column
        if self.state.has_user_preference(column_config.column_index):
            user_width = self.state.user_preferred_widths.get(column_config.column_index)
            if user_width and user_width >= column_config.min_width:
                logger.debug(
                    f"[ColumnManager] Using user preference: {user_width}px for column {column_config.column_index}",
                    extra={"dev_only": True},
                )
                return user_width

        # Try to load saved width from config system
        if table_type == "file_table" and column_config.column_index > 0:
            saved_width = self._load_saved_column_width(column_config.column_index)
            if saved_width and saved_width >= column_config.min_width:
                logger.debug(
                    f"[ColumnManager] Using saved width: {saved_width}px for column {column_config.column_index}",
                    extra={"dev_only": True},
                )
                return saved_width

        # Handle different column types
        if column_config.column_type == ColumnType.FIXED:
            logger.debug(
                f"[ColumnManager] Using fixed width: {column_config.default_width}px for column {column_config.column_index}",
                extra={"dev_only": True},
            )
            return column_config.default_width

        elif column_config.column_type == ColumnType.INTERACTIVE:
            width = max(column_config.default_width, column_config.min_width)
            logger.debug(
                f"[ColumnManager] Using interactive width: {width}px (default: {column_config.default_width}, min: {column_config.min_width}) for column {column_config.column_index}",
                extra={"dev_only": True},
            )
            return width

        elif column_config.column_type == ColumnType.STRETCH:
            width = self._calculate_stretch_column_width(table_view, table_type, column_config)
            logger.debug(
                f"[ColumnManager] Using stretch width: {width}px for column {column_config.column_index}",
                extra={"dev_only": True},
            )
            return width

        elif column_config.column_type == ColumnType.CONTENT_BASED:
            logger.debug(
                f"[ColumnManager] Using content-based width: {column_config.default_width}px for column {column_config.column_index}",
                extra={"dev_only": True},
            )
            return column_config.default_width

        logger.debug(
            f"[ColumnManager] Using fallback width: {column_config.default_width}px for column {column_config.column_index}",
            extra={"dev_only": True},
        )
        return column_config.default_width

    def _load_saved_column_width(self, column_index: int) -> Optional[int]:
        """Load saved column width from config system."""
        try:
            logger.debug(
                f"[ColumnManager] Loading saved width for column {column_index}",
                extra={"dev_only": True},
            )

            if hasattr(self.main_window, "window_config_manager"):
                config_manager = self.main_window.window_config_manager.config_manager
                window_config = config_manager.get_category("window")
                column_widths = window_config.get("file_table_column_widths", {})

                logger.debug(
                    f"[ColumnManager] Found column widths in window config: {column_widths}",
                    extra={"dev_only": True},
                )

                # Map column index to column key
                column_keys = ["filename", "file_size", "type", "modified"]
                if column_index <= len(column_keys):
                    column_key = column_keys[column_index - 1]  # -1 because column 0 is status
                    if column_key in column_widths:
                        width = column_widths[column_key]
                        logger.debug(
                            f"[ColumnManager] Found saved width for {column_key}: {width}px",
                            extra={"dev_only": True},
                        )
                        return width
                    else:
                        logger.debug(
                            f"[ColumnManager] No saved width found for {column_key}",
                            extra={"dev_only": True},
                        )

            # Fallback to old config system
            from utils.json_config_manager import load_config

            config = load_config()
            column_widths = config.get("file_table_column_widths", {})

            logger.debug(
                f"[ColumnManager] Found column widths in old config: {column_widths}",
                extra={"dev_only": True},
            )

            column_keys = ["filename", "file_size", "type", "modified"]
            if column_index <= len(column_keys):
                column_key = column_keys[column_index - 1]
                if column_key in column_widths:
                    width = column_widths[column_key]
                    logger.debug(
                        f"[ColumnManager] Found saved width in old config for {column_key}: {width}px",
                        extra={"dev_only": True},
                    )
                    return width

        except Exception as e:
            logger.warning(f"[ColumnManager] Error loading saved column width: {e}")

        logger.debug(
            f"[ColumnManager] No saved width found for column {column_index}",
            extra={"dev_only": True},
        )
        return None

    def _calculate_stretch_column_width(
        self, table_view: Union[QTableView, QTreeView], table_type: str, column_config: ColumnConfig
    ) -> int:
        """
        Calculate width for stretch columns that fill remaining space.

        Args:
            table_view: The table/tree view
            table_type: Type identifier
            column_config: Configuration for the column

        Returns:
            Calculated width in pixels
        """
        try:
            viewport_width = table_view.viewport().width()
            if viewport_width <= 0:
                return column_config.default_width

            # Calculate space used by other columns
            config = self.table_configs[table_type]
            other_columns_width = 0

            for idx, other_config in config.items():
                if idx != column_config.column_index:
                    if other_config.column_type == ColumnType.FIXED:
                        other_columns_width += other_config.default_width
                    elif other_config.column_type == ColumnType.INTERACTIVE:
                        # Use current width if available, otherwise default
                        current_width = (
                            table_view.columnWidth(idx)
                            if hasattr(table_view, "columnWidth")
                            else other_config.default_width
                        )
                        other_columns_width += current_width

            # Calculate available width
            available_width = viewport_width - other_columns_width - 20  # Small margin

            # Ensure minimum width
            return max(available_width, column_config.min_width)

        except Exception as e:
            logger.warning(f"[ColumnManager] Error calculating stretch column width: {e}")
            return column_config.default_width

    def _needs_vertical_scrollbar(self, table_view: Union[QTableView, QTreeView]) -> bool:
        """Check if vertical scrollbar is needed."""
        try:
            model = table_view.model()
            if not model:
                return False

            row_count = model.rowCount()
            if row_count == 0:
                return False

            viewport_height = table_view.viewport().height()
            if viewport_height <= 0:
                return False

            # Estimate row height (this is approximate)
            row_height = 20  # Default estimate
            if hasattr(table_view, "rowHeight"):
                try:
                    row_height = table_view.rowHeight(0) if row_count > 0 else 20
                except (AttributeError, RuntimeError):
                    pass

            total_content_height = row_count * row_height

            # Add header height
            header_height = 0
            if isinstance(table_view, QTableView):
                header = table_view.horizontalHeader()
                if header:
                    header_height = header.height()
            elif isinstance(table_view, QTreeView):
                header = table_view.header()
                if header:
                    header_height = header.height()

            return (total_content_height + header_height) > viewport_height

        except Exception as e:
            logger.warning(f"[ColumnManager] Error checking scrollbar need: {e}")
            return False

    def _get_scrollbar_width(self, table_view: Union[QTableView, QTreeView]) -> int:
        """Get the width of the vertical scrollbar."""
        try:
            if hasattr(table_view, "verticalScrollBar"):
                scrollbar = table_view.verticalScrollBar()
                if scrollbar and scrollbar.isVisible():
                    width = scrollbar.width()
                    if width > 0:
                        return width
        except (AttributeError, RuntimeError):
            pass
        return 14  # Default estimate

    def ensure_horizontal_scrollbar_state(self, table_view: QTableView) -> None:
        """
        Ensure that the horizontal scrollbar state is consistent with the current column layout.
        Forces proper recalculation when viewport changes.
        """
        try:
            # Store current scrollbar position to preserve user's scroll position
            hbar = table_view.horizontalScrollBar()
            current_scroll_position = hbar.value() if hbar else 0

            # Force complete geometry recalculation
            table_view.updateGeometries()

            # Force layout recalculation to update elided text
            if table_view.model():
                table_view.model().layoutChanged.emit()

            # Update viewport to refresh display
            table_view.viewport().update()

            # Restore scrollbar position if it's still valid
            if hbar:
                # If the stored position is still valid, restore it
                if hbar.maximum() > 0:
                    # If the stored position is still valid, restore it
                    if current_scroll_position <= hbar.maximum():
                        hbar.setValue(current_scroll_position)
                        logger.debug(
                            f"[ColumnManager] Restored horizontal scrollbar to position: {current_scroll_position}",
                            extra={"dev_only": True},
                        )
                    else:
                        # If the stored position is beyond the new range, go to the rightmost valid position
                        hbar.setValue(hbar.maximum())
                        logger.debug(
                            f"[ColumnManager] Adjusted horizontal scrollbar to maximum: {hbar.maximum()}",
                            extra={"dev_only": True},
                        )
                else:
                    # No scrolling needed, reset to 0
                    hbar.setValue(0)
                    logger.debug(
                        "[ColumnManager] Reset horizontal scrollbar to 0 (no scrolling needed)",
                        extra={"dev_only": True},
                    )

                logger.debug(
                    f"[ColumnManager] Updated horizontal scrollbar: max={hbar.maximum()}, value={hbar.value()}",
                    extra={"dev_only": True},
                )

        except Exception as e:
            logger.warning(f"[ColumnManager] Error updating horizontal scrollbar state: {e}")

    def _connect_resize_signals(
        self, table_view: Union[QTableView, QTreeView], table_type: str
    ) -> None:
        """Connect resize signals for user preference tracking."""
        try:
            # Get header - QTableView has horizontalHeader(), QTreeView has header()
            header = None
            if isinstance(table_view, QTableView):
                header = table_view.horizontalHeader()
            elif isinstance(table_view, QTreeView):
                header = table_view.header()

            if header:
                # Disconnect any existing connections to avoid duplicates
                try:
                    # Use a more specific disconnect approach
                    header.sectionResized.disconnect()
                except (AttributeError, RuntimeError, TypeError):
                    # If disconnect fails, it's okay - we'll just connect again
                    pass

                # Connect new handler with proper lambda capture
                def resize_handler(logical_index, old_size, new_size):
                    self._on_column_resized(table_type, logical_index, old_size, new_size)

                header.sectionResized.connect(resize_handler)

        except Exception as e:
            logger.warning(f"[ColumnManager] Error connecting resize signals: {e}")

    def _on_column_resized(
        self, table_type: str, logical_index: int, old_size: int, new_size: int
    ) -> None:
        """Handle column resize events to track user preferences."""
        if self.state.programmatic_resize_active:
            return

        # Skip column 0 (status) - it's hardcoded and shouldn't be saved
        if logical_index == 0:
            return

        # Check if this is a user-initiated resize
        if table_type in self.table_configs and logical_index in self.table_configs[table_type]:
            column_config = self.table_configs[table_type][logical_index]

            # Only track interactive columns
            if column_config.column_type == ColumnType.INTERACTIVE:
                # Enforce minimum width
                if new_size < column_config.min_width:
                    self.state.programmatic_resize_active = True
                    # Need to set the width back (this requires access to the table view)
                    # This will be handled by the individual table view's resize handler
                    self.state.programmatic_resize_active = False
                    return

                # Track user preference
                self.state.set_user_preference(logical_index, new_size)
                logger.debug(
                    f"[ColumnManager] User preference set for {table_type} column {logical_index}: {new_size}",
                    extra={"dev_only": True},
                )

                # Update horizontal scrollbar state after user resize
                # We need to find the table view for this - this is a limitation of the current design
                # For now, we'll rely on the table view's own resize handlers to call this method

    def adjust_columns_for_splitter_change(
        self, table_view: Union[QTableView, QTreeView], table_type: str
    ) -> None:
        """
        Adjust columns when splitter position changes.

        Args:
            table_view: The table/tree view to adjust
            table_type: Type identifier
        """
        if table_type not in self.table_configs:
            return

        config = self.table_configs[table_type]

        # Recalculate and adjust columns that need dynamic sizing
        for column_index, column_config in config.items():
            if column_config.column_type in [ColumnType.INTERACTIVE, ColumnType.STRETCH]:
                # Skip if user has manual preference and it's recent
                if self.state.has_user_preference(column_index):
                    continue

                # Calculate new width
                new_width = self._calculate_column_width(table_view, table_type, column_config)

                # Only update if there's a significant change
                current_width = table_view.columnWidth(column_index)
                if abs(new_width - current_width) > 5:  # 5px threshold
                    self.state.programmatic_resize_active = True
                    table_view.setColumnWidth(column_index, new_width)
                    self.state.programmatic_resize_active = False

        # Ensure horizontal scrollbar state is correct after column adjustments
        if isinstance(table_view, QTableView):
            self.ensure_horizontal_scrollbar_state(table_view)

    def reset_user_preferences(self, table_type: str, column_index: Optional[int] = None) -> None:
        """
        Reset user preferences for columns to allow auto-sizing.

        Args:
            table_type: Type identifier
            column_index: Specific column to reset, or None for all columns
        """
        if column_index is not None:
            self.state.clear_user_preference(column_index)
            logger.debug(
                f"[ColumnManager] Reset user preference for {table_type} column {column_index}",
                extra={"dev_only": True},
            )
        else:
            # Reset all preferences for this table type
            if table_type in self.table_configs:
                for column_index in self.table_configs[table_type].keys():
                    self.state.clear_user_preference(column_index)
                logger.debug(
                    f"[ColumnManager] Reset all user preferences for {table_type}",
                    extra={"dev_only": True},
                )

    def save_column_state(self, table_type: str) -> Dict[str, Any]:
        """
        Save current column state for persistence.

        Args:
            table_type: Type identifier

        Returns:
            Dictionary containing column state data
        """
        state_data = {"user_preferences": {}, "manual_flags": {}}

        if table_type in self.table_configs:
            for column_index in self.table_configs[table_type].keys():
                # Skip column 0 (status) - it's hardcoded and shouldn't be saved
                if column_index == 0:
                    continue

                if column_index in self.state.user_preferred_widths:
                    state_data["user_preferences"][column_index] = self.state.user_preferred_widths[
                        column_index
                    ]
                if column_index in self.state.manual_resize_flags:
                    state_data["manual_flags"][column_index] = self.state.manual_resize_flags[
                        column_index
                    ]

        return state_data

    def load_column_state(self, table_type: str, state_data: Dict[str, Any]) -> None:
        """
        Load column state from persistence.

        Args:
            table_type: Type identifier
            state_data: Dictionary containing column state data
        """
        try:
            if "user_preferences" in state_data:
                for column_index, width in state_data["user_preferences"].items():
                    self.state.user_preferred_widths[int(column_index)] = width

            if "manual_flags" in state_data:
                for column_index, flag in state_data["manual_flags"].items():
                    self.state.manual_resize_flags[int(column_index)] = flag

            logger.debug(
                f"[ColumnManager] Loaded column state for {table_type}", extra={"dev_only": True}
            )

        except Exception as e:
            logger.warning(f"[ColumnManager] Error loading column state: {e}")

    def get_column_config(self, table_type: str, column_index: int) -> Optional[ColumnConfig]:
        """
        Get column configuration for a specific column.

        Args:
            table_type: Type identifier
            column_index: Column index

        Returns:
            ColumnConfig if found, None otherwise
        """
        if table_type in self.table_configs:
            return self.table_configs[table_type].get(column_index)
        return None

    def update_column_config(self, table_type: str, column_index: int, **kwargs) -> None:
        """
        Update column configuration.

        Args:
            table_type: Type identifier
            column_index: Column index
            **kwargs: Configuration parameters to update
        """
        if table_type in self.table_configs and column_index in self.table_configs[table_type]:
            config = self.table_configs[table_type][column_index]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            logger.debug(
                f"[ColumnManager] Updated config for {table_type} column {column_index}",
                extra={"dev_only": True},
            )
