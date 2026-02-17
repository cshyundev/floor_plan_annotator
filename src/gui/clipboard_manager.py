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
        from src.gui.items import RoomItem

        selected = self.canvas.scene.selectedItems()
        self._clipboard = []
        for item in selected:
            if isinstance(item, RoomItem):
                # Store data needed to recreate
                data = {
                    "type": "room",
                    "room_type": item.room_type,
                    "nodes": [(n.pos().x(), n.pos().y()) for n in item.nodes]
                }
                self._clipboard.append(data)

    def paste_clipboard(self):
        """Paste clipboard items at an offset position."""
        if not self._clipboard:
            return

        from src.gui.items import NodeItem, RoomItem
        from src.core.undo_commands import AddItemCommand

        paste_offset = self._config.get_value("colors", "room", "paste_offset") or 20
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

        if new_items:
            cmd = AddItemCommand(self.canvas.scene, new_items, "Paste Items")
            self.canvas.push_command(cmd)
