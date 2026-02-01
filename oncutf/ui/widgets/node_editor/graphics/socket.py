"""Graphics representation of socket connection points.

This module defines QDMGraphicsSocket, the Qt graphics item that renders
socket circles on nodes. Sockets are connection points where edges can
attach to transfer data between nodes.

The graphics socket:
    - Renders as a colored circle indicating socket type
    - Supports highlight state for connection feedback
    - Integrates with theme system for customization

Author:
    Michael Economou

Date:
    2025-12-11
"""

from typing import TYPE_CHECKING

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtWidgets import QGraphicsItem

from oncutf.ui.widgets.node_editor.themes.theme_engine import ThemeEngine

if TYPE_CHECKING:
    from oncutf.ui.widgets.node_editor.core.socket import Socket


class QDMGraphicsSocket(QGraphicsItem):
    """Qt graphics item rendering socket connection points.

    Displays colored circle representing a socket, with visual feedback
    for connection highlighting. Color indicates socket type for
    compatibility checking.

    Attributes:
        socket: Reference to logical Socket model.
        isHighlighted: True when highlighted during connection drag.
        radius: Socket circle radius in pixels.
        outline_width: Width of socket outline stroke.

    """

    def __init__(self, socket: "Socket"):
        """Initialize graphics socket for a logical socket.

        Args:
            socket: Logical Socket this graphics item represents.

        """
        super().__init__(socket.node.graphics_node)

        self.socket = socket

        self.isHighlighted = False

        self.radius = 6
        self.outline_width = 1
        self.init_assets()

    @property
    def socket_type(self) -> int:
        """Get socket type from logical socket.

        Returns:
            Socket type identifier integer.

        """
        return self.socket.socket_type

    def get_socket_color(self, key: int | str) -> QColor:
        """Resolve color for a socket type.

        Looks up socket type in theme color list. Falls back to
        first color if type index is out of range.

        Args:
            key: Socket type integer or hex color string.

        Returns:
            QColor for the specified socket type.

        """
        theme = ThemeEngine.current_theme()
        if isinstance(key, int):
            if 0 <= key < len(theme.socket_colors):
                return theme.socket_colors[key]
            return theme.socket_colors[0]
        if isinstance(key, str):
            return QColor(key)
        return Qt.GlobalColor.transparent

    def change_socket_type(self) -> None:
        """Update visual appearance after socket type change.

        Refreshes background color and brush from current type.
        """
        self._color_background = self.get_socket_color(self.socket_type)
        self._brush = QBrush(self._color_background)
        self.update()

    def init_assets(self) -> None:
        """Initialize pens and brushes from theme.

        Creates Qt drawing objects for normal and highlighted states.
        """
        theme = ThemeEngine.current_theme()

        self._color_background = self.get_socket_color(self.socket_type)
        self._color_outline = theme.socket_outline_color
        self._color_highlight = theme.socket_highlight_color

        self._pen = QPen(self._color_outline)
        self._pen.setWidthF(self.outline_width)
        self._pen_highlight = QPen(self._color_highlight)
        self._pen_highlight.setWidthF(2.0)
        self._brush = QBrush(self._color_background)

    def paint(self, painter, _option, _widget=None) -> None:
        """Render socket as filled circle with outline.

        Uses highlight pen when socket is highlighted during edge drag.

        Args:
            painter: QPainter for rendering.
            _option: Style options (unused).
            _widget: Target widget (unused).

        """
        painter.setBrush(self._brush)
        painter.setPen(self._pen if not self.isHighlighted else self._pen_highlight)
        painter.drawEllipse(-self.radius, -self.radius, 2 * self.radius, 2 * self.radius)

    def boundingRect(self) -> QRectF:
        """Calculate bounding rectangle for socket circle.

        Includes outline width for proper hit detection.

        Returns:
            QRectF enclosing the socket circle with outline.

        """
        return QRectF(
            -self.radius - self.outline_width,
            -self.radius - self.outline_width,
            2 * (self.radius + self.outline_width),
            2 * (self.radius + self.outline_width),
        )
