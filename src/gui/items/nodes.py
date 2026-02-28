import math

from PyQt6.QtWidgets import QGraphicsItem, QGraphicsEllipseItem, QGraphicsLineItem
from PyQt6.QtCore import Qt, QLineF, QPointF
from PyQt6.QtGui import QPen, QBrush

from src.core.config import ConfigManager
from src.gui.items.geometry_utils import compute_hv_status, compute_aligned_positions


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
            # Clear snap guides
            if self.scene():
                views = self.scene().views()
                if views and hasattr(views[0], 'snap_manager'):
                    views[0].snap_manager.clear_guides()
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
                if not getattr(poly, '_batch_updating', False):
                    poly.update_shape()
            # Show alignment guides during drag (skip during polygon batch update)
            if self._drag_start_pos is not None and self.scene():
                batch_active = any(
                    getattr(p, '_batch_updating', False) for p in self.polygons
                )
                if not batch_active:
                    views = self.scene().views()
                    if views and hasattr(views[0], 'snap_manager'):
                        views[0].snap_manager.snap_drag_point(value, exclude_items=[self])
        return super().itemChange(change, value)

    def _get_neighbor_node(self, edge):
        """Return the node on the other end of the edge."""
        return edge.end_node if edge.start_node is self else edge.start_node

    def _get_neighbor_nodes(self):
        """Get unique neighbor nodes from both edges and polygons."""
        neighbors = set()
        for edge in self.edges:
            neighbors.add(self._get_neighbor_node(edge))
        for poly in self.polygons:
            idx = poly.nodes.index(self)
            n = len(poly.nodes)
            neighbors.add(poly.nodes[(idx - 1) % n])
            neighbors.add(poly.nodes[(idx + 1) % n])
        return list(neighbors)

    def _compute_perpendicular_position(self):
        """Compute new position for this node so two adjacent lines meet at 90 degrees.

        Uses Thales' theorem: any point on a circle with diameter AB
        sees segment AB at exactly 90 degrees. Projects the current
        position onto that circle (closest point).

        Works for nodes connected via wall edges and/or polygon edges.

        Returns:
            New QPointF for this node, or None if not applicable.
        """
        neighbors = self._get_neighbor_nodes()
        if len(neighbors) != 2:
            return None

        a = neighbors[0].pos()
        b = neighbors[1].pos()
        mid = QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)
        radius = math.hypot(b.x() - a.x(), b.y() - a.y()) / 2

        dx = self.pos().x() - mid.x()
        dy = self.pos().y() - mid.y()
        dist = math.hypot(dx, dy)

        if dist < 1e-12:
            # Node is at midpoint of AB — pick perpendicular direction
            ab_x = b.x() - a.x()
            ab_y = b.y() - a.y()
            dx, dy = -ab_y, ab_x
            dist = math.hypot(dx, dy)

        return QPointF(
            mid.x() + dx / dist * radius,
            mid.y() + dy / dist * radius,
        )

    def make_perpendicular(self):
        """Move this node so connected edges meet at exactly 90 degrees."""
        new_pos = self._compute_perpendicular_position()
        if new_pos is None:
            return

        if self.scene():
            views = self.scene().views()
            if views and hasattr(views[0], 'push_command'):
                from src.core.undo_commands import MoveNodeCommand
                cmd = MoveNodeCommand(self, self.pos(), new_pos)
                views[0].push_command(cmd)
                if hasattr(views[0], 'status_message'):
                    views[0].status_message.emit("Node moved to make 90\u00b0 angle.")

    def contextMenuEvent(self, event):
        neighbors = self._get_neighbor_nodes()
        if len(neighbors) != 2:
            return super().contextMenuEvent(event)

        from PyQt6.QtWidgets import QMenu
        menu = QMenu()
        action = menu.addAction("Make Perpendicular")

        # Disable if already perpendicular (dot product ≈ 0)
        a = neighbors[0].pos()
        b = neighbors[1].pos()
        c = self.pos()
        dot = (a.x() - c.x()) * (b.x() - c.x()) + (a.y() - c.y()) * (b.y() - c.y())
        if abs(dot) < 1e-9:
            action.setEnabled(False)

        action.triggered.connect(self.make_perpendicular)
        menu.exec(event.screenPos())
        event.accept()

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

        self.is_boundary_edge = False

        # Register self to nodes
        self.start_node.add_edge(self)
        self.end_node.add_edge(self)

        # Style
        config = ConfigManager.instance()
        default_color = config.get_color("wall", "default", "color")
        default_width = config.get_ui_value("wall", "default", "width")

        selected_color = config.get_color("wall", "selected", "color")
        selected_width = config.get_ui_value("wall", "selected", "width")

        hover_width = config.get_ui_value("wall", "hover", "width")
        hv_color = config.get_color("wall", "hover", "hv_color")
        other_color = config.get_color("wall", "hover", "other_color")

        self.pen_default = QPen(default_color, default_width)
        self.pen_selected = QPen(selected_color, selected_width)
        self.pen_hover_hv = QPen(hv_color, hover_width)
        self.pen_hover_other = QPen(other_color, hover_width)
        self.setPen(self.pen_default)
        self.setZValue(config.get_ui_value("wall", "z_value"))

        self._hv_threshold = config.get_ui_value("wall", "hover", "angle_threshold")

        self.setAcceptHoverEvents(True)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

        self.update_line()

    def _compute_hv_status(self):
        """Compute whether this edge is horizontal or vertical.

        Returns:
            (is_hv, deviation_deg, label) where deviation_deg is the
            angular distance from the nearest H/V axis.
        """
        return compute_hv_status(
            self.start_node.pos(), self.end_node.pos(), self._hv_threshold,
        )

    def hoverEnterEvent(self, event):
        is_hv, deviation, label = self._compute_hv_status()
        self.setPen(self.pen_hover_hv if is_hv else self.pen_hover_other)
        if self.scene():
            views = self.scene().views()
            if views and hasattr(views[0], 'status_message'):
                if label:
                    msg = f"Wall: {label} ({deviation:.1f}\u00b0 off)"
                else:
                    msg = f"Wall: {deviation:.1f}\u00b0 from nearest H/V"
                views[0].status_message.emit(msg)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if self.isSelected():
            self.setPen(self.pen_selected)
        else:
            self.setPen(self.pen_default)
        super().hoverLeaveEvent(event)

    def _compute_aligned_positions(self, direction):
        """Compute node positions that align this edge to H or V.

        Args:
            direction: "horizontal" or "vertical"

        Returns:
            (new_start_pos, new_end_pos) as QPointF pair.
        """
        return compute_aligned_positions(
            self.start_node.pos(), self.end_node.pos(), direction,
        )

    def align_to(self, direction):
        """Align this edge to horizontal or vertical via undo command."""
        old_positions = [self.start_node.pos(), self.end_node.pos()]
        new_start, new_end = self._compute_aligned_positions(direction)
        new_positions = [new_start, new_end]

        if self.scene():
            views = self.scene().views()
            if views and hasattr(views[0], 'push_command'):
                from src.core.undo_commands import MoveNodesCommand
                cmd = MoveNodesCommand(
                    [self.start_node, self.end_node],
                    old_positions, new_positions,
                )
                views[0].push_command(cmd)
                if hasattr(views[0], 'status_message'):
                    views[0].status_message.emit(
                        f"Wall aligned to {direction}."
                    )

    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu

        menu = QMenu()
        h_action = menu.addAction("Align Horizontal")
        v_action = menu.addAction("Align Vertical")

        # Disable only if alignment would not change positions
        start, end = self.start_node.pos(), self.end_node.pos()
        if start.y() == end.y():
            h_action.setEnabled(False)
        if start.x() == end.x():
            v_action.setEnabled(False)

        h_action.triggered.connect(lambda: self.align_to("horizontal"))
        v_action.triggered.connect(lambda: self.align_to("vertical"))

        menu.exec(event.screenPos())
        event.accept()

    def update_line(self):
        line = QLineF(self.start_node.pos(), self.end_node.pos())
        self.setLine(line)

    def paint(self, painter, option, widget):
        if self.isSelected():
            self.setPen(self.pen_selected)
        elif not self.isUnderMouse():
            self.setPen(self.pen_default)
        super().paint(painter, option, widget)
