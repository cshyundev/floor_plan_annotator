"""Clipboard management for Canvas2D."""

from PyQt6.QtCore import QPointF
from src.core.config import ConfigManager


class ClipboardManager:
    """Manages copy/paste operations for canvas items."""

    def __init__(self, canvas):
        """Initialize clipboard manager.

        Args:
            canvas: Canvas2D instance
        """
        self.canvas = canvas
        self._clipboard = []
        self._config = ConfigManager.instance()

    def copy_selection(self):
        """Copy selected items to clipboard."""
        from src.gui.items import RoomItem, CustomPolygonItem, ObjectItem

        selected = self.canvas.scene.selectedItems()
        self._clipboard = []
        for item in selected:
            if isinstance(item, RoomItem):
                data = {
                    "type": "room",
                    "room_type": item.room_type,
                    "nodes": [(n.pos().x(), n.pos().y()) for n in item.nodes]
                }
                self._clipboard.append(data)
            elif isinstance(item, CustomPolygonItem):
                data = {
                    "type": "custom_polygon",
                    "polygon_type": item.polygon_type,
                    "nodes": [(n.pos().x(), n.pos().y()) for n in item.nodes]
                }
                self._clipboard.append(data)
            elif isinstance(item, ObjectItem):
                data = {
                    "type": "object",
                    "object_type": item.object_type,
                    "center": (item.center.x(), item.center.y()),
                    "width": item.width,
                    "height": item.height,
                    "angle": item.angle,
                    "elevation": item.elevation,
                    "height_3d": item.height_3d,
                }
                self._clipboard.append(data)

    def paste_clipboard(self):
        """Paste clipboard items at an offset position."""
        if not self._clipboard:
            return

        from src.gui.items import NodeItem, RoomItem, CustomPolygonItem, ObjectItem
        from src.core.undo_commands import AddItemCommand

        paste_offset = self._config.get_ui_value("room", "paste_offset")
        new_items = []
        offset = QPointF(paste_offset, paste_offset)

        for data in self._clipboard:
            if data["type"] == "room":
                nodes = []
                for x, y in data["nodes"]:
                    node = NodeItem(x + offset.x(), y + offset.y())
                    nodes.append(node)

                room_id = self.canvas.next_room_id()
                room = RoomItem(nodes, room_type=data["room_type"], room_id=room_id)
                new_items.extend(nodes)
                new_items.append(room)

            elif data["type"] == "custom_polygon":
                nodes = []
                for x, y in data["nodes"]:
                    node = NodeItem(x + offset.x(), y + offset.y())
                    nodes.append(node)

                polygon_id = self.canvas.next_custom_polygon_id()
                poly = CustomPolygonItem(nodes, polygon_type=data["polygon_type"],
                                         polygon_id=polygon_id)
                new_items.extend(nodes)
                new_items.append(poly)

            elif data["type"] == "object":
                cx, cy = data["center"]
                center = QPointF(cx + offset.x(), cy + offset.y())
                object_id = self.canvas.next_object_id()
                obj = ObjectItem(
                    center=center,
                    width=data["width"],
                    height=data["height"],
                    angle=data["angle"],
                    object_type=data["object_type"],
                    object_id=object_id,
                    elevation=data.get("elevation"),
                    height_3d=data.get("height_3d"),
                )
                new_items.append(obj)

        if new_items:
            cmd = AddItemCommand(self.canvas.scene, new_items, "Paste Items")
            self.canvas.push_command(cmd)
