from src.gui.base_type_editor import BaseTypeEditorWidget


class RoomTypeEditorWidget(BaseTypeEditorWidget):
    _dialog_title = "Add Room Type"
    _default_alpha = 100
    _default_color = [200, 200, 200, 100]
    _default_border = [100, 100, 100]
    _in_use_label = "room(s)"
    _config_prefix = "room"
    _item_class_path = "src.gui.items.room_item.RoomItem"
    _type_attr = "room_type"
    _has_overlay = True
