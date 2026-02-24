from src.gui.base_type_editor import BaseTypeEditorWidget


class RoomTypeEditorWidget(BaseTypeEditorWidget):
    _dialog_title = "Add Room Type"
    _key_prefix = "room_"
    _default_alpha = 100
    _default_color = [200, 200, 200, 100]
    _default_border = [100, 100, 100]
    _in_use_label = "room(s)"

    def _get_types(self):
        return self.config.get_room_types()

    def _get_type(self, key):
        return self.config.get_room_type(key)

    def _add_config_type(self, key, name, color, border):
        return self.config.add_room_type(key, name, color, border)

    def _update_config_type(self, key, **kwargs):
        return self.config.update_room_type(key, **kwargs)

    def _delete_config_type(self, key):
        self.config.delete_room_type(key)

    def _check_type_in_use(self, type_key):
        if not self._scene:
            return []
        from src.gui.items import RoomItem
        return [
            item for item in self._scene.items()
            if isinstance(item, RoomItem) and item.room_type == type_key
        ]

    def update_all(self):
        if not self._scene:
            return
        from src.gui.items import RoomItem
        for item in self._scene.items():
            if isinstance(item, RoomItem):
                item.update_style()
                item.update_overlay()
