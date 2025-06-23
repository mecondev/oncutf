"""
progress_widget.py

Author: Michael Economou
Date: 2025-06-23

Unified progress widget system for the oncutf application.
Consolidates all progress-related widgets into a single, consistent module.

Features:
- Basic progress bar with status and filename
- Enhanced progress tracking with size and time estimation
- Configurable layout modes (compact, standard, enhanced)
- Cross-platform compatible formatting
- Consistent API across all variants
"""

from typing import Optional

from core.qt_imports import (
    Qt, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QSizePolicy, QFrame
)
from utils.logger_factory import get_cached_logger
from utils.time_formatter import ProgressEstimator

logger = get_cached_logger(__name__)


class BaseProgressWidget(QWidget):
    """
    Base progress widget with common functionality.

    Provides the foundation for all progress widgets with:
    - Progress bar
    - Status message
    - Filename display
    - Count display
    - Consistent styling
    """

    def __init__(self, parent: Optional[QWidget] = None,
                 bar_color: str = "#64b5f6",
                 bar_bg_color: str = "#0a1a2a"):
        """
        Initialize the base progress widget.

        Args:
            parent: Parent widget
            bar_color: Progress bar color
            bar_bg_color: Progress bar background color
        """
        super().__init__(parent)

        self.bar_color = bar_color
        self.bar_bg_color = bar_bg_color

        self._setup_ui()
        self._apply_styling()

        logger.debug("[BaseProgressWidget] Initialized")

    def _setup_ui(self):
        """Setup the basic UI components."""
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(8)

        # Status label
        self.status_label = QLabel("Please wait...")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.main_layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progress_bar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.main_layout.addWidget(self.progress_bar)

        # Filename label
        self.filename_label = QLabel("")
        self.filename_label.setObjectName("filename_label")
        self.filename_label.setAlignment(Qt.AlignCenter)
        self.filename_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.main_layout.addWidget(self.filename_label)

        # Count label
        self.count_label = QLabel("")
        self.count_label.setObjectName("count_label")
        self.count_label.setAlignment(Qt.AlignCenter)
        self.count_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.main_layout.addWidget(self.count_label)

        self.setLayout(self.main_layout)

    def _apply_styling(self):
        """Apply styling to the widget components."""
        style = f"""
        QLabel#status_label {{
            color: #f0ebd8;
            font-size: 13px;
            font-family: 'Inter', sans-serif;
            font-weight: 500;
            background-color: transparent;
            border: none;
            padding: 4px 8px;
        }}

        QLabel#filename_label {{
            color: #b0bec5;
            font-size: 11px;
            font-family: 'Inter', sans-serif;
            background-color: transparent;
            border: none;
            padding: 2px 4px;
        }}

        QLabel#count_label {{
            color: #90a4ae;
            font-size: 10px;
            font-family: 'Inter', sans-serif;
            background-color: transparent;
            border: none;
            padding: 2px 4px;
        }}

        QProgressBar#progress_bar {{
            border: 1px solid #3a3b40;
            border-radius: 6px;
            background-color: {self.bar_bg_color};
            height: 8px;
            text-align: center;
        }}

        QProgressBar#progress_bar::chunk {{
            background-color: {self.bar_color};
            border-radius: 5px;
            margin: 1px;
        }}
        """

        self.setStyleSheet(style)

    # Public API methods
    def set_progress(self, value: int, total: int):
        """Set progress bar value and total."""
        if total > 0:
            percentage = int((value / total) * 100)
            self.progress_bar.setValue(percentage)
        else:
            self.progress_bar.setValue(0)

    def set_status(self, status: str):
        """Set status message."""
        self.status_label.setText(status)

    def set_filename(self, filename: str):
        """Set current filename display."""
        if filename:
            # Truncate long filenames
            max_length = 50
            if len(filename) > max_length:
                filename = f"...{filename[-(max_length-3):]}"
            self.filename_label.setText(filename)
            self.filename_label.show()
        else:
            self.filename_label.hide()

    def set_count(self, current: int, total: int):
        """Set current/total count display."""
        if total > 0:
            self.count_label.setText(f"{current}/{total}")
            self.count_label.show()
        else:
            self.count_label.hide()


class CompactProgressWidget(BaseProgressWidget):
    """
    Compact progress widget optimized for dialogs.

    Features:
    - Smaller margins and spacing
    - Tighter layout
    - Optimized for modal dialogs
    """

    def __init__(self, *args, **kwargs):
        """Initialize compact progress widget."""
        super().__init__(*args, **kwargs)
        self._apply_compact_layout()

        logger.debug("[CompactProgressWidget] Initialized")

    def _apply_compact_layout(self):
        """Apply compact layout settings."""
        # Adjust main layout for compact mode
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(6)

        # Apply compact styling
        compact_style = """
        QLabel#status_label {
            font-size: 12px;
            padding: 2px 4px;
        }

        QLabel#filename_label {
            font-size: 10px;
            padding: 1px 2px;
        }

        QLabel#count_label {
            font-size: 9px;
            padding: 1px 2px;
        }
        """

        current_style = self.styleSheet()
        self.setStyleSheet(current_style + compact_style)


class EnhancedProgressWidget(BaseProgressWidget):
    """
    Enhanced progress widget with size and time tracking.

    Features:
    - File size progress tracking
    - Time estimation and elapsed time
    - Real-time progress rate calculation
    - Configurable info display layout
    """

    def __init__(self, parent: Optional[QWidget] = None,
                 bar_color: str = "#64b5f6",
                 bar_bg_color: str = "#0a1a2a",
                 show_size_info: bool = True,
                 show_time_info: bool = True,
                 layout_style: str = "bottom"):
        """
        Initialize enhanced progress widget.

        Args:
            parent: Parent widget
            bar_color: Progress bar color
            bar_bg_color: Progress bar background color
            show_size_info: Whether to show size tracking
            show_time_info: Whether to show time estimation
            layout_style: Layout style ("bottom" or "side")
        """
        self.show_size_info = show_size_info
        self.show_time_info = show_time_info
        self.layout_style = layout_style

        # Progress estimator for advanced tracking
        self.progress_estimator = ProgressEstimator()

        super().__init__(parent, bar_color, bar_bg_color)

        # Add enhanced info panel after base setup
        if self.show_size_info or self.show_time_info:
            self._setup_info_panel()

        logger.debug(f"[EnhancedProgressWidget] Initialized (layout: {layout_style})")

    def _setup_info_panel(self):
        """Setup the additional information panel."""
        # Create info container
        info_container = QWidget()
        info_layout = QHBoxLayout(info_container)
        info_layout.setContentsMargins(8, 4, 8, 4)
        info_layout.setSpacing(16)

        # Size info label
        if self.show_size_info:
            self.size_label = QLabel("Calculating size...")
            self.size_label.setObjectName("size_info_label")
            self.size_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.size_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            info_layout.addWidget(self.size_label)

        # Spacer
        if self.show_size_info and self.show_time_info:
            info_layout.addStretch()

        # Time info label
        if self.show_time_info:
            self.time_label = QLabel("Calculating time...")
            self.time_label.setObjectName("time_info_label")
            self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.time_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            info_layout.addWidget(self.time_label)

        info_container.setLayout(info_layout)

        # Add to main layout
        if self.layout_style == "side":
            # Convert main layout to horizontal and add info on the side
            # This is more complex, so we'll implement bottom layout for now
            pass

        # Add at bottom (default)
        self.main_layout.addWidget(info_container)

        # Apply info styling
        self._apply_info_styling()

    def _apply_info_styling(self):
        """Apply styling to info labels."""
        info_style = """
        QLabel#size_info_label, QLabel#time_info_label {
            color: #b0bec5;
            font-size: 11px;
            font-family: 'Inter', sans-serif;
            background-color: transparent;
            border: none;
            padding: 2px 4px;
        }

        QLabel#size_info_label:hover, QLabel#time_info_label:hover {
            color: #cfd8dc;
        }
        """

        current_style = self.styleSheet()
        self.setStyleSheet(current_style + info_style)

    def start_progress(self, total_size: int = 0):
        """
        Start enhanced progress tracking.

        Args:
            total_size: Total size in bytes (optional)
        """
        self.progress_estimator.start(total_size)

        # Initialize displays
        if self.show_size_info:
            if total_size > 0:
                self.size_label.setText("0 B/calculating...")
            else:
                self.size_label.setText("Processing...")

        if self.show_time_info:
            self.time_label.setText("Starting...")

        logger.debug(f"[EnhancedProgressWidget] Started tracking (total_size: {total_size})")

    def update_progress(self, current: int, total: int, current_size: int = 0):
        """
        Update progress with comprehensive tracking.

        Args:
            current: Current item number
            total: Total number of items
            current_size: Current processed size in bytes
        """
        # Update base progress
        super().set_progress(current, total)

        # Update progress estimator
        self.progress_estimator.update(current, total, current_size)

        # Update additional info
        self._update_info_displays()

    def _update_info_displays(self):
        """Update the size and time info displays."""
        summary = self.progress_estimator.get_progress_summary()

        # Update size info
        if self.show_size_info:
            size_text = summary['size_range']
            if not size_text or size_text == "0 B":
                size_text = "Processing..."
            self.size_label.setText(size_text)

        # Update time info
        if self.show_time_info:
            time_text = summary['time_range']
            if not time_text or time_text == "0''":
                time_text = "Calculating..."
            self.time_label.setText(time_text)

    def set_size_info(self, processed_size: int, total_size: int = 0):
        """Manually set size information."""
        if not self.show_size_info:
            return

        from utils.file_size_formatter import format_file_size_system_compatible

        processed_str = format_file_size_system_compatible(processed_size)

        if total_size > 0:
            total_str = format_file_size_system_compatible(total_size)
            size_text = f"{processed_str}/{total_str}"
        else:
            size_text = processed_str

        self.size_label.setText(size_text)

    def set_time_info(self, elapsed: float, estimated_total: Optional[float] = None):
        """Manually set time information."""
        if not self.show_time_info:
            return

        from utils.time_formatter import format_time_range

        time_text = format_time_range(elapsed, estimated_total)
        self.time_label.setText(time_text)

    def get_progress_summary(self) -> dict:
        """Get comprehensive progress summary."""
        return self.progress_estimator.get_progress_summary()

    def reset(self):
        """Reset all progress tracking."""
        self.progress_estimator = ProgressEstimator()
        self.set_progress(0, 100)

        if self.show_size_info:
            self.size_label.setText("Ready...")

        if self.show_time_info:
            self.time_label.setText("Ready...")


class CompactEnhancedProgressWidget(EnhancedProgressWidget):
    """
    Compact version of EnhancedProgressWidget optimized for dialogs.

    Combines enhanced functionality with compact layout for modal dialogs.
    """

    def __init__(self, *args, **kwargs):
        """Initialize compact enhanced progress widget."""
        super().__init__(*args, **kwargs)
        self._apply_compact_enhancements()

        logger.debug("[CompactEnhancedProgressWidget] Initialized")

    def _apply_compact_enhancements(self):
        """Apply compact layout and styling."""
        # Adjust main layout for compact mode
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(4)

        # Apply compact styling for enhanced elements
        compact_enhanced_style = """
        QLabel#status_label {
            font-size: 12px;
            padding: 2px 4px;
        }

        QLabel#filename_label {
            font-size: 10px;
            padding: 1px 2px;
        }

        QLabel#count_label {
            font-size: 9px;
            padding: 1px 2px;
        }

        QLabel#size_info_label, QLabel#time_info_label {
            color: #90a4ae;
            font-size: 10px;
            font-family: 'Inter', sans-serif;
            background-color: transparent;
            border: none;
            padding: 1px 2px;
            margin: 0px;
        }

        QLabel#size_info_label:hover, QLabel#time_info_label:hover {
            color: #b0bec5;
        }
        """

        current_style = self.styleSheet()
        self.setStyleSheet(current_style + compact_enhanced_style)


# Factory functions for easy creation
def create_basic_progress_widget(parent=None, **kwargs):
    """Create a basic progress widget."""
    return BaseProgressWidget(parent, **kwargs)

def create_compact_progress_widget(parent=None, **kwargs):
    """Create a compact progress widget."""
    return CompactProgressWidget(parent, **kwargs)

def create_enhanced_progress_widget(parent=None, **kwargs):
    """Create an enhanced progress widget."""
    return EnhancedProgressWidget(parent, **kwargs)

def create_compact_enhanced_progress_widget(parent=None, **kwargs):
    """Create a compact enhanced progress widget."""
    return CompactEnhancedProgressWidget(parent, **kwargs)


# Legacy compatibility aliases
CompactWaitingWidget = CompactProgressWidget  # For backward compatibility
