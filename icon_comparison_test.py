#!/usr/bin/env python3
"""
Icon Comparison Test

Visual comparison of old PNG icons vs new SVG icons with proper colors.
Uses the same dark theme as OnCutF for accurate representation.

Colors used:
- Extended metadata: #ffb74d (orange like progress bar)
- Hash operations: #9c27b0 (purple like progress bar)
- Basic info: #74c0fc (light blue)
- Invalid/Error: #ff6b6b (light red)
- Valid/Success: #51cf66 (light green)
- Partial/Warning: #ffa726 (light orange)
"""

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QScrollArea, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QColor
from PyQt5.QtSvg import QSvgRenderer

class IconComparisonWindow(QMainWindow):
    """Window to compare old PNG icons with new SVG icons."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OnCutF Icon Comparison - Old PNG vs New SVG")
        self.setGeometry(100, 100, 1200, 800)

        # Apply dark theme similar to OnCutF
        self.setStyleSheet("""
            QMainWindow {
                background-color: #181818;
                color: #f0ebd8;
            }
            QWidget {
                background-color: #181818;
                color: #f0ebd8;
            }
            QLabel {
                color: #f0ebd8;
                font-family: 'Inter', sans-serif;
                background-color: transparent;
            }
            QFrame {
                background-color: #232323;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
            }
            QScrollArea {
                background-color: #181818;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #181818;
            }
        """)

        # Setup UI
        self.setup_ui()
        self.load_icons()

    def setup_ui(self):
        """Setup the main UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title
        title = QLabel("Icon Comparison: Old PNG vs New SVG")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #f0ebd8;
            margin-bottom: 20px;
        """)
        layout.addWidget(title)

        # Subtitle with color explanation
        subtitle = QLabel("""
        Colors used for new SVG icons:
        • Extended Metadata: #ffb74d (orange like progress bar)
        • Hash Operations: #9c27b0 (purple like progress bar)
        • Basic Info: #74c0fc (light blue)
        • Invalid/Error: #ff6b6b (light red)
        • Valid/Success: #51cf66 (light green)
        • Partial/Warning: #ffa726 (light orange)
        """)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 12px;
            color: #90a4ae;
            margin-bottom: 20px;
            line-height: 1.4;
        """)
        layout.addWidget(subtitle)

        # Scroll area for comparisons
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        self.scroll_layout.setSpacing(30)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

    def create_svg_icon(self, svg_path: str, color: str, size: int = 16) -> QPixmap:
        """Create a colored SVG icon."""
        try:
            # Read SVG content
            with open(svg_path, 'r') as f:
                svg_content = f.read()

            # Debug: Print original SVG content (first few lines)
            print(f"Original SVG: {svg_content[:200]}...")

                        # More comprehensive color replacement for feather icons
            # Feather icons typically use stroke="currentColor" or hardcoded colors
            svg_content = svg_content.replace('stroke="currentColor"', f'stroke="{color}"')
            svg_content = svg_content.replace("stroke='currentColor'", f"stroke='{color}'")
            svg_content = svg_content.replace('stroke="#000"', f'stroke="{color}"')
            svg_content = svg_content.replace('stroke="#000000"', f'stroke="{color}"')
            svg_content = svg_content.replace('stroke="black"', f'stroke="{color}"')
            # Replace the hardcoded gray color from feather icons
            svg_content = svg_content.replace('stroke="#d6d6d6"', f'stroke="{color}"')

            # If no stroke attribute, add it to the main SVG element
            if 'stroke=' not in svg_content:
                svg_content = svg_content.replace('<svg', f'<svg stroke="{color}"')

            # Also handle fill for some icons
            svg_content = svg_content.replace('fill="currentColor"', f'fill="{color}"')
            svg_content = svg_content.replace("fill='currentColor'", f"fill='{color}'")

            # Debug: Print modified SVG content
            print(f"Modified SVG: {svg_content[:200]}...")

            # Create SVG renderer
            renderer = QSvgRenderer()
            success = renderer.load(svg_content.encode())
            print(f"SVG loaded successfully: {success}")

            # Create pixmap with dark background for better visibility
            pixmap = QPixmap(size, size)
            pixmap.fill(QColor("#2a2a2a"))  # Dark background instead of transparent

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            renderer.render(painter)
            painter.end()

            return pixmap

        except Exception as e:
            print(f"Error creating SVG icon: {e}")
            # Return empty pixmap with dark background
            pixmap = QPixmap(size, size)
            pixmap.fill(QColor("#2a2a2a"))
            return pixmap

    def create_comparison_row(self, title: str, old_icon_path: str, new_icon_configs: list):
        """Create a comparison row showing old PNG vs new SVG options."""
        frame = QFrame()
        frame.setFixedHeight(140)  # Increased height for better visibility

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(30)

        # Title
        title_label = QLabel(title)
        title_label.setFixedWidth(180)  # Increased width to prevent truncation
        title_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        title_label.setWordWrap(True)  # Allow text wrapping
        title_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #f0ebd8;
            padding: 5px;
        """)
        layout.addWidget(title_label)

        # Old PNG icon
        old_section = QVBoxLayout()
        old_label = QLabel("Current PNG")
        old_label.setAlignment(Qt.AlignCenter)
        old_label.setStyleSheet("font-size: 12px; color: #90a4ae; margin-bottom: 5px;")

        old_icon_label = QLabel()
        old_icon_label.setFixedSize(32, 32)
        old_icon_label.setAlignment(Qt.AlignCenter)
        old_icon_label.setStyleSheet("border: 1px solid #3a3a3a; background-color: #2a2a2a;")

        try:
            pixmap = QPixmap(old_icon_path)
            if not pixmap.isNull():
                old_icon_label.setPixmap(pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                old_icon_label.setText("N/A")
                old_icon_label.setStyleSheet(old_icon_label.styleSheet() + " color: #666;")
        except:
            old_icon_label.setText("N/A")
            old_icon_label.setStyleSheet(old_icon_label.styleSheet() + " color: #666;")

        old_section.addWidget(old_label)
        old_section.addWidget(old_icon_label)
        old_section.addStretch()
        layout.addLayout(old_section)

        # Arrow
        arrow_label = QLabel("→")
        arrow_label.setAlignment(Qt.AlignCenter)
        arrow_label.setStyleSheet("font-size: 20px; color: #748cab; font-weight: bold;")
        layout.addWidget(arrow_label)

        # New SVG icons
        for config in new_icon_configs:
            svg_section = QVBoxLayout()

            svg_label = QLabel(config['name'])
            svg_label.setAlignment(Qt.AlignCenter)
            svg_label.setStyleSheet("font-size: 12px; color: #90a4ae; margin-bottom: 5px;")

            svg_icon_label = QLabel()
            svg_icon_label.setFixedSize(32, 32)
            svg_icon_label.setAlignment(Qt.AlignCenter)
            svg_icon_label.setStyleSheet("border: 1px solid #3a3a3a; background-color: #2a2a2a;")

            # Create SVG icon
            svg_pixmap = self.create_svg_icon(config['path'], config['color'], 16)
            svg_icon_label.setPixmap(svg_pixmap)

            # Color indicator
            color_label = QLabel(config['color'])
            color_label.setAlignment(Qt.AlignCenter)
            color_label.setStyleSheet(f"""
                font-size: 10px;
                color: {config['color']};
                font-family: monospace;
                margin-top: 2px;
            """)

            svg_section.addWidget(svg_label)
            svg_section.addWidget(svg_icon_label)
            svg_section.addWidget(color_label)
            layout.addLayout(svg_section)

        layout.addStretch()
        return frame

    def load_icons(self):
        """Load and display icon comparisons."""
        # Define comparisons
        comparisons = [
            {
                'title': 'Basic Info',
                'old_path': 'resources/icons/info.png',
                'new_configs': [
                    {'name': 'Info (Blue)', 'path': 'resources/icons/feather_icons/info.svg', 'color': '#74c0fc'},
                ]
            },
            {
                'title': 'Extended Metadata',
                'old_path': 'resources/icons/info_extended.png',
                'new_configs': [
                    {'name': 'Info (Orange)', 'path': 'resources/icons/feather_icons/info.svg', 'color': '#ffb74d'},
                ]
            },
            {
                'title': 'Invalid/Error',
                'old_path': 'resources/icons/info_invalid.png',
                'new_configs': [
                    {'name': 'Alert Circle', 'path': 'resources/icons/feather_icons/alert-circle.svg', 'color': '#ff6b6b'},
                    {'name': 'Alert Triangle', 'path': 'resources/icons/feather_icons/alert-triangle.svg', 'color': '#ff6b6b'},
                ]
            },
            {
                'title': 'Loaded/Valid',
                'old_path': 'resources/icons/info_loaded.png',
                'new_configs': [
                    {'name': 'Check Circle', 'path': 'resources/icons/feather_icons/check-circle.svg', 'color': '#51cf66'},
                    {'name': 'Info (Green)', 'path': 'resources/icons/feather_icons/info.svg', 'color': '#51cf66'},
                ]
            },
            {
                'title': 'Modified',
                'old_path': 'resources/icons/info_modified.png',
                'new_configs': [
                    {'name': 'Edit Circle', 'path': 'resources/icons/feather_icons/edit-2.svg', 'color': '#ffa726'},
                    {'name': 'Info (Orange)', 'path': 'resources/icons/feather_icons/info.svg', 'color': '#ffa726'},
                ]
            },
            {
                'title': 'Partial',
                'old_path': 'resources/icons/info_partial.png',
                'new_configs': [
                    {'name': 'Alert Triangle', 'path': 'resources/icons/feather_icons/alert-triangle.svg', 'color': '#ffa726'},
                    {'name': 'Info (Orange)', 'path': 'resources/icons/feather_icons/info.svg', 'color': '#ffa726'},
                ]
            },
            {
                'title': 'Hash Operations',
                'old_path': None,  # No current hash icon
                'new_configs': [
                    {'name': 'Hash (Purple)', 'path': 'resources/icons/feather_icons/hash.svg', 'color': '#9c27b0'},
                    {'name': 'Key (Purple)', 'path': 'resources/icons/feather_icons/key.svg', 'color': '#9c27b0'},
                ]
            },
        ]

        # Create comparison rows
        for comparison in comparisons:
            row = self.create_comparison_row(
                comparison['title'],
                comparison['old_path'],
                comparison['new_configs']
            )
            self.scroll_layout.addWidget(row)

        # Add stretch at the end
        self.scroll_layout.addStretch()

def main():
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle('Fusion')

    window = IconComparisonWindow()
    window.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
