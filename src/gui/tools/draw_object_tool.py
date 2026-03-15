import math

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPen, QBrush
from PyQt6.QtWidgets import QGraphicsRectItem

from src.core.input_context import InputContext
from src.core.undo_commands import AddItemCommand
from src.gui.tools.base import Tool


class DrawObjectTool(Tool):
    """Draws Object (OBB) annotations by click-and-drag."""
    annotation_type = "object"

    IDLE = "idle"
    DRAWING = "drawing"

    def __init__(self, canvas):
        super().__init__(canvas)
        self._state = self.IDLE
        self._press_pos = None
        self._preview_item = None
        self._passthrough = False

    def _find_object_item_at(self, scene_pos):
        """Return ObjectItem at scene_pos (checking parent chain), or None."""
        from src.gui.items.object_item import ObjectItem
        for item in self.scene.items(scene_pos):
            target = item
            while target is not None:
                if isinstance(target, ObjectItem):
                    return target
                target = target.parentItem()
        return None

    def on_mouse_press(self, context: InputContext):
        if context.buttons == Qt.MouseButton.LeftButton and self._state == self.IDLE:
            # If clicking on an existing ObjectItem, passthrough to let item handle it
            if self._find_object_item_at(context.scene_pos) is not None:
                self._passthrough = True
                return

            self._press_pos = context.scene_pos
            self._state = self.DRAWING

            # Create preview rect (non-interactive — no mouse, no selection)
            self._preview_item = QGraphicsRectItem(QRectF(self._press_pos, self._press_pos))
            border_color = self.config.get_color("tool_preview", "object", "border")
            fill_color = self.config.get_color("tool_preview", "object", "fill")
            preview_pen = QPen(border_color, 0)  # width=0 → cosmetic 1px line
            preview_pen.setStyle(Qt.PenStyle.DashLine)
            self._preview_item.setPen(preview_pen)
            self._preview_item.setBrush(QBrush(fill_color))
            self._preview_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self._preview_item.setFlag(
                self._preview_item.GraphicsItemFlag.ItemIsSelectable, False
            )
            self.scene.addItem(self._preview_item)

    def on_mouse_move(self, context: InputContext):
        if self._passthrough:
            return
        if self._state == self.DRAWING and self._preview_item is not None:
            snapped = self.snap_manager.snap_drag_point(
                context.scene_pos, modifiers=context.modifiers,
            )
            rect = QRectF(self._press_pos, snapped).normalized()
            self._preview_item.setRect(rect)

    def on_mouse_release(self, context: InputContext):
        if self._passthrough:
            self._passthrough = False
            return
        if self._state != self.DRAWING:
            return

        # Remove preview and guides
        self.snap_manager.clear_guides()
        if self._preview_item is not None:
            self.scene.removeItem(self._preview_item)
            self._preview_item = None

        end_pos = context.scene_pos
        dx = end_pos.x() - self._press_pos.x()
        dy = end_pos.y() - self._press_pos.y()
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < 0.01:
            self._state = self.IDLE
            self._press_pos = None
            return

        # Select type via popup (None if cancelled/ESC)
        selected_key = self._select_object_type()
        if selected_key is None:
            self._state = self.IDLE
            self._press_pos = None
            return

        center = QPointF(
            (self._press_pos.x() + end_pos.x()) / 2,
            (self._press_pos.y() + end_pos.y()) / 2
        )
        width = abs(dx)
        height = abs(dy)

        object_id = self.canvas.next_object_id()
        from src.gui.items.object_item import ObjectItem
        obj_item = ObjectItem(
            center=center,
            width=width,
            height=height,
            angle=0.0,
            object_type=selected_key,
            object_id=object_id
        )

        cmd = AddItemCommand(self.scene, [obj_item], "Add Object")
        self.canvas.push_command(cmd)
        self.canvas.status_message.emit(f"Object '{selected_key}' created.")

        self._state = self.IDLE
        self._press_pos = None

    def _select_object_type(self):
        from src.gui.type_popup import TypePopup
        from PyQt6.QtGui import QCursor  # noqa: QCursor is in QtGui
        popup = TypePopup(self.canvas, self.config.get_object_types, [150, 200, 255, 150])
        popup.move(QCursor.pos())
        if popup.exec():
            selected = popup.get_selected_type()
            if selected:
                return selected
        return None

    def cleanup(self):
        self.snap_manager.clear_guides()
        if self._preview_item is not None:
            if self._preview_item.scene() == self.scene:
                self.scene.removeItem(self._preview_item)
            self._preview_item = None
        self._state = self.IDLE
        self._press_pos = None
