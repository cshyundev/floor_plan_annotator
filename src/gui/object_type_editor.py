from src.gui.base_type_editor import BaseTypeEditorWidget


class ObjectTypeEditorWidget(BaseTypeEditorWidget):
    _dialog_title = "Add Object Type"
    _key_prefix = "obj_"
    _default_alpha = 150
    _default_color = [150, 200, 255, 150]
    _default_border = [80, 130, 200]
    _in_use_label = "object(s)"

    def _get_types(self):
        return self.config.get_object_types()

    def _get_type(self, key):
        return self.config.get_object_type(key)

    def _add_config_type(self, key, name, color, border):
        return self.config.add_object_type(key, name, color, border)

    def _update_config_type(self, key, **kwargs):
        return self.config.update_object_type(key, **kwargs)

    def _delete_config_type(self, key):
        self.config.delete_object_type(key)

    def _check_type_in_use(self, type_key):
        if not self._scene:
            return []
        from src.gui.items import ObjectItem
        return [
            item for item in self._scene.items()
            if isinstance(item, ObjectItem) and item.object_type == type_key
        ]

    def update_all(self):
        if not self._scene:
            return
        from src.gui.items import ObjectItem
        for item in self._scene.items():
            if isinstance(item, ObjectItem):
                item.update_style()
