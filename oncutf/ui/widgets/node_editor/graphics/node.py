"""Graphics representation of nodes in the scene.

This module defines QDMGraphicsNode, the Qt graphics item that renders
individual nodes. It handles visual appearance including title bar,
content area, selection states, and hover effects.

The graphics node:
    - Draws rounded rectangle with title and content areas
    - Responds to mouse events for selection and movement
    - Updates connected edges when moved
    - Supports hover highlighting
    - Integrates with theme system for colors

Author:
    Michael Economou

Date:
    2025-12-11
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt5.QtCore import QRectF, Qt, QTimer
from PyQt5.QtGui import QBrush, QFont, QPainterPath, QPen
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsTextItem, QWidget

from oncutf.ui.widgets.node_editor.themes.theme_engine import ThemeEngine

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QGraphicsSceneHoverEvent, QStyleOptionGraphicsItem

    from oncutf.ui.widgets.node_editor.core.node import Node
    from oncutf.ui.widgets.node_editor.widgets.content_widget import (
        QDMNodeContentWidget,
    )

logger = logging.getLogger(__name__)


class QDMGraphicsNode(QGraphicsItem):
    """Qt graphics item rendering a node in the scene.

    Manages the visual representation of a node including its title bar,
    content widget area, selection highlighting, and hover effects.
    Handles mouse interactions for selection, movement, and double-click.

    Attributes:
        node: Reference to the logical Node model.
        hovered: True while mouse is over this item.
        width: Node width in pixels.
        height: Node height in pixels.
        title_item: QGraphicsTextItem displaying the title.
        graphics_content: QGraphicsProxyWidget containing content widget.

    """

    def __init__(self, node: Node, parent: QWidget | None = None):
        """Initialize graphics node for a logical node.

        Args:
            node: Logical Node this graphics item represents.
            parent: Optional parent widget.

        """
        super().__init__(parent)
        self.node = node

        self.hovered = False
        self._was_moved = False
        self._last_selected_state = False
        self._edge_update_pending = False
        self._edge_update_timer: QTimer | None = None

        self.init_sizes()
        self.init_assets()
        self.init_ui()

    @property
    def content(self) -> QDMNodeContentWidget | None:
        """Content widget of the associated node.

        Returns:
            QDMNodeContentWidget instance or None.

        """
        return self.node.content if self.node else None

    @property
    def title(self) -> str:
        """Display title of this node.

        Returns:
            Current title string.

        """
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        """Update displayed title text.

        Args:
            value: New title string.

        """
        self._title = value
        self.title_item.setPlainText(self._title)

    def init_ui(self) -> None:
        """Configure item flags and initialize visual components."""
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setAcceptHoverEvents(True)

        self.initTitle()
        self.title = self.node.title

        self.initContent()

    def init_sizes(self) -> None:
        """Set default dimensions and padding values."""
        self.width = 180
        self.height = 240
        self.edge_roundness = 10.0
        self.edge_padding = 10
        self.title_height = 24
        self.title_horizontal_padding = 4.0
        self.title_vertical_padding = 4.0

    def init_assets(self) -> None:
        """Initialize pens, brushes, and fonts from theme."""
        theme = ThemeEngine.current_theme()

        self._title_color = theme.node_title_color
        self._title_font = QFont(theme.node_title_font)
        self._title_font.setPointSize(theme.node_title_font_size)

        self._color = theme.node_border_default
        self._color_selected = theme.node_border_selected
        self._color_hovered = theme.node_border_hovered

        self._pen_default = QPen(self._color)
        self._pen_default.setWidthF(theme.node_border_width)
        self._pen_selected = QPen(self._color_selected)
        self._pen_selected.setWidthF(theme.node_border_width)
        self._pen_hovered = QPen(self._color_hovered)
        self._pen_hovered.setWidthF(theme.node_border_width_hovered)

        # Error state pen - from theme
        self._pen_error = QPen(theme.node_border_error)
        self._pen_error.setWidthF(2.5)

        self._brush_title = QBrush(theme.node_title_background)
        self._brush_background = QBrush(theme.node_background)

    def on_selected(self) -> None:
        """Emit selection signal to scene.

        Called when node becomes selected to notify listeners.
        """
        self.node.scene.graphics_scene.item_selected.emit()

    def do_select(self, new_state: bool = True) -> None:
        """Programmatically select or deselect this node.

        Updates internal state tracking and emits signal if selecting.

        Args:
            new_state: True to select, False to deselect.

        """
        self.setSelected(new_state)
        self._last_selected_state = new_state
        if new_state:
            self.on_selected()

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse drag to move node and update edges.

        Uses deferred batch updates to optimize performance when dragging
        multiple nodes. Edge updates are scheduled via QTimer to run once
        per frame instead of on every mouse move event.

        Args:
            event: Qt mouse move event.

        """
        super().mouseMoveEvent(event)

        try:
            scene = self.scene()
            if scene is None or not hasattr(scene, "scene"):
                return

            # Schedule batch edge update if not already pending
            if not self._edge_update_pending:
                self._edge_update_pending = True
                if self._edge_update_timer is None:
                    self._edge_update_timer = QTimer()
                    self._edge_update_timer.timeout.connect(self._batch_update_edges)
                    self._edge_update_timer.setSingleShot(True)
                self._edge_update_timer.start(0)  # Run on next event loop iteration

        except (RuntimeError, AttributeError) as e:
            # Ignore errors from deleted Qt objects during cleanup
            logger.debug("Ignoring Qt cleanup error during node move: %s", e)

        self._was_moved = True

    def _batch_update_edges(self) -> None:
        """Update edges for all selected nodes in a single batch.

        Called by QTimer after mouseMoveEvent to batch multiple edge
        updates into a single operation per frame.
        """
        self._edge_update_pending = False

        try:
            scene = self.scene()
            if scene is None or not hasattr(scene, "scene"):
                return

            # Update edges for all selected nodes once
            for node in list(scene.scene.nodes):
                if node.graphics_node and node.graphics_node.isSelected():
                    node.update_connected_edges()
        except (RuntimeError, AttributeError) as e:
            logger.debug("Ignoring Qt cleanup error during batch edge update: %s", e)

    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release to store history and update selection.

        Args:
            event: Qt mouse release event.

        """
        super().mouseReleaseEvent(event)

        if self._was_moved:
            self._was_moved = False
            self.node.scene.history.store_history("Node moved", set_modified=True)

            self.node.scene.graphics_scene.reset_last_selected_states()
            self.do_select()

            self.node.scene._last_selected_items = self.node.scene.get_selected_items()
            return

        if (
            self._last_selected_state != self.isSelected()
            or self.node.scene._last_selected_items != self.node.scene.get_selected_items()
        ):
            self.node.scene.graphics_scene.reset_last_selected_states()
            self._last_selected_state = self.isSelected()
            self.on_selected()

    def mouseDoubleClickEvent(self, event) -> None:
        """Forward double-click to logical node handler.

        Args:
            event: Qt mouse double-click event.

        """
        self.node.on_double_clicked(event)

    def hoverEnterEvent(self, _event: QGraphicsSceneHoverEvent) -> None:
        """Enable hover highlighting when mouse enters.

        Args:
            _event: Qt hover enter event (unused).

        """
        self.hovered = True
        self.update()

    def hoverLeaveEvent(self, _event: QGraphicsSceneHoverEvent) -> None:
        """Disable hover highlighting when mouse leaves.

        Args:
            _event: Qt hover leave event (unused).

        """
        self.hovered = False
        self.update()

    def boundingRect(self) -> QRectF:
        """Return bounding rectangle for Qt graphics framework.

        Returns:
            QRectF defining item bounds.

        """
        return QRectF(0, 0, self.width, self.height).normalized()

    def initTitle(self) -> None:
        """Create and configure title text item."""
        self.title_item = QGraphicsTextItem(self)
        self.title_item.node = self.node  # type: ignore[attr-defined]  # Dynamic Qt ref
        self.title_item.setDefaultTextColor(self._title_color)
        self.title_item.setFont(self._title_font)
        self.title_item.setPos(self.title_horizontal_padding, 0)
        self.title_item.setTextWidth(self.width - 2 * self.title_horizontal_padding)

    def initContent(self) -> None:
        """Embed content widget as graphics proxy within node."""
        if self.content is not None:
            self.content.setGeometry(
                self.edge_padding,
                self.title_height + self.edge_padding,
                self.width - 2 * self.edge_padding,
                self.height - 2 * self.edge_padding - self.title_height,
            )

        self.graphics_content = self.node.scene.graphics_scene.addWidget(self.content)
        self.graphics_content.node = self.node  # type: ignore[attr-defined]  # Dynamic Qt ref
        self.graphics_content.setParentItem(self)

    def paint(self, painter, _option: QStyleOptionGraphicsItem, _widget=None) -> None:
        """Render node with title bar, content area, and outline.

        Draws rounded rectangles for title and content backgrounds,
        then draws border with appropriate color for selection/hover state.

        Args:
            painter: QPainter for drawing operations.
            _option: Style options (unused).
            _widget: Target widget (unused).

        """
        path_title = QPainterPath()
        path_title.setFillRule(Qt.FillRule.WindingFill)
        path_title.addRoundedRect(
            0,
            0,
            self.width,
            self.title_height,
            self.edge_roundness,
            self.edge_roundness,
        )
        path_title.addRect(
            0,
            self.title_height - self.edge_roundness,
            self.edge_roundness,
            self.edge_roundness,
        )
        path_title.addRect(
            self.width - self.edge_roundness,
            self.title_height - self.edge_roundness,
            self.edge_roundness,
            self.edge_roundness,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._brush_title)
        painter.drawPath(path_title.simplified())

        path_content = QPainterPath()
        path_content.setFillRule(Qt.FillRule.WindingFill)
        path_content.addRoundedRect(
            0,
            self.title_height,
            self.width,
            self.height - self.title_height,
            self.edge_roundness,
            self.edge_roundness,
        )
        path_content.addRect(0, self.title_height, self.edge_roundness, self.edge_roundness)
        path_content.addRect(
            self.width - self.edge_roundness,
            self.title_height,
            self.edge_roundness,
            self.edge_roundness,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._brush_background)
        painter.drawPath(path_content.simplified())

        path_outline = QPainterPath()
        path_outline.addRoundedRect(
            -1,
            -1,
            self.width + 2,
            self.height + 2,
            self.edge_roundness,
            self.edge_roundness,
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Check if node is in error state
        if self.node and self.node.is_invalid():
            painter.setPen(self._pen_error)
            painter.drawPath(path_outline.simplified())
        elif self.hovered:
            painter.setPen(self._pen_hovered)
            painter.drawPath(path_outline.simplified())
            painter.setPen(self._pen_default)
            painter.drawPath(path_outline.simplified())
        else:
            painter.setPen(self._pen_default if not self.isSelected() else self._pen_selected)
            painter.drawPath(path_outline.simplified())
