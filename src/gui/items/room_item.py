from PyQt6.QtGui import QPen, QBrush, QColor

from src.core.config import ConfigManager
from src.gui.items.polygon_base import PolygonItem


class RoomItem(PolygonItem):
    """
    A room defined by a list of NodeItems.
    """
    annotation_type = "room"
    _config_section = "room"

    def __init__(self, nodes: list, room_type: str = "default", room_id: str = ""):
        self.room_type = room_type
        self.room_id = room_id
        super().__init__(nodes)

    def update_style(self):
        config = ConfigManager.instance()
        type_conf = config.get_room_type(self.room_type) or config.get_room_type(config.get_value("rooms", "default_type"))

        pen_color = config.get_color("room", "edge", "color")
        pen_width = config.get_ui_value("room", "edge", "width")

        if type_conf:
            c = type_conf.get("color", [200, 200, 200, 100])
            brush_color = QColor(*c)
        else:
            brush_color = config.get_color("fallback", "room", "fill")

        self._brush_color = brush_color
        self.setBrush(QBrush(brush_color))
        self.setPen(QPen(pen_color, pen_width))
        self.setZValue(config.get_ui_value("room", "z_value"))

    def get_label_text(self) -> str:
        config = ConfigManager.instance()
        type_conf = config.get_room_type(self.room_type)
        type_name = type_conf.get("name", self.room_type) if type_conf else self.room_type
        display_id = self.room_id if self.room_id else "?"
        return f"{type_name} ({display_id})"

    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu
        from src.core.undo_commands import ChangeRoomTypeCommand

        menu = QMenu()
        config = ConfigManager.instance()
        types = config.get_room_types()

        sorted_keys = sorted(types.keys(), key=lambda k: types[k].get("index", 0))

        for key in sorted_keys:
            t_data = types[key]
            action = menu.addAction(t_data["name"])

            if key == self.room_type:
                action.setCheckable(True)
                action.setChecked(True)

            def make_callback(k):
                return lambda: self.change_type(k)

            action.triggered.connect(make_callback(key))

        self._build_alignment_menu(menu, event.scenePos())

        menu.exec(event.screenPos())
        event.accept()

    def change_type(self, new_type):
        if new_type == self.room_type:
            return

        views = self.scene().views()
        if views:
            canvas = views[0]
            if hasattr(canvas, "push_command"):
                from src.core.undo_commands import ChangeRoomTypeCommand
                cmd = ChangeRoomTypeCommand(self, self.room_type, new_type)
                canvas.push_command(cmd)
            else:
                self.room_type = new_type
                self.update_style()
                self.update_overlay()
