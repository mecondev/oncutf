"""
Module: placeholder_helper.py

Author: Michael Economou
Date: 2025-01-15

Unified placeholder management system for all widgets.
Provides consistent placeholder behavior across FileTableView, MetadataTreeView, and PreviewTablesView.
"""

from core.pyqt_imports import QLabel, QPixmap, Qt, QWidget
from utils.logger_factory import get_cached_logger
from utils.path_utils import get_images_dir
from utils.theme import get_theme_color

logger = get_cached_logger(__name__)


class PlaceholderHelper:
    """
    Unified placeholder management for widgets.

    Features:
    - Consistent placeholder appearance across all widgets
    - Automatic icon loading and scaling
    - Theme-aware styling
    - Simple show/hide interface
    """

    def __init__(
        self,
        parent_widget: QWidget,
        icon_name: str,
        placeholder_text: str = "",
        icon_size: int = 160,
    ):
        """
        Initialize placeholder helper.

        Args:
            parent_widget: The widget that will contain the placeholder
            icon_name: Name of the icon file (without extension)
            placeholder_text: Optional text to display (defaults to icon only)
            icon_size: Size of the placeholder icon in pixels
        """
        self.parent_widget = parent_widget
        self.icon_name = icon_name
        self.placeholder_text = placeholder_text
        self.icon_size = icon_size

        # Create placeholder label
        self.placeholder_label = QLabel(parent_widget.viewport())
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setVisible(False)

        logger.debug(
            f"[PlaceholderHelper] Created placeholder label for {icon_name}",
            extra={"dev_only": True},
        )

        # Load and setup icon
        self._setup_icon()

        # Apply theme-aware styling
        self._apply_styling()

        logger.debug(f"[PlaceholderHelper] Initialized for {icon_name}", extra={"dev_only": True})

    def _setup_icon(self) -> None:
        """Load and setup the placeholder icon."""
        try:
            icon_path = get_images_dir() / f"{self.icon_name}.png"
            self.placeholder_icon = QPixmap(str(icon_path))

            if not self.placeholder_icon.isNull():
                scaled = self.placeholder_icon.scaled(
                    self.icon_size, self.icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.placeholder_label.setPixmap(scaled)
                logger.debug(
                    f"[PlaceholderHelper] Icon loaded and set: {icon_path} (size: {scaled.size()})",
                    extra={"dev_only": True},
                )
            else:
                logger.warning(f"[PlaceholderHelper] Could not load icon: {icon_path}")

        except Exception as e:
            logger.error(f"[PlaceholderHelper] Error loading icon: {e}")
            self.placeholder_icon = QPixmap()

    def _apply_styling(self) -> None:
        """Apply theme-aware styling to the placeholder."""
        try:
            bg_color = get_theme_color("table_background")

            if self.placeholder_text:
                # Text + icon styling
                style = f"""
                    background-color: {bg_color};
                    color: #f0ebd8;
                    font-size: 14px;
                    font-weight: normal;
                    padding: 20px;
                """
            else:
                # Icon-only styling
                style = f"background-color: {bg_color};"

            self.placeholder_label.setStyleSheet(style)
            logger.debug(
                f"[PlaceholderHelper] Applied styling: {bg_color}", extra={"dev_only": True}
            )

        except Exception as e:
            logger.error(f"[PlaceholderHelper] Error applying styling: {e}")
            # Fallback styling
            self.placeholder_label.setStyleSheet("background-color: #181818;")

    def show(self) -> None:
        """Show the placeholder."""
        if self.placeholder_label:
            self.placeholder_label.raise_()
            self.placeholder_label.show()
            logger.debug(
                f"[PlaceholderHelper] Placeholder shown: {self.icon_name}", extra={"dev_only": True}
            )
        else:
            logger.warning(f"[PlaceholderHelper] No placeholder label to show: {self.icon_name}")

    def hide(self) -> None:
        """Hide the placeholder."""
        if self.placeholder_label:
            self.placeholder_label.hide()
            logger.debug(
                f"[PlaceholderHelper] Placeholder hidden: {self.icon_name}",
                extra={"dev_only": True},
            )
        else:
            logger.warning(f"[PlaceholderHelper] No placeholder label to hide: {self.icon_name}")

    def is_visible(self) -> bool:
        """Check if placeholder is currently visible."""
        return self.placeholder_label.isVisible() if self.placeholder_label else False

    def update_position(self) -> None:
        """Update placeholder position to center it in the viewport."""
        if self.placeholder_label and self.parent_widget:
            viewport_size = self.parent_widget.viewport().size()

            # Get the actual scaled icon size from the label's pixmap
            pixmap = self.placeholder_label.pixmap()
            if pixmap and not pixmap.isNull():
                icon_size = pixmap.size()
                # Calculate center position
                x = max(0, (viewport_size.width() - icon_size.width()) // 2)
                y = max(0, (viewport_size.height() - icon_size.height()) // 2)

                # Resize label to icon size and position it
                self.placeholder_label.resize(icon_size)
                self.placeholder_label.move(x, y)
                logger.debug(
                    f"[PlaceholderHelper] Positioned at ({x}, {y}) with size {icon_size}",
                    extra={"dev_only": True},
                )
            else:
                # Fallback: center the label itself
                self.placeholder_label.resize(viewport_size)
                self.placeholder_label.move(0, 0)
                logger.debug(
                    f"[PlaceholderHelper] Fallback positioning with viewport size {viewport_size}",
                    extra={"dev_only": True},
                )

    def set_text(self, text: str) -> None:
        """Set placeholder text (if supported)."""
        if self.placeholder_text and self.placeholder_label:
            self.placeholder_label.setText(text)

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.placeholder_label:
            self.placeholder_label.deleteLater()
            self.placeholder_label = None


def create_placeholder_helper(
    widget: QWidget, placeholder_type: str, text: str = "", icon_size: int = 160
) -> PlaceholderHelper:
    """
    Factory function to create placeholder helpers for different widget types.

    Args:
        widget: The widget to add placeholder to
        placeholder_type: Type of placeholder ('file_table', 'metadata_tree', 'preview_old', 'preview_new')
        text: Optional placeholder text
        icon_size: Size of the placeholder icon

    Returns:
        PlaceholderHelper instance
    """
    icon_mapping = {
        "file_table": "File_table_placeholder_fixed",
        "metadata_tree": "metadata_tree_placeholder_fixed",
        "preview_old": "old_names-preview_placeholder",
        "preview_new": "new_names-preview_placeholder",
    }

    icon_name = icon_mapping.get(placeholder_type, "File_table_placeholder_fixed")

    return PlaceholderHelper(widget, icon_name, text, icon_size)
