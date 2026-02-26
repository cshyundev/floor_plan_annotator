import math

from PyQt6.QtWidgets import QGraphicsItem, QGraphicsTextItem, QGraphicsPolygonItem
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPen, QBrush, QColor, QPolygonF

from src.core.config import ConfigManager


class ObjectItem(QGraphicsPolygonItem):
    """
    An Oriented Bounding Box (OBB) annotation item.
    Defined by center, width, height, and rotation angle (degrees).
    """
    annotation_type = "object"

    def __init__(self, center: QPointF, width: float, height: float,
                 angle: float = 0.0, object_type: str = "furniture", object_id: str = ""):
        super().__init__()
        self.center = center
        self.width = width
        self.height = height
        self.angle = angle  # degrees
        self.object_type = object_type
        self.object_id = object_id

        self._drag_start_pos = None
        self._drag_start_center = None
        self._rotating = False
        self._resizing = False
        self._resize_corner_idx = None
        self._initial_center = None
        self._initial_width = None
        self._initial_height = None
        self._initial_angle = None

        config = ConfigManager.instance()
        self._handle_size = config.get_ui_value("object", "handle_size")
        self._rot_handle_offset = config.get_ui_value("object", "rotation_handle_offset")

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

        self._hovered = False

        # Label
        self.label = QGraphicsTextItem(self)
        label_scale = config.get_ui_value("object", "label_scale")
        self.label.setScale(label_scale)

        self.update_style()
        self.update_shape()

    def _compute_corners(self):
        """Compute the 4 corners of the OBB in scene coordinates."""
        cx, cy = self.center.x(), self.center.y()
        w, h = self.width / 2, self.height / 2
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        offsets = [(-w, -h), (w, -h), (w, h), (-w, h)]
        corners = []
        for dx, dy in offsets:
            rx = dx * cos_a - dy * sin_a
            ry = dx * sin_a + dy * cos_a
            corners.append(QPointF(cx + rx, cy + ry))
        return corners

    def _rotation_handle_pos(self):
        """Compute rotation handle position (above top-center)."""
        cx, cy = self.center.x(), self.center.y()
        h = self.height / 2 + self._rot_handle_offset
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        # Top-center direction
        rx = 0 * cos_a - (-h) * sin_a
        ry = 0 * sin_a + (-h) * cos_a
        return QPointF(cx + rx, cy + ry)

    def update_shape(self):
        corners = self._compute_corners()
        polygon = QPolygonF(corners)
        self.setPolygon(polygon)
        self._update_label_pos()

    def _update_label_pos(self):
        rect = self.label.boundingRect()
        self.label.setPos(
            self.center.x() - rect.width() * self.label.scale() / 2,
            self.center.y() - rect.height() * self.label.scale() / 2
        )

    def boundingRect(self):
        base = super().boundingRect()
        hs = self._handle_size
        # Extend for corner handle padding and rotation handle
        extended = base.adjusted(-hs, -hs, hs, hs)
        rh = self._rotation_handle_pos()
        rh_rect = QRectF(rh.x() - hs, rh.y() - hs, hs * 2, hs * 2)
        return extended.united(rh_rect)

    def shape(self):
        path = super().shape()
        hs = self._handle_size
        # Include rotation handle area so hover/click events reach the item there
        rh = self._rotation_handle_pos()
        path.addEllipse(QRectF(rh.x() - hs, rh.y() - hs, hs * 2, hs * 2))
        return path

    def update_style(self):
        config = ConfigManager.instance()
        type_conf = config.get_object_type(self.object_type)
        pen_width = config.get_ui_value("object", "width")

        if type_conf:
            c = type_conf.get("color", [150, 200, 255, 150])
            b = type_conf.get("border", [80, 130, 200])
            brush_color = QColor(*c)
            pen_color = QColor(*b)
        else:
            brush_color = config.get_color("fallback", "object", "fill")
            pen_color = config.get_color("fallback", "object", "border")

        self._brush_color = brush_color
        self.setBrush(QBrush(brush_color))
        self.setPen(QPen(pen_color, pen_width))
        self.setZValue(config.get_ui_value("object", "z_value"))

        # Update label
        config_obj = config.get_object_type(self.object_type)
        type_name = config_obj.get("name", self.object_type) if config_obj else self.object_type
        display_id = self.object_id if self.object_id else "?"
        bg = config.get_value("colors", "label", "background")
        if bg is None:
            raise KeyError("colors key not found: label.background")
        color = config.get_value("colors", "label", "color")
        if color is None:
            raise KeyError("colors key not found: label.color")
        self.label.setHtml(
            f"<div style='background-color:{bg}; color:{color};'>"
            f"{type_name} ({display_id})</div>"
        )

        # Cache paint-time colors to avoid per-frame config lookup
        self._paint_arrow_color = config.get_color("object", "arrow")
        self._paint_corner_fill = config.get_color("handle", "corner_fill")
        self._paint_corner_outline = config.get_color("handle", "corner_outline")
        self._paint_rot_fill = config.get_color("handle", "fill")
        self._paint_rot_outline = config.get_color("handle", "outline")
        self._paint_dash_color = config.get_color("handle", "dash")

    def paint(self, painter, option, widget):
        # Suppress Qt's default selection indicator (dashed bounding-rect box).
        # We draw our own selection visual (corner handles + rotation handle).
        from PyQt6.QtWidgets import QStyleOptionGraphicsItem, QStyle
        if option.state & QStyle.StateFlag.State_Selected:
            opt = QStyleOptionGraphicsItem(option)
            opt.state = opt.state & ~QStyle.StateFlag.State_Selected
            super().paint(painter, opt, widget)
        else:
            super().paint(painter, option, widget)

        # Always draw x-axis direction arrow (orientation indicator)
        cx, cy = self.center.x(), self.center.y()
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        arrow_len = self.width / 2 * 0.7
        x_end = QPointF(cx + arrow_len * cos_a, cy + arrow_len * sin_a)
        hs = self._handle_size
        thin = hs * 0.05

        arrow_color = self._paint_arrow_color
        painter.setPen(QPen(arrow_color, thin * 2))
        painter.drawLine(self.center, x_end)

        # Arrowhead triangle
        head_size = hs * 0.5
        perp_x, perp_y = -sin_a, cos_a
        back = QPointF(x_end.x() - cos_a * head_size, x_end.y() - sin_a * head_size)
        p1 = QPointF(back.x() + perp_x * head_size * 0.5, back.y() + perp_y * head_size * 0.5)
        p2 = QPointF(back.x() - perp_x * head_size * 0.5, back.y() - perp_y * head_size * 0.5)
        painter.setBrush(QBrush(arrow_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygonF([x_end, p1, p2]))

        if self.isSelected() or self._hovered:
            # Draw corner handles
            painter.setBrush(QBrush(self._paint_corner_fill))
            painter.setPen(QPen(self._paint_corner_outline, thin))
            for corner in self._compute_corners():
                painter.drawRect(QRectF(corner.x() - hs/2, corner.y() - hs/2, hs, hs))

            # Draw rotation handle (1.5x bigger than corner handles)
            rhs = hs * 1.5
            rh_pos = self._rotation_handle_pos()
            painter.setBrush(QBrush(self._paint_rot_fill))
            painter.setPen(QPen(self._paint_rot_outline, thin))
            painter.drawEllipse(QRectF(rh_pos.x() - rhs/2, rh_pos.y() - rhs/2, rhs, rhs))

            # Draw line from center to rotation handle
            painter.setPen(QPen(self._paint_dash_color, thin, Qt.PenStyle.DashLine))
            painter.drawLine(self.center, rh_pos)

    def _hit_test_corner(self, scene_pos):
        """Return index of corner handle hit, or None."""
        hs = self._handle_size
        for i, corner in enumerate(self._compute_corners()):
            if abs(scene_pos.x() - corner.x()) < hs and abs(scene_pos.y() - corner.y()) < hs:
                return i
        return None

    def _hit_test_rotation_handle(self, scene_pos):
        """Return True if rotation handle is hit."""
        hs = self._handle_size
        rh = self._rotation_handle_pos()
        return abs(scene_pos.x() - rh.x()) < hs and abs(scene_pos.y() - rh.y()) < hs

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def _is_drawing_tool_active(self):
        """Return True if a non-matching drawing tool is active.

        Same-type tools (tool.annotation_type == 'object') are allowed to
        interact. Different-type drawing tools cause this method to return
        True so the item ignores mouse events.
        """
        if not self.scene():
            return False
        views = self.scene().views()
        if not views:
            return False
        current_tool = getattr(views[0], 'current_tool', None)
        if current_tool is None:
            return False
        if getattr(current_tool, 'allows_item_events', True):
            return False
        if getattr(current_tool, '_passthrough', False):
            return False
        tool_type = getattr(current_tool, 'annotation_type', None)
        if tool_type is not None and tool_type == self.annotation_type:
            return False
        return True

    def mousePressEvent(self, event):
        # Ignore interaction when a drawing tool is active to prevent event conflicts
        if self._is_drawing_tool_active():
            event.ignore()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.setSelected(True)
            scene_pos = event.scenePos()

            # Save initial state for undo
            self._initial_center = QPointF(self.center)
            self._initial_width = self.width
            self._initial_height = self.height
            self._initial_angle = self.angle

            if self._hit_test_rotation_handle(scene_pos):
                self._rotating = True
                event.accept()
                return

            corner_idx = self._hit_test_corner(scene_pos)
            if corner_idx is not None:
                self._resizing = True
                self._resize_corner_idx = corner_idx
                event.accept()
                return

            # Body drag
            self._drag_start_pos = scene_pos
            self._drag_start_center = QPointF(self.center)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        scene_pos = event.scenePos()

        if self._rotating:
            self.prepareGeometryChange()
            delta = scene_pos - self.center
            raw_angle = math.degrees(math.atan2(delta.y(), delta.x())) + 90
            if self.scene():
                views = self.scene().views()
                if views and hasattr(views[0], 'snap_manager'):
                    raw_angle = views[0].snap_manager.snap_rotation_angle(
                        self.center, raw_angle, event.modifiers(),
                    )
            self.angle = raw_angle
            self.update_shape()
            event.accept()

        elif self._resizing and self._resize_corner_idx is not None:
            corners = self._compute_corners()
            # Opposite corner is fixed
            opp_idx = (self._resize_corner_idx + 2) % 4
            opp_corner = corners[opp_idx]

            new_center = QPointF((scene_pos.x() + opp_corner.x()) / 2,
                                  (scene_pos.y() + opp_corner.y()) / 2)

            # Compute new w/h in rotated frame
            rad = math.radians(self.angle)
            cos_a, sin_a = math.cos(rad), math.sin(rad)
            dx = scene_pos.x() - new_center.x()
            dy = scene_pos.y() - new_center.y()
            # Inverse rotate
            local_x = dx * cos_a + dy * sin_a
            local_y = -dx * sin_a + dy * cos_a

            new_w = max(0.01, abs(local_x) * 2)
            new_h = max(0.01, abs(local_y) * 2)

            self.prepareGeometryChange()
            self.center = new_center
            self.width = new_w
            self.height = new_h
            self.update_shape()
            event.accept()

        elif self._drag_start_pos is not None:
            self.prepareGeometryChange()
            delta = scene_pos - self._drag_start_pos
            self.center = self._drag_start_center + delta
            self.update_shape()
            # Show alignment guides during body drag
            if self.scene():
                views = self.scene().views()
                if views and hasattr(views[0], 'snap_manager'):
                    views[0].snap_manager.snap_drag_point(
                        self.center, exclude_items=[self],
                    )
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._rotating or self._resizing or self._drag_start_pos is not None:
            # Clear snap guides
            if self.scene():
                views = self.scene().views()
                if views and hasattr(views[0], 'snap_manager'):
                    views[0].snap_manager.clear_guides()
            # Push undo command if state changed
            changed = (
                self.center != self._initial_center or
                self.width != self._initial_width or
                self.height != self._initial_height or
                self.angle != self._initial_angle
            )
            if changed:
                views = self.scene().views()
                if views and hasattr(views[0], 'push_command'):
                    from src.core.undo_commands import TransformObjectCommand
                    cmd = TransformObjectCommand(
                        self,
                        (self._initial_center, self._initial_width,
                         self._initial_height, self._initial_angle),
                        (QPointF(self.center), self.width,
                         self.height, self.angle)
                    )
                    views[0].push_command(cmd)

            self._rotating = False
            self._resizing = False
            self._resize_corner_idx = None
            self._drag_start_pos = None
            self._drag_start_center = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu

        menu = QMenu()
        config = ConfigManager.instance()
        types = config.get_object_types()
        sorted_keys = sorted(types.keys(), key=lambda k: types[k].get("index", 0))

        for key in sorted_keys:
            t_data = types[key]
            action = menu.addAction(t_data["name"])
            if key == self.object_type:
                action.setCheckable(True)
                action.setChecked(True)
            action.triggered.connect(lambda checked, k=key: self.change_type(k))

        menu.exec(event.screenPos())
        event.accept()

    def change_type(self, new_type):
        if new_type == self.object_type:
            return

        views = self.scene().views()
        if views:
            canvas = views[0]
            if hasattr(canvas, "push_command"):
                from src.core.undo_commands import ChangeObjectTypeCommand
                cmd = ChangeObjectTypeCommand(self, self.object_type, new_type)
                canvas.push_command(cmd)
            else:
                self.object_type = new_type
                self.update_style()
