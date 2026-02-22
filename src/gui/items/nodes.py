from PyQt6.QtWidgets import QGraphicsItem, QGraphicsEllipseItem, QGraphicsLineItem
from PyQt6.QtCore import Qt, QLineF
from PyQt6.QtGui import QPen, QBrush

from src.core.config import ConfigManager


class NodeItem(QGraphicsEllipseItem):
    """
    A draggable node (point).
    """
    def __init__(self, x, y, radius=None):
        config = ConfigManager.instance()
        if radius is None:
            radius = config.get_ui_value("node", "radius")

        super().__init__(-radius, -radius, radius*2, radius*2)
        self.setPos(x, y)

        # Style
        brush_color = config.get_color("node", "brush")
        pen_color = config.get_color("node", "pen")
        pen_width = config.get_ui_value("node", "pen_width")
        self.setBrush(QBrush(brush_color))
        self.setPen(QPen(pen_color, pen_width))
        self.setZValue(config.get_ui_value("node", "z_value"))

        # Hover settings
        self.setAcceptHoverEvents(True)
        self.default_brush = QBrush(brush_color)
        self.hover_brush = QBrush(config.get_color("node", "hover", "brush"))
        self.default_scale = 1.0
        self.hover_scale = config.get_ui_value("node", "hover", "scale")

        # Interaction
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
                      QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        self._drag_start_pos = None
        self.edges = [] # List of connected EdgeItems
        self.polygons = [] # List of connected PolygonItems

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and self._drag_start_pos is not None:
            new_pos = self.pos()
            if new_pos != self._drag_start_pos:
                views = self.scene().views()
                if views and hasattr(views[0], 'push_command'):
                    from src.core.undo_commands import MoveNodeCommand
                    cmd = MoveNodeCommand(self, self._drag_start_pos, new_pos)
                    views[0].push_command(cmd)
            self._drag_start_pos = None

    def hoverEnterEvent(self, event):
        self.setScale(self.hover_scale)
        self.setBrush(self.hover_brush)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setScale(self.default_scale)
        self.setBrush(self.default_brush)
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Notify connected items
            for edge in self.edges:
                edge.update_line()
            for poly in self.polygons:
                poly.update_shape()
        return super().itemChange(change, value)

    def add_edge(self, edge):
        if edge not in self.edges:
            self.edges.append(edge)

    def add_polygon(self, poly):
        if poly not in self.polygons:
            self.polygons.append(poly)


class EdgeItem(QGraphicsLineItem):
    """
    A wall connecting two NodeItems.
    """
    annotation_type = "wall"

    def __init__(self, start_node: NodeItem, end_node: NodeItem):
        super().__init__()
        self.start_node = start_node
        self.end_node = end_node

        # Generate unique ID for 3D wall geometry tracking
        self.edge_id = f"edge_{id(self)}"

        # Register self to nodes
        self.start_node.add_edge(self)
        self.end_node.add_edge(self)

        # Style
        config = ConfigManager.instance()
        default_color = config.get_color("wall", "default", "color")
        default_width = config.get_ui_value("wall", "default", "width")

        selected_color = config.get_color("wall", "selected", "color")
        selected_width = config.get_ui_value("wall", "selected", "width")

        self.pen_default = QPen(default_color, default_width)
        self.pen_selected = QPen(selected_color, selected_width)
        self.setPen(self.pen_default)
        self.setZValue(config.get_ui_value("wall", "z_value"))

        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

        self.update_line()

    def update_line(self):
        line = QLineF(self.start_node.pos(), self.end_node.pos())
        self.setLine(line)

    def paint(self, painter, option, widget):
        if self.isSelected():
            self.setPen(self.pen_selected)
        else:
            self.setPen(self.pen_default)
        super().paint(painter, option, widget)
