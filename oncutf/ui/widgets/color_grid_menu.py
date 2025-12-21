"""
Module: color_grid_menu.py

Author: Michael Economou
Date: 2025-12-21

Custom color grid menu widget for file color tagging.

Layout:
┌─────────────────────────┬───────┐
│ Color Grid (4 rows x 8) │ Color │
│                         │ Picker│
│                         │ Image │
├─────────────────────────┴───────┤
│      None - Reset color         │
└─────────────────────────────────┘
"""

from oncutf.core.pyqt_imports import (
    QColorDialog,
    QGridLayout,
    QHBoxLayout,
    QIcon,
    QPushButton,
    QSize,
    QToolButton,
    QVBoxLayout,
    QWidget,
    Qt,
    pyqtSignal,
    QPixmap,
)
from oncutf.utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ColorButton(QToolButton):
    """
    Single color button in the color grid.
    
    Displays a solid color swatch that can be clicked to select.
    """
    
    clicked_with_color = pyqtSignal(str)  # Emits hex color on click
    
    def __init__(self, color: str, parent=None):
        """
        Initialize color button.
        
        Args:
            color: Hex color string (e.g., "#ff0000")
            parent: Parent widget
        """
        super().__init__(parent)
        self.color = color
        
        from oncutf.config import COLOR_SWATCH_SIZE
        
        self.setFixedSize(COLOR_SWATCH_SIZE, COLOR_SWATCH_SIZE)
        self.setToolTip(color.upper())
        
        # Style with solid color background
        self.setStyleSheet(f"""
            QToolButton {{
                background-color: {color};
                border: 1px solid #555;
                border-radius: 2px;
            }}
            QToolButton:hover {{
                border: 2px solid #fff;
                border-radius: 2px;
            }}
            QToolButton:pressed {{
                border: 2px solid #aaa;
            }}
        """)
        
        self.clicked.connect(lambda: self.clicked_with_color.emit(self.color))


class ColorGridMenu(QWidget):
    """
    Color grid menu widget with 32 color swatches, custom color picker, and reset option.
    
    This widget appears as a popup when right-clicking on the color column.
    """
    
    color_selected = pyqtSignal(str)  # Emits selected color hex or "none"
    
    def __init__(self, parent=None):
        """
        Initialize color grid menu.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Popup window flags
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self._setup_ui()
        
        logger.debug("[ColorGridMenu] Initialized")
    
    def _setup_ui(self):
        """Setup the menu UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)
        
        # Top section: Color grid + Picker image
        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)
        
        # Left: Color grid (4 rows x 8 columns)
        grid_widget = self._create_color_grid()
        top_layout.addWidget(grid_widget)
        
        # Right: Color picker button with image
        picker_btn = self._create_picker_button()
        top_layout.addWidget(picker_btn)
        
        main_layout.addLayout(top_layout)
        
        # Bottom: None/Reset button
        none_btn = QPushButton("None - Reset the color")
        none_btn.setFixedHeight(28)
        none_btn.setToolTip("Remove color tag from file")
        none_btn.clicked.connect(lambda: self._on_color_selected("none"))
        main_layout.addWidget(none_btn)
        
        # Apply dark theme styling
        self.setStyleSheet("""
            ColorGridMenu {
                background-color: #2b2b2b;
                border: 2px solid #555;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: #ddd;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border: 1px solid #777;
            }
            QPushButton:pressed {
                background-color: #333;
            }
        """)
    
    def _create_color_grid(self) -> QWidget:
        """
        Create the color grid widget with all color swatches.
        
        Returns:
            Widget containing the color grid
        """
        from oncutf.config import COLOR_PALETTE, COLOR_GRID_ROWS, COLOR_GRID_COLS
        
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(3)
        
        for i, color in enumerate(COLOR_PALETTE):
            row = i // COLOR_GRID_COLS
            col = i % COLOR_GRID_COLS
            
            btn = ColorButton(color)
            btn.clicked_with_color.connect(self._on_color_selected)
            grid_layout.addWidget(btn, row, col)
        
        return grid_widget
    
    def _create_picker_button(self) -> QToolButton:
        """
        Create the custom color picker button with image.
        
        Returns:
            Color picker button widget
        """
        from oncutf.config import COLOR_PICKER_IMAGE
        from oncutf.utils.path_utils import get_resource_path
        
        picker_btn = QToolButton()
        picker_btn.setFixedSize(65, 85)
        picker_btn.setToolTip("Custom color picker\n(OS color dialog)")
        
        # Load color range image
        try:
            image_path = get_resource_path(COLOR_PICKER_IMAGE)
            pixmap = QPixmap(str(image_path))
            
            if not pixmap.isNull():
                # Scale to button size with smooth transformation
                scaled_pixmap = pixmap.scaled(
                    63, 83,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                picker_btn.setIcon(QIcon(scaled_pixmap))
                picker_btn.setIconSize(QSize(63, 83))
            else:
                logger.warning("[ColorGridMenu] Failed to load color picker image")
                picker_btn.setText("...")
        
        except Exception as e:
            logger.error("[ColorGridMenu] Error loading picker image: %s", e)
            picker_btn.setText("...")
        
        picker_btn.setStyleSheet("""
            QToolButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 3px;
            }
            QToolButton:hover {
                border: 2px solid #777;
            }
            QToolButton:pressed {
                border: 2px solid #aaa;
            }
        """)
        
        picker_btn.clicked.connect(self._open_color_picker)
        
        return picker_btn
    
    def _on_color_selected(self, color: str):
        """
        Handle color selection.
        
        Args:
            color: Selected hex color or "none"
        """
        logger.debug("[ColorGridMenu] Color selected: %s", color)
        self.color_selected.emit(color)
        self.close()
    
    def _open_color_picker(self):
        """Open the OS native color picker dialog."""
        logger.debug("[ColorGridMenu] Opening custom color picker")
        
        color = QColorDialog.getColor(
            parent=self,
            title="Select Custom Color"
        )
        
        if color.isValid():
            hex_color = color.name()  # Returns #RRGGBB format
            logger.debug("[ColorGridMenu] Custom color selected: %s", hex_color)
            self._on_color_selected(hex_color)
        else:
            logger.debug("[ColorGridMenu] Color picker cancelled")
