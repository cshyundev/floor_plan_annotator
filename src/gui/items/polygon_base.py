import math

from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsItem, QGraphicsTextItem, QGraphicsRectItem
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPen, QBrush, QPainterPath

from src.core.config import ConfigManager


class PolygonItem(QGraphicsPathItem):
    """
    Base class for polygon-shaped annotation items.
    Handles drag, rotate, label, and rotation handle logic.
    Subclasses implement update_style() and get_label_text().
    """
    annotation_type = "polygon"  # Override in subclasses
    _config_section: str  # Override in subclasses to read correct config section

    def __init__(self, nodes: list):
        super().__init__()
        self.nodes = nodes

        self._centroid = QPointF(0, 0)
        self._drag_start_pos = None
        self._dragging = False
        self._rotating = False
        self._initial_node_positions = []
        self._initial_angle = 0.0

        for n in self.nodes:
            n.add_polygon(self)

        # Apply subclass style
        self.update_style()

        # Label
        self.label = QGraphicsTextItem(self)
        config = ConfigManager.instance()
        label_scale = config.get_ui_value(self._config_section, "label_scale")
        self.label.setScale(label_scale)
        self.update_overlay()

        # Interaction flags
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

        # Rotation Handle
        handle_size = config.get_ui_value("polygon_handle", "size")
        handle_pen_w = config.get_ui_value("polygon_handle", "pen_width")
        self.rotation_handle = QGraphicsRectItem(-handle_size/2, -handle_size/2, handle_size, handle_size, self)
        self.rotation_handle.setBrush(QBrush(config.get_color("handle", "fill")))
        self.rotation_handle.setPen(QPen(config.get_color("handle", "outline"), handle_pen_w))
        self.rotation_handle.setVisible(False)
        self.rotation_handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

        self.update_shape()

    # --- Template methods (subclasses must override) ---

    def update_style(self):
        """Set pen/brush/z-value. Called on construction and type change."""
        raise NotImplementedError

    def get_label_text(self) -> str:
        """Return string to display in label."""
        raise NotImplementedError

    # --- Common logic ---

    def update_overlay(self):
        config = ConfigManager.instance()
        bg = config.get_value("colors", "label", "background")
        if bg is None:
            raise KeyError("colors key not found: label.background")
        self.label.setHtml(f"<div style='background-color:{bg};'>{self.get_label_text()}</div>")
        self.update_label_pos()

    def update_shape(self):
        path = QPainterPath()
        if not self.nodes:
            self.setPath(path)
            return

        path.moveTo(self.nodes[0].pos())
        x_sum, y_sum = 0, 0
        for i in range(len(self.nodes)):
            pos = self.nodes[i].pos()
            if i > 0:
                path.lineTo(pos)
            x_sum += pos.x()
            y_sum += pos.y()

        path.closeSubpath()
        self.setPath(path)

        if self.nodes:
            self._centroid = QPointF(x_sum / len(self.nodes), y_sum / len(self.nodes))

        self.update_label_pos()
        self.update_handle_pos()

    def update_label_pos(self):
        rect = self.label.boundingRect()
        self.label.setPos(
            self._centroid.x() - rect.width() / 2,
            self._centroid.y() - rect.height() / 2
        )

    def update_handle_pos(self):
        config = ConfigManager.instance()
        offset = config.get_ui_value(self._config_section, "rotation_handle_offset")
        self.rotation_handle.setPos(self._centroid.x(), self._centroid.y() - offset)

    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(self._brush_color.lighter(110)))
        if self.isSelected():
            self.rotation_handle.setVisible(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(QBrush(self._brush_color))
        if not self.isSelected():
            self.rotation_handle.setVisible(False)
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            self.rotation_handle.setVisible(bool(value))
        return super().itemChange(change, value)

    def _is_drawing_tool_active(self):
        """Return True if a non-matching drawing tool is active.

        Same-type tools (tool.annotation_type == self.annotation_type) are
        allowed to interact with this item. Different-type drawing tools
        cause this method to return True so the item ignores mouse events.
        """
        if not self.scene():
            return False
        views = self.scene().views()
        if not views:
            return False
        current_tool = getattr(views[0], 'current_tool', None)
        if current_tool is None:
            return False
        # SelectTool: allows_item_events is True → not blocking
        if getattr(current_tool, 'allows_item_events', True):
            return False
        # Passthrough mode: tool defers to item for this interaction
        if getattr(current_tool, '_passthrough', False):
            return False
        # Same annotation type: allow interaction
        tool_type = getattr(current_tool, 'annotation_type', None)
        if tool_type is not None and tool_type == self.annotation_type:
            return False
        # Different-type drawing tool: block
        return True

    def mousePressEvent(self, event):
        if self._is_drawing_tool_active():
            event.ignore()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.setSelected(True)

            handle_map_pos = self.rotation_handle.mapFromScene(event.scenePos())
            if self.rotation_handle.contains(handle_map_pos) and self.rotation_handle.isVisible():
                self._rotating = True
                self._drag_start_pos = event.scenePos()
                self._initial_node_positions = [n.pos() for n in self.nodes]

                delta = event.scenePos() - self._centroid
                self._initial_angle = math.atan2(delta.y(), delta.x())
                event.accept()
                return

            self._dragging = True
            self._drag_start_pos = event.scenePos()
            self._initial_node_positions = [n.pos() for n in self.nodes]
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_drawing_tool_active():
            event.ignore()
            return

        if self._rotating:
            current_pos = event.scenePos()
            delta = current_pos - self._centroid
            current_angle = math.atan2(delta.y(), delta.x())
            angle_diff = current_angle - self._initial_angle

            cos_a = math.cos(angle_diff)
            sin_a = math.sin(angle_diff)

            for i, node in enumerate(self.nodes):
                orig_pos = self._initial_node_positions[i]
                dx = orig_pos.x() - self._centroid.x()
                dy = orig_pos.y() - self._centroid.y()

                nx = self._centroid.x() + dx * cos_a - dy * sin_a
                ny = self._centroid.y() + dx * sin_a + dy * cos_a
                node.setPos(nx, ny)

            event.accept()

        elif self._dragging:
            delta = event.scenePos() - self._drag_start_pos
            for i, node in enumerate(self.nodes):
                orig_pos = self._initial_node_positions[i]
                node.setPos(orig_pos + delta)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_drawing_tool_active():
            event.ignore()
            return

        if self._dragging or self._rotating:
            new_positions = [QPointF(n.pos()) for n in self.nodes]
            changed = any(
                new_positions[i] != self._initial_node_positions[i]
                for i in range(len(self.nodes))
            )
            if changed:
                views = self.scene().views()
                if views and hasattr(views[0], 'push_command'):
                    from src.core.undo_commands import MoveNodesCommand
                    cmd = MoveNodesCommand(
                        self.nodes,
                        [QPointF(p) for p in self._initial_node_positions],
                        new_positions
                    )
                    views[0].push_command(cmd)
            self._dragging = False
            self._rotating = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)
