from PyQt6.QtGui import QPen, QBrush, QColor

from src.core.config import ConfigManager
from src.gui.items.polygon_base import PolygonItem


class CustomPolygonItem(PolygonItem):
    """
    A custom polygon annotation (e.g. clean zone, danger zone).
    """
    annotation_type = "custom_polygon"
    _config_section = "custom_polygon"

    def __init__(self, nodes: list, polygon_type: str = "clean_zone", polygon_id: str = ""):
        self.polygon_type = polygon_type
        self.polygon_id = polygon_id
        super().__init__(nodes)

    def update_style(self):
        config = ConfigManager.instance()
        type_conf = config.get_custom_polygon_type(self.polygon_type)

        pen_width = config.get_ui_value("custom_polygon", "width")

        if type_conf:
            c = type_conf.get("color", [100, 220, 100, 100])
            b = type_conf.get("border", [50, 160, 50])
            brush_color = QColor(*c)
            pen_color = QColor(*b)
        else:
            brush_color = config.get_color("fallback", "custom_polygon", "fill")
            pen_color = config.get_color("fallback", "custom_polygon", "border")

        self._brush_color = brush_color
        self.setBrush(QBrush(brush_color))
        self.setPen(QPen(pen_color, pen_width))
        self.setZValue(config.get_ui_value("custom_polygon", "z_value"))

    def get_label_text(self) -> str:
        config = ConfigManager.instance()
        type_conf = config.get_custom_polygon_type(self.polygon_type)
        type_name = type_conf.get("name", self.polygon_type) if type_conf else self.polygon_type
        display_id = self.polygon_id if self.polygon_id else "?"
        return f"{type_name} ({display_id})"

    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu

        menu = QMenu()
        config = ConfigManager.instance()
        types = config.get_custom_polygon_types()
        sorted_keys = sorted(types.keys(), key=lambda k: types[k].get("index", 0))

        for key in sorted_keys:
            t_data = types[key]
            action = menu.addAction(t_data["name"])
            if key == self.polygon_type:
                action.setCheckable(True)
                action.setChecked(True)
            action.triggered.connect(lambda checked, k=key: self.change_type(k))

        self._build_alignment_menu(menu, event.scenePos())

        menu.exec(event.screenPos())
        event.accept()

    def change_type(self, new_type):
        if new_type == self.polygon_type:
            return

        views = self.scene().views()
        if views:
            canvas = views[0]
            if hasattr(canvas, "push_command"):
                from src.core.undo_commands import ChangeCustomPolygonTypeCommand
                cmd = ChangeCustomPolygonTypeCommand(self, self.polygon_type, new_type)
                canvas.push_command(cmd)
            else:
                self.polygon_type = new_type
                self.update_style()
                self.update_overlay()
