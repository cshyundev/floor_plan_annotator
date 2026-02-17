from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsItem, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsTextItem, QGraphicsRectItem, QGraphicsTextItem, QGraphicsRectItem
from PyQt6.QtCore import Qt, QPointF, QLineF, QRectF, pyqtSignal, QObject
from PyQt6.QtGui import QPen, QBrush, QColor, QPainterPath

from src.core.config import ConfigManager

class NodeItem(QGraphicsEllipseItem):
    """
    A draggable node (point).
    """
    def __init__(self, x, y, radius=None):
        config = ConfigManager.instance()
        if radius is None:
            radius = config.get_value("colors", "node", "radius") or 0.05
            
        super().__init__(-radius, -radius, radius*2, radius*2)
        self.setPos(x, y)
        
        # Style
        brush_color = config.get_color("node", "brush")
        pen_color = config.get_color("node", "pen")
        pen_width = config.get_value("colors", "node", "pen_width") or 0.01
        self.setBrush(QBrush(brush_color))
        self.setPen(QPen(pen_color, pen_width))
        self.setZValue(config.get_value("colors", "node", "z_value") or 100)
        
        # Hover settings
        self.setAcceptHoverEvents(True)
        self.default_brush = QBrush(brush_color)
        self.hover_brush = QBrush(QColor(config.get_value("colors", "node", "hover", "brush") or "orange"))
        self.default_scale = 1.0
        self.hover_scale = config.get_value("colors", "node", "hover", "scale") or 1.5

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
        default_width = config.get_value("colors", "wall", "default", "width") or 0.02

        selected_color = config.get_color("wall", "selected", "color")
        selected_width = config.get_value("colors", "wall", "selected", "width") or 0.03
        
        self.pen_default = QPen(default_color, default_width)
        self.pen_selected = QPen(selected_color, selected_width)
        self.setPen(self.pen_default)
        self.setZValue(config.get_value("colors", "wall", "z_value") or 50)
        
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


class RoomItem(QGraphicsPathItem):
    """
    A room defined by a list of NodeItems.
    """
    def __init__(self, nodes: list[NodeItem], room_type: str = "default", room_id: str = ""):
        super().__init__()
        self.nodes = nodes
        self.room_type = room_type
        self.room_id = room_id
        
        self._centroid = QPointF(0, 0)
        self._drag_start_pos = None
        self._dragging = False
        self._rotating = False
        self._initial_node_positions = []
        self._initial_angle = 0.0
        
        for n in self.nodes:
            n.add_polygon(self)
        
        # Config
        self.update_style()
        
        # Label (scaled to match scene coordinates - meters)
        self.label = QGraphicsTextItem(self)
        config = ConfigManager.instance()
        label_scale = config.get_value("colors", "room", "label_scale") or 0.015
        self.label.setScale(label_scale)
        self.update_overlay()
        
        # Interaction flags
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        
        # Rotation Handle (size in scene coordinates - meters)
        handle_size = 0.1  # 10cm x 10cm
        self.rotation_handle = QGraphicsRectItem(-handle_size/2, -handle_size/2, handle_size, handle_size, self)
        self.rotation_handle.setBrush(QBrush(Qt.GlobalColor.blue))
        self.rotation_handle.setPen(QPen(Qt.GlobalColor.white, 0.01))
        self.rotation_handle.setVisible(False)
        self.rotation_handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        
        self.update_shape()

    def update_overlay(self):
        self.label.setHtml(f"<div style='background-color:rgba(255,255,255,150);'>{self.get_label_text()}</div>")
        self.update_label_pos()

    def get_label_text(self):
        config = ConfigManager.instance()
        type_conf = config.get_room_type(self.room_type)
        type_name = type_conf.get("name", self.room_type) if type_conf else self.room_type
        display_id = self.room_id if self.room_id else "?"
        return f"{type_name} ({display_id})"

    def update_style(self):
        config = ConfigManager.instance()
        type_conf = config.get_room_type(self.room_type) or config.get_room_type(config.get_value("rooms", "default_type"))

        # Pen color from config (room.edge.color) - blue by default
        pen_color = config.get_color("room", "edge", "color")
        pen_width = config.get_value("colors", "room", "edge", "width") or 0.02

        if type_conf:
            c = type_conf.get("color", [200, 200, 200, 100])
            brush_color = QColor(*c)
            self.__brush_color = brush_color
        else:
            brush_color = QColor(200, 200, 200, 100)
            self.__brush_color = brush_color

        self.setBrush(QBrush(brush_color))
        self.setPen(QPen(pen_color, pen_width))
        self.setZValue(config.get_value("colors", "room", "z_value") or 40)

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
        
        # Update Centroid
        if self.nodes:
            self._centroid = QPointF(x_sum / len(self.nodes), y_sum / len(self.nodes))
        
        self.update_label_pos()
        self.update_handle_pos()

    def update_label_pos(self):
        # Center label
        rect = self.label.boundingRect()
        self.label.setPos(self._centroid.x() - rect.width()/2, self._centroid.y() - rect.height()/2)

    def update_handle_pos(self):
        """Place rotation handle above centroid."""
        config = ConfigManager.instance()
        offset = config.get_value("colors", "room", "rotation_handle_offset") or 30
        self.rotation_handle.setPos(self._centroid.x(), self._centroid.y() - offset)

    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(self.__brush_color.lighter(110)))
        if self.isSelected():
             self.rotation_handle.setVisible(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(QBrush(self.__brush_color))
        if not self.isSelected():
            self.rotation_handle.setVisible(False)
        super().hoverLeaveEvent(event)
        
    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            self.rotation_handle.setVisible(bool(value))
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setSelected(True)

            # Check if clicked on rotation handle
            handle_map_pos = self.rotation_handle.mapFromScene(event.scenePos())
            if self.rotation_handle.contains(handle_map_pos) and self.rotation_handle.isVisible():
                self._rotating = True
                self._drag_start_pos = event.scenePos()
                self._initial_node_positions = [n.pos() for n in self.nodes]

                delta = event.scenePos() - self._centroid
                import math
                self._initial_angle = math.atan2(delta.y(), delta.x())
                event.accept()
                return

            # Else, dragging
            self._dragging = True
            self._drag_start_pos = event.scenePos()
            self._initial_node_positions = [n.pos() for n in self.nodes]
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._rotating:
            import math
            current_pos = event.scenePos()
            delta = current_pos - self._centroid
            current_angle = math.atan2(delta.y(), delta.x())
            angle_diff = current_angle - self._initial_angle
            
            # Rotate nodes
            # x' = cx + (x-cx)cos - (y-cy)sin
            # y' = cy + (x-cx)sin + (y-cy)cos
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

    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu
        from src.core.undo_commands import ChangeRoomTypeCommand
        
        menu = QMenu()
        config = ConfigManager.instance()
        types = config.get_room_types()
        
        # Sort by index
        sorted_keys = sorted(types.keys(), key=lambda k: types[k].get("index", 0))
        
        for key in sorted_keys:
            t_data = types[key]
            action = menu.addAction(t_data["name"])
            
            # visual check if current
            if key == self.room_type:
                action.setCheckable(True)
                action.setChecked(True)
                
            def make_callback(k):
                return lambda: self.change_type(k)
                
            action.triggered.connect(make_callback(key))
            
        menu.exec(event.screenPos())
        event.accept()

    def change_type(self, new_type):
        if new_type == self.room_type:
            return
            
        # Get canvas to push command
        # scene.views() returns list of QGraphicsView
        views = self.scene().views()
        if views:
            canvas = views[0]
            # Verify it has push_command
            if hasattr(canvas, "push_command"):
                from src.core.undo_commands import ChangeRoomTypeCommand
                cmd = ChangeRoomTypeCommand(self, self.room_type, new_type)
                canvas.push_command(cmd)
            else:
                # Fallback if not attached to Canvas2D properly
                self.room_type = new_type
                self.update_style()
                self.update_overlay()
